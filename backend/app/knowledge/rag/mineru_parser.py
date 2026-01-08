"""MinerU PDF解析器实现"""
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
import pandas as pd
from app.knowledge.rag.pdf_parser import BasePDFParser
from app.knowledge.rag.mineru_client import mineru_client
from app.knowledge.rag.ai_description_generator import ai_description_generator
from app.knowledge.rag.pdf_data_exporter import pdf_data_exporter
from app.config import get_settings
from app.utils.logger import app_logger

settings = get_settings()


class MinerUParser(BasePDFParser):
    """MinerU PDF解析器"""
    
    def __init__(self):
        """初始化解析器"""
        if not mineru_client:
            raise ValueError("MinerU客户端未初始化，请检查配置")
        self.client = mineru_client
        self.description_generator = ai_description_generator
        self.exporter = pdf_data_exporter
    
    def get_parser_type(self) -> str:
        """返回解析器类型"""
        return "mineru"
    
    def _try_load_json(self, json_paths: List[Path]) -> Optional[Dict]:
        """
        尝试从多个路径加载JSON文件
        
        Args:
            json_paths: 可能的JSON文件路径列表
        
        Returns:
            JSON数据字典，如果所有路径都失败则返回None
        """
        for json_path in json_paths:
            if json_path.exists():
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        app_logger.debug(f"成功加载JSON: {json_path}")
                        return data
                except Exception as e:
                    app_logger.warning(f"加载JSON失败: {json_path}, {e}")
        
        return None
    
    def _extract_tables_from_model_json(self, model_json: Dict, doc_id: str) -> List[Dict[str, Any]]:
        """
        从model.json提取表格（category_id=5）
        
        Args:
            model_json: model.json数据
            doc_id: 文档ID
        
        Returns:
            表格列表
        """
        tables = []
        
        try:
            # 查找所有category_id=5的元素（表格）
            table_elements = []
            if isinstance(model_json, list):
                elements = model_json
            elif isinstance(model_json, dict):
                elements = model_json.get("elements", []) if "elements" in model_json else list(model_json.values())
            else:
                elements = []
            
            for element in elements:
                if isinstance(element, dict) and element.get("category_id") == 5:
                    table_elements.append(element)
            
            # 查找标题（category_id=6）
            title_elements = []
            for element in elements:
                if isinstance(element, dict) and element.get("category_id") == 6:
                    title_elements.append(element)
            
            # 关联表格和标题
            for idx, table_element in enumerate(table_elements):
                table_page = table_element.get("page_num", 0)
                table_bbox = table_element.get("bbox", {})
                
                # 查找最近的标题（同一页且位置在表格上方）
                table_title = None
                for title_element in title_elements:
                    title_page = title_element.get("page_num", 0)
                    title_bbox = title_element.get("bbox", {})
                    
                    if title_page == table_page:
                        # 检查标题是否在表格上方
                        if title_bbox.get("y1", 0) <= table_bbox.get("y0", float('inf')):
                            title_text = title_element.get("text", "")
                            if title_text:
                                table_title = title_text
                                break
                
                table_data = {
                    "page": table_page,
                    "index": idx,
                    "html": table_element.get("html", ""),
                    "bbox": table_bbox,
                    "title": table_title,
                    "category_id": 5
                }
                
                tables.append(table_data)
            
            app_logger.info(f"从model.json提取了 {len(tables)} 个表格")
        
        except Exception as e:
            app_logger.error(f"提取表格失败: {e}")
        
        return tables
    
    def _extract_images_from_content_list(self, content_list_json: Dict, 
                                         extract_dir: Path, doc_id: str) -> List[Dict[str, Any]]:
        """
        从content_list.json提取图片
        
        Args:
            content_list_json: content_list.json数据
            extract_dir: 解压目录
            doc_id: 文档ID
        
        Returns:
            图片列表
        """
        images = []
        
        try:
            # 解析content_list.json结构
            if isinstance(content_list_json, list):
                content_list = content_list_json
            elif isinstance(content_list_json, dict):
                content_list = content_list_json.get("content_list", []) if "content_list" in content_list_json else list(content_list_json.values())
            else:
                content_list = []
            
            # 提取图片信息
            for idx, content_item in enumerate(content_list):
                if isinstance(content_item, dict):
                    content_type = content_item.get("type", "")
                    if content_type == "image" or "image" in str(content_type).lower():
                        image_path = content_item.get("path", "")
                        if not image_path:
                            # 如果content_list中没有路径，尝试从Images文件夹查找
                            page_num = content_item.get("page_num", 0)
                            image_index = content_item.get("index", idx)
                            # 尝试多种可能的图片路径格式
                            possible_paths = [
                                extract_dir / "Images" / f"page_{page_num}_{image_index}.png",
                                extract_dir / "Images" / f"page_{page_num}_{image_index}.jpg",
                                extract_dir / "Images" / f"{page_num}_{image_index}.png",
                                extract_dir / "images" / f"page_{page_num}_{image_index}.png",
                                extract_dir / "images" / f"{page_num}_{image_index}.png",
                                extract_dir / "output" / "Images" / f"page_{page_num}_{image_index}.png",
                            ]
                            
                            for possible_path in possible_paths:
                                if possible_path.exists():
                                    image_path = str(possible_path)
                                    break
                        
                        if image_path:
                            # 处理相对路径
                            if not Path(image_path).is_absolute():
                                full_path = extract_dir / image_path
                                if not full_path.exists():
                                    # 尝试从Images文件夹查找
                                    image_name = Path(image_path).name
                                    images_dir = extract_dir / "Images"
                                    if images_dir.exists():
                                        image_file = images_dir / image_name
                                        if image_file.exists():
                                            full_path = image_file
                                        else:
                                            # 查找Images文件夹下的所有图片，按索引匹配
                                            image_files = sorted(list(images_dir.glob("*")))
                                            if idx < len(image_files):
                                                full_path = image_files[idx]
                                image_path = str(full_path) if full_path.exists() else str(extract_dir / image_path)
                            else:
                                image_path = str(Path(image_path))
                            
                            # 提取上下文（前后文本）
                            context_before = content_item.get("context_before", "") or content_item.get("text_before", "") or content_item.get("before_text", "")
                            context_after = content_item.get("context_after", "") or content_item.get("text_after", "") or content_item.get("after_text", "")
                            title = content_item.get("title", "") or content_item.get("caption", "") or content_item.get("image_title", "")
                            
                            image_data = {
                                "page": content_item.get("page_num", 0),
                                "index": idx,
                                "path": image_path,
                                "title": title,
                                "bbox": content_item.get("bbox", {}),
                                "context_before": context_before,
                                "context_after": context_after
                            }
                            
                            images.append(image_data)
            
            app_logger.info(f"从content_list.json提取了 {len(images)} 张图片")
        
        except Exception as e:
            app_logger.error(f"提取图片失败: {e}")
        
        return images
    
    def _generate_markdown_with_metadata(self, text: str, tables: List[Dict], 
                                       images: List[Dict]) -> str:
        """
        生成带元数据的Markdown
        
        Args:
            text: 原始文本
            tables: 表格列表
            images: 图片列表
        
        Returns:
            带元数据注释的Markdown文本
        """
        markdown_parts = [text]
        
        # 按页码和索引排序所有元素
        all_elements = []
        for table in tables:
            all_elements.append({
                "type": "table",
                "page": table.get("page", 0),
                "index": table.get("index", 0),
                "data": table
            })
        for image in images:
            all_elements.append({
                "type": "image",
                "page": image.get("page", 0),
                "index": image.get("index", 0),
                "data": image
            })
        
        # 排序
        all_elements.sort(key=lambda x: (x["page"], x["index"]))
        
        # 为每个元素生成元数据注释
        for element in all_elements:
            element_type = element["type"]
            element_data = element["data"]
            
            metadata = {
                "type": element_type,
                "page": element_data.get("page", 0),
                "index": element_data.get("index", 0),
                "title": element_data.get("title", "")
            }
            
            if element_type == "table":
                metadata["description"] = element_data.get("ai_description", "")
                metadata_str = json.dumps(metadata, ensure_ascii=False)
                markdown_parts.append(f'\n\n<!-- PDF_ELEMENT_METADATA: {metadata_str} -->\n')
                markdown_parts.append(f"\n## {element_data.get('title', '表格')}\n\n")
                markdown_parts.append(element_data.get("html", ""))
                if element_data.get("ai_description"):
                    markdown_parts.append(f"\n\n*描述: {element_data.get('ai_description')}*\n")
            
            elif element_type == "image":
                metadata["description"] = element_data.get("ai_description", "")
                metadata["path"] = element_data.get("path", "")
                metadata_str = json.dumps(metadata, ensure_ascii=False)
                markdown_parts.append(f'\n\n<!-- PDF_ELEMENT_METADATA: {metadata_str} -->\n')
                markdown_parts.append(f"\n## {element_data.get('title', '图片')}\n\n")
                markdown_parts.append(f"![{element_data.get('title', '图片')}]({element_data.get('path', '')})\n")
                if element_data.get("ai_description"):
                    markdown_parts.append(f"\n*描述: {element_data.get('ai_description')}*\n")
        
        return "\n".join(markdown_parts)
    
    def parse_pdf(self, file_path: str, extract_images: bool = True, 
                  doc_id: Optional[str] = None) -> Dict[str, Any]:
        """
        解析PDF文件（异步）
        
        Args:
            file_path: PDF文件路径
            extract_images: 是否提取图片
            doc_id: 文档ID，如果为None则从文件名生成
        
        Returns:
            解析结果字典
        """
        try:
            # 生成文档ID
            if doc_id is None:
                doc_id = Path(file_path).stem
            
            # 检查缓存
            if self.exporter:
                cached_data = self.exporter.load_from_cache(doc_id)
                if cached_data:
                    app_logger.info(f"使用缓存数据: {doc_id}")
                    return cached_data
            
            # 1. 调用MinerU API解析并下载（同步调用异步方法）
            app_logger.info(f"开始解析PDF: {file_path}")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                extract_dir = loop.run_until_complete(self.client.parse_and_download(file_path))
            finally:
                loop.close()
            
            # 2. 加载解析结果JSON文件
            # 尝试多种路径格式
            model_json_paths = [
                extract_dir / f"{doc_id}_model.json",
                extract_dir / "model.json",
                extract_dir / f"{doc_id}" / "model.json",
                extract_dir / "output" / "model.json"
            ]
            
            content_list_json_paths = [
                extract_dir / f"{doc_id}_content_list.json",
                extract_dir / "content_list.json",
                extract_dir / f"{doc_id}" / "content_list.json",
                extract_dir / "output" / "content_list.json"
            ]
            
            model_json = self._try_load_json(model_json_paths)
            content_list_json = self._try_load_json(content_list_json_paths)
            
            if not model_json:
                app_logger.warning("未找到model.json，可能解析失败")
                raise ValueError("未找到model.json文件")
            
            # 3. 提取表格
            tables = self._extract_tables_from_model_json(model_json, doc_id)
            
            # 4. 提取图片
            images = []
            if extract_images and content_list_json:
                images = self._extract_images_from_content_list(content_list_json, extract_dir, doc_id)
            
            # 5. 提取文本（从model.json或其他文件）
            text = ""
            if isinstance(model_json, dict):
                text = model_json.get("text", "")
            elif isinstance(model_json, list):
                # 提取所有文本元素
                text_parts = []
                for element in model_json:
                    if isinstance(element, dict):
                        element_text = element.get("text", "")
                        if element_text and element.get("category_id") not in [5, 6]:  # 排除表格和标题
                            text_parts.append(element_text)
                text = "\n".join(text_parts)
            
            # 6. 生成AI描述（如果启用）- 确保在分块前完成
            if self.description_generator:
                # 生成表格描述（同步调用异步方法）
                if tables and settings.ENABLE_TABLE_DESCRIPTION:
                    app_logger.info(f"开始为 {len(tables)} 个表格生成AI描述...")
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        tables = loop.run_until_complete(
                            self.description_generator.generate_table_descriptions_batch(tables)
                        )
                        # 验证描述已添加到元数据
                        for table in tables:
                            if not table.get("ai_description"):
                                app_logger.warning(f"表格 {table.get('index')} 未生成AI描述")
                    finally:
                        loop.close()
                    app_logger.info("表格AI描述生成完成")
                else:
                    # 即使未启用AI描述，也确保每个表格都有description字段
                    for table in tables:
                        if not table.get("ai_description"):
                            table["ai_description"] = ""
                
                # 生成图片描述（同步调用异步方法）
                if images and settings.ENABLE_IMAGE_DESCRIPTION:
                    app_logger.info(f"开始为 {len(images)} 张图片生成AI描述...")
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        images = loop.run_until_complete(
                            self.description_generator.generate_image_descriptions_batch(images)
                        )
                        # 验证描述已添加到元数据
                        for image in images:
                            if not image.get("ai_description"):
                                app_logger.warning(f"图片 {image.get('index')} 未生成AI描述")
                    finally:
                        loop.close()
                    app_logger.info("图片AI描述生成完成")
                else:
                    # 即使未启用AI描述，也确保每张图片都有description字段
                    for image in images:
                        if not image.get("ai_description"):
                            image["ai_description"] = ""
            
            # 7. 生成Markdown（带元数据）
            markdown_text = self._generate_markdown_with_metadata(text, tables, images)
            
            # 8. 构建结果
            result = {
                "text": text,
                "markdown": markdown_text,
                "tables": tables,
                "images": images,
                "has_images": len(images) > 0,
                "total_pages": model_json.get("total_pages", 0) if isinstance(model_json, dict) else 0,
                "metadata": {
                    "doc_id": doc_id,
                    "parser_type": "mineru",
                    "file_path": file_path,
                    "file_name": Path(file_path).name,
                    "extract_images": extract_images,
                    "table_count": len(tables),
                    "image_count": len(images),
                    "parsed_at": None  # 将在导出时添加时间戳
                }
            }
            
            # 9. 导出数据（如果启用）
            if self.exporter:
                try:
                    self.exporter.export_all(doc_id, result)
                except Exception as e:
                    app_logger.warning(f"数据导出失败: {e}")
            
            app_logger.info(f"PDF解析完成: {doc_id}, 表格={len(tables)}, 图片={len(images)}")
            return result
        
        except Exception as e:
            app_logger.error(f"PDF解析失败: {e}")
            # 返回错误信息
            return {
                "text": "",
                "markdown": "",
                "tables": [],
                "images": [],
                "has_images": False,
                "total_pages": 0,
                "error": str(e),
                "metadata": {
                    "doc_id": doc_id or Path(file_path).stem,
                    "parser_type": "mineru",
                    "file_path": file_path,
                    "error": True
                }
            }

