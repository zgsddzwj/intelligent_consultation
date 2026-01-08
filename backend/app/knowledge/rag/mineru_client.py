"""MinerU API客户端 - 远程PDF解析服务"""
import base64
import asyncio
import aiohttp
import aiofiles
import tempfile
import zipfile
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from app.config import get_settings
from app.utils.logger import app_logger

settings = get_settings()


class MinerUClient:
    """MinerU API客户端"""
    
    def __init__(self):
        """初始化客户端"""
        self.api_url = settings.MINERU_API_URL
        self.api_key = settings.MINERU_API_KEY
        self.timeout = settings.MINERU_TIMEOUT
        self.output_dir = Path(settings.MINERU_OUTPUT_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def to_b64(self, file_path: str) -> str:
        """
        将PDF文件转换为Base64编码
        
        Args:
            file_path: PDF文件路径
        
        Returns:
            Base64编码的字符串
        """
        try:
            with open(file_path, 'rb') as f:
                pdf_bytes = f.read()
                b64_string = base64.b64encode(pdf_bytes).decode('utf-8')
                app_logger.debug(f"PDF文件已编码为Base64，大小: {len(b64_string)} 字符")
                return b64_string
        except Exception as e:
            app_logger.error(f"Base64编码失败: {e}")
            raise
    
    async def parse_pdf_async(self, file_path: str, options: Optional[Dict] = None) -> Dict[str, Any]:
        """
        异步调用MinerU API解析PDF
        
        Args:
            file_path: PDF文件路径
            options: 解析选项
        
        Returns:
            任务信息字典，包含 task_id 和 status
        """
        if not self.api_url:
            raise ValueError("MinerU API URL未配置")
        
        try:
            # 编码PDF文件
            pdf_b64 = self.to_b64(file_path)
            
            # 准备请求数据
            payload = {
                "file": pdf_b64,
                "options": options or {}
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            # 发送解析请求
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(
                    f"{self.api_url}/parse",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"MinerU API请求失败: {response.status} - {error_text}")
                    
                    result = await response.json()
                    app_logger.info(f"MinerU解析任务已提交: {result.get('task_id')}")
                    return result
        
        except Exception as e:
            app_logger.error(f"MinerU API调用失败: {e}")
            raise
    
    async def poll_task_status(self, task_id: str, poll_interval: int = 2, max_polls: int = 150) -> Dict[str, Any]:
        """
        轮询任务状态直到完成
        
        Args:
            task_id: 任务ID
            poll_interval: 轮询间隔（秒）
            max_polls: 最大轮询次数
        
        Returns:
            任务状态字典
        """
        if not self.api_url:
            raise ValueError("MinerU API URL未配置")
        
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        for poll_count in range(max_polls):
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                    async with session.get(
                        f"{self.api_url}/status/{task_id}",
                        headers=headers
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            raise Exception(f"查询任务状态失败: {response.status} - {error_text}")
                        
                        status_result = await response.json()
                        status = status_result.get("status", "unknown")
                        
                        app_logger.debug(f"任务状态 ({poll_count + 1}/{max_polls}): {status}")
                        
                        if status == "completed":
                            app_logger.info(f"任务完成: {task_id}")
                            return status_result
                        elif status == "failed":
                            error_msg = status_result.get("error", "未知错误")
                            raise Exception(f"任务失败: {error_msg}")
                        elif status == "processing":
                            # 继续轮询
                            await asyncio.sleep(poll_interval)
                        else:
                            app_logger.warning(f"未知状态: {status}")
                            await asyncio.sleep(poll_interval)
            
            except Exception as e:
                if poll_count == max_polls - 1:
                    raise
                app_logger.warning(f"轮询失败 (尝试 {poll_count + 1}/{max_polls}): {e}")
                await asyncio.sleep(poll_interval)
        
        raise TimeoutError(f"任务超时: {task_id} (超过 {max_polls * poll_interval} 秒)")
    
    async def download_output_files(self, task_id: str, output_dir: Optional[Path] = None) -> Path:
        """
        异步下载解析结果ZIP文件
        
        Args:
            task_id: 任务ID
            output_dir: 输出目录，如果为None则使用配置目录
        
        Returns:
            下载的ZIP文件路径
        """
        if not self.api_url:
            raise ValueError("MinerU API URL未配置")
        
        output_dir = output_dir or self.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        
        zip_path = output_dir / f"{task_id}.zip"
        failed_marker = output_dir / f"{task_id}_download_failed.txt"
        
        # 检查是否已经失败
        if failed_marker.exists():
            raise Exception(f"之前的下载已失败: {task_id}")
        
        try:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout * 2)) as session:
                async with session.get(
                    f"{self.api_url}/download/{task_id}",
                    headers=headers
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        # 创建失败标记
                        async with aiofiles.open(failed_marker, 'w') as f:
                            await f.write(f"Download failed: {response.status} - {error_text}")
                        raise Exception(f"下载失败: {response.status} - {error_text}")
                    
                    # 保存ZIP文件
                    async with aiofiles.open(zip_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)
                    
                    app_logger.info(f"下载完成: {zip_path}")
                    return zip_path
        
        except Exception as e:
            # 创建失败标记
            try:
                async with aiofiles.open(failed_marker, 'w') as f:
                    await f.write(f"Download failed: {str(e)}")
            except:
                pass
            
            app_logger.error(f"下载失败: {e}")
            raise
    
    async def extract_zip(self, zip_path: Path, extract_dir: Optional[Path] = None) -> Path:
        """
        解压ZIP文件
        
        Args:
            zip_path: ZIP文件路径
            extract_dir: 解压目录，如果为None则解压到ZIP文件所在目录
        
        Returns:
            解压后的目录路径
        """
        try:
            if extract_dir is None:
                extract_dir = zip_path.parent / zip_path.stem
            else:
                extract_dir = Path(extract_dir)
            
            extract_dir.mkdir(parents=True, exist_ok=True)
            
            # 异步解压
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            app_logger.info(f"解压完成: {extract_dir}")
            return extract_dir
        
        except Exception as e:
            app_logger.error(f"解压失败: {e}")
            raise
    
    async def parse_and_download(self, file_path: str, options: Optional[Dict] = None) -> Path:
        """
        完整流程：解析PDF并下载结果
        
        Args:
            file_path: PDF文件路径
            options: 解析选项
        
        Returns:
            解压后的结果目录路径
        """
        try:
            # 1. 提交解析任务
            task_result = await self.parse_pdf_async(file_path, options)
            task_id = task_result.get("task_id")
            
            if not task_id:
                raise ValueError("未获取到任务ID")
            
            # 2. 轮询任务状态
            status_result = await self.poll_task_status(task_id)
            
            # 3. 下载结果
            zip_path = await self.download_output_files(task_id)
            
            # 4. 解压
            extract_dir = await self.extract_zip(zip_path)
            
            # 5. 延迟控制（避免限流）
            await asyncio.sleep(1)
            
            return extract_dir
        
        except Exception as e:
            app_logger.error(f"完整流程失败: {e}")
            raise


# 全局实例
mineru_client = MinerUClient() if settings.ENABLE_MINERU and settings.MINERU_API_URL else None

