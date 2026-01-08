"""AI描述生成器 - 为表格和图片生成描述"""
import asyncio
import time
import json
from typing import Dict, Any, Optional, List
from app.config import get_settings
from app.utils.logger import app_logger

settings = get_settings()


class AIDescriptionGenerator:
    """AI描述生成器"""
    
    def __init__(self):
        """初始化生成器"""
        self.table_api_key = settings.TABLE_DESCRIPTION_API_KEY
        self.table_model = settings.TABLE_DESCRIPTION_MODEL
        self.table_base_url = settings.TABLE_DESCRIPTION_BASE_URL
        self.table_enabled = settings.ENABLE_TABLE_DESCRIPTION and self.table_api_key
        
        self.image_api_key = settings.IMAGE_DESCRIPTION_API_KEY
        self.image_model = settings.IMAGE_DESCRIPTION_MODEL
        self.image_base_url = settings.IMAGE_DESCRIPTION_BASE_URL
        self.image_enabled = settings.ENABLE_IMAGE_DESCRIPTION and self.image_api_key
        
        self.max_retries = 3
        self.base_delay = 1.0  # 指数退避基础延迟（秒）
    
    async def _call_llm_api(self, api_key: str, model: str, base_url: str, 
                           prompt: str, system_prompt: Optional[str] = None,
                           is_vision: bool = False, image_data: Optional[str] = None) -> str:
        """
        调用LLM API生成描述
        
        Args:
            api_key: API密钥
            model: 模型名称
            base_url: API基础URL
            prompt: 提示词
            system_prompt: 系统提示词
            is_vision: 是否为视觉模型
            image_data: 图片数据（Base64或URL）
        
        Returns:
            生成的描述文本
        """
        import aiohttp
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        # 构建请求数据
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        if is_vision and image_data:
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_data}}
                ]
            })
        else:
            messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.3,  # 低temperature以获得更确定的描述
            "max_tokens": 1000
        }
        
        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
                    async with session.post(
                        f"{base_url}/chat/completions",
                        headers=headers,
                        json=payload
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            raise Exception(f"API请求失败: {response.status} - {error_text}")
                        
                        result = await response.json()
                        description = result["choices"][0]["message"]["content"]
                        
                        app_logger.debug(f"AI描述生成成功 (尝试 {attempt + 1}/{self.max_retries})")
                        return description
            
            except Exception as e:
                if attempt == self.max_retries - 1:
                    app_logger.error(f"AI描述生成失败 (已重试 {self.max_retries} 次): {e}")
                    return ""
                
                # 指数退避
                delay = self.base_delay * (2 ** attempt)
                app_logger.warning(f"AI描述生成失败 (尝试 {attempt + 1}/{self.max_retries}): {e}，{delay}秒后重试")
                await asyncio.sleep(delay)
        
        return ""
    
    async def generate_table_description(self, table_html: str, table_title: Optional[str] = None,
                                        context: Optional[str] = None) -> str:
        """
        生成表格描述
        
        Args:
            table_html: 表格HTML
            table_title: 表格标题
            context: 上下文信息
        
        Returns:
            表格描述文本
        """
        if not self.table_enabled:
            return ""
        
        try:
            # 构建提示词
            prompt_parts = []
            if context:
                prompt_parts.append(f"上下文信息：\n{context}\n\n")
            if table_title:
                prompt_parts.append(f"表格标题：{table_title}\n\n")
            prompt_parts.append(f"表格HTML：\n{table_html}\n\n")
            prompt_parts.append("请分析这个表格，生成简洁的文字描述，包括表格的主要内容和关键数据。")
            
            prompt = "".join(prompt_parts)
            
            system_prompt = "你是一个专业的数据分析师，擅长分析表格数据并生成准确、简洁的描述。"
            
            description = await self._call_llm_api(
                api_key=self.table_api_key,
                model=self.table_model,
                base_url=self.table_base_url,
                prompt=prompt,
                system_prompt=system_prompt
            )
            
            return description
        
        except Exception as e:
            app_logger.error(f"表格描述生成失败: {e}")
            return ""
    
    async def generate_image_description(self, image_path: str, image_title: Optional[str] = None,
                                        context_before: Optional[str] = None,
                                        context_after: Optional[str] = None) -> str:
        """
        生成图片描述
        
        Args:
            image_path: 图片路径
            image_title: 图片标题
            context_before: 前文上下文
            context_after: 后文上下文
        
        Returns:
            图片描述文本
        """
        if not self.image_enabled:
            return ""
        
        try:
            # 读取图片并转换为Base64
            import base64
            with open(image_path, 'rb') as f:
                image_bytes = f.read()
                image_b64 = base64.b64encode(image_bytes).decode('utf-8')
                image_data = f"data:image/jpeg;base64,{image_b64}"
            
            # 构建提示词
            prompt_parts = []
            if context_before:
                prompt_parts.append(f"前文上下文：\n{context_before}\n\n")
            if image_title:
                prompt_parts.append(f"图片标题：{image_title}\n\n")
            prompt_parts.append("请详细描述这张图片中的医疗相关内容，包括图表、文字、数据等信息。")
            if context_after:
                prompt_parts.append(f"\n\n后文上下文：\n{context_after}")
            
            prompt = "".join(prompt_parts)
            
            system_prompt = "你是一个专业的医疗图像分析师，擅长识别和分析医疗相关的图表、数据可视化等信息。"
            
            description = await self._call_llm_api(
                api_key=self.image_api_key,
                model=self.image_model,
                base_url=self.image_base_url,
                prompt=prompt,
                system_prompt=system_prompt,
                is_vision=True,
                image_data=image_data
            )
            
            return description
        
        except Exception as e:
            app_logger.error(f"图片描述生成失败: {e}")
            return ""
    
    async def generate_table_descriptions_batch(self, tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量生成表格描述（当前为同步处理，未来可扩展为异步批处理）
        
        Args:
            tables: 表格列表
        
        Returns:
            带描述的表格列表
        """
        results = []
        
        for i, table in enumerate(tables):
            app_logger.info(f"生成表格描述 ({i + 1}/{len(tables)})")
            
            description = await self.generate_table_description(
                table_html=table.get("html", ""),
                table_title=table.get("title"),
                context=table.get("context")
            )
            
            table["ai_description"] = description
            results.append(table)
            
            # 延迟控制（避免限流）
            if i < len(tables) - 1:
                await asyncio.sleep(0.5)
        
        return results
    
    async def generate_image_descriptions_batch(self, images: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量生成图片描述（当前为同步处理，未来可扩展为异步批处理）
        
        Args:
            images: 图片列表
        
        Returns:
            带描述的图片列表
        """
        results = []
        
        for i, image in enumerate(images):
            app_logger.info(f"生成图片描述 ({i + 1}/{len(images)})")
            
            description = await self.generate_image_description(
                image_path=image.get("path", ""),
                image_title=image.get("title"),
                context_before=image.get("context_before"),
                context_after=image.get("context_after")
            )
            
            image["ai_description"] = description
            results.append(image)
            
            # 延迟控制（避免限流）
            if i < len(images) - 1:
                await asyncio.sleep(0.5)
        
        return results


# 全局实例
ai_description_generator = AIDescriptionGenerator() if (
    settings.ENABLE_TABLE_DESCRIPTION or settings.ENABLE_IMAGE_DESCRIPTION
) else None

