"""结构感知分块器 - 基于标题层级和文档结构的智能分块"""
import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from app.utils.logger import app_logger


class StructureAwareChunker:
    """结构感知分块器"""
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        """
        初始化分块器
        
        Args:
            chunk_size: 文本块大小（字符数）
            chunk_overlap: 块之间重叠大小（字符数）
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # 标题模式：Markdown格式
        self.h1_pattern = re.compile(r'^#\s+(.+)$', re.MULTILINE)
        self.h2_pattern = re.compile(r'^##\s+(.+)$', re.MULTILINE)
        
        # 标题模式：HTML格式
        self.h1_html_pattern = re.compile(r'<h1[^>]*>(.*?)</h1>', re.IGNORECASE | re.DOTALL)
        self.h2_html_pattern = re.compile(r'<h2[^>]*>(.*?)</h2>', re.IGNORECASE | re.DOTALL)
    
    def parse_structure(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析文档结构
        
        Args:
            content: 包含text、tables、images的字典
        
        Returns:
            结构字典，包含：
            - headings: 标题列表（按顺序，包含层级和位置）
            - tables: 表格列表（包含位置信息）
            - images: 图片列表（包含位置信息）
            - text_sections: 文本段落列表
        """
        text = content.get("text", "") or content.get("markdown", "")
        tables = content.get("tables", [])
        images = content.get("images", [])
        
        # 1. 解析标题（Markdown和HTML格式）
        headings = self._extract_headings(text)
        
        # 2. 标记表格和图片位置（在文本中的位置）
        table_positions = self._mark_positions(text, tables, "table")
        image_positions = self._mark_positions(text, images, "image")
        
        # 3. 提取文本段落
        text_sections = self._extract_text_sections(text)
        
        return {
            "headings": headings,
            "tables": table_positions,
            "images": image_positions,
            "text_sections": text_sections,
            "raw_text": text
        }
    
    def _extract_headings(self, text: str) -> List[Dict[str, Any]]:
        """
        提取标题
        
        Args:
            text: 文本内容
        
        Returns:
            标题列表，每个标题包含：
            - level: 层级（1或2）
            - text: 标题文本
            - position: 在文本中的位置（字符索引）
        """
        headings = []
        
        # 提取Markdown格式标题
        for match in self.h1_pattern.finditer(text):
            headings.append({
                "level": 1,
                "text": match.group(1).strip(),
                "position": match.start(),
                "format": "markdown"
            })
        
        for match in self.h2_pattern.finditer(text):
            headings.append({
                "level": 2,
                "text": match.group(1).strip(),
                "position": match.start(),
                "format": "markdown"
            })
        
        # 提取HTML格式标题
        for match in self.h1_html_pattern.finditer(text):
            headings.append({
                "level": 1,
                "text": re.sub(r'<[^>]+>', '', match.group(1)).strip(),
                "position": match.start(),
                "format": "html"
            })
        
        for match in self.h2_html_pattern.finditer(text):
            headings.append({
                "level": 2,
                "text": re.sub(r'<[^>]+>', '', match.group(1)).strip(),
                "position": match.start(),
                "format": "html"
            })
        
        # 按位置排序
        headings.sort(key=lambda x: x["position"])
        
        return headings
    
    def _mark_positions(self, text: str, elements: List[Dict], element_type: str) -> List[Dict[str, Any]]:
        """
        标记元素在文本中的位置
        
        Args:
            text: 文本内容
            elements: 元素列表（表格或图片）
            element_type: 元素类型（"table"或"image"）
        
        Returns:
            带位置信息的元素列表
        """
        marked_elements = []
        
        for element in elements:
            element_copy = element.copy()
            element_copy["element_type"] = element_type
            
            # 尝试在文本中查找元素引用
            title = element.get("title", "")
            page = element.get("page", 0)
            
            # 使用标题或页码在文本中查找位置
            position = -1
            if title:
                # 查找标题在文本中的位置
                title_pos = text.find(title)
                if title_pos >= 0:
                    position = title_pos
                else:
                    # 如果标题没找到，尝试查找相关关键词
                    keywords = title.split()[:3]  # 取前三个词
                    for keyword in keywords:
                        if len(keyword) > 2:
                            pos = text.find(keyword)
                            if pos >= 0:
                                position = pos
                                break
            
            # 如果还是没找到，使用页码估算位置
            if position < 0 and page > 0:
                # 粗略估算：假设每页约2000字符
                position = (page - 1) * 2000
            
            element_copy["position"] = position
            marked_elements.append(element_copy)
        
        # 按位置排序
        marked_elements.sort(key=lambda x: (x.get("page", 0), x.get("position", 0)))
        
        return marked_elements
    
    def _extract_text_sections(self, text: str) -> List[Dict[str, Any]]:
        """
        提取文本段落
        
        Args:
            text: 文本内容
        
        Returns:
            文本段落列表
        """
        # 按段落分割
        paragraphs = re.split(r'\n\s*\n', text)
        
        sections = []
        current_pos = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # 跳过标题行（已经单独处理）
            if self.h1_pattern.match(para) or self.h2_pattern.match(para):
                continue
            
            sections.append({
                "text": para,
                "position": current_pos,
                "length": len(para)
            })
            
            current_pos += len(para) + 2  # +2 for newline
            
        return sections
    
    def chunk_by_structure(self, structure: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        按结构分块
        
        Args:
            structure: 结构字典（由parse_structure返回）
        
        Returns:
            分块列表
        """
        chunks = []
        headings = structure.get("headings", [])
        tables = structure.get("tables", [])
        images = structure.get("images", [])
        text_sections = structure.get("text_sections", [])
        raw_text = structure.get("raw_text", "")
        
        # 如果没有标题，使用简单分块
        if not headings:
            return self._simple_chunk_with_elements(text_sections, tables, images)
        
        # 按标题层级分块
        current_h1 = None
        current_h2 = None
        current_chunk_text = []
        current_chunk_elements = []
        processed_text_positions = set()  # 跟踪已处理的文本位置
        
        # 将所有元素（标题、表格、图片）合并并按位置排序
        all_elements = []
        
        # 添加标题
        for heading in headings:
            all_elements.append({
                "type": "heading",
                "level": heading["level"],
                "data": heading,
                "position": heading["position"]
            })
        
        # 添加表格
        for table in tables:
            all_elements.append({
                "type": "table",
                "level": 0,  # 表格不分级
                "data": table,
                "position": table.get("position", 0)
            })
        
        # 添加图片
        for image in images:
            all_elements.append({
                "type": "image",
                "level": 0,  # 图片不分级
                "data": image,
                "position": image.get("position", 0)
            })
        
        # 添加文本段落（关联到最近的标题）
        for text_section in text_sections:
            all_elements.append({
                "type": "text",
                "level": 0,  # 文本段落不分级
                "data": text_section,
                "position": text_section.get("position", 0)
            })
        
        # 按位置排序
        all_elements.sort(key=lambda x: x["position"])
        
        # 处理每个元素
        for i, element in enumerate(all_elements):
            element_type = element["type"]
            element_data = element["data"]
            element_position = element.get("position", 0)
            
            if element_type == "heading":
                level = element["level"]
                heading_text = element_data["text"]
                
                # 如果遇到新的H1，保存当前块
                if level == 1:
                    if current_h1 and current_chunk_text:
                        chunk_list = self._create_chunk(
                            title=f"# {current_h1}",
                            text="\n\n".join(current_chunk_text),
                            elements=current_chunk_elements,
                            level=1
                        )
                        chunks.extend(chunk_list)
                    
                    # 开始新的H1块
                    current_h1 = heading_text
                    current_h2 = None
                    current_chunk_text = []
                    current_chunk_elements = []
                
                # 如果遇到新的H2，保存当前H2块（如果有）
                elif level == 2:
                    if current_h2 and current_chunk_text:
                        chunk_list = self._create_chunk(
                            title=f"## {current_h2}",
                            text="\n\n".join(current_chunk_text),
                            elements=current_chunk_elements,
                            level=2,
                            parent_title=current_h1
                        )
                        chunks.extend(chunk_list)
                    
                    # 开始新的H2块
                    current_h2 = heading_text
                    current_chunk_text = []
                    current_chunk_elements = []
            
            elif element_type == "table":
                # 表格单独成块（不依赖标题）
                table_chunk = self._create_table_chunk(element_data, current_h1, current_h2)
                chunks.append(table_chunk)
            
            elif element_type == "image":
                # 图片单独成块（不依赖标题）
                image_chunk = self._create_image_chunk(element_data, current_h1, current_h2)
                chunks.append(image_chunk)
            
            elif element_type == "text":
                # 文本段落添加到当前块（如果有标题）
                text_content = element_data.get("text", "")
                text_position = element_data.get("position", 0)
                
                if text_content and text_position not in processed_text_positions:
                    # 只有当有当前标题时才添加到块中
                    if current_h1 or current_h2:
                        current_chunk_text.append(text_content)
                        processed_text_positions.add(text_position)
        
        # 保存最后一个块
        if current_chunk_text:
            if current_h2:
                chunk_list = self._create_chunk(
                    title=f"## {current_h2}",
                    text="\n\n".join(current_chunk_text),
                    elements=current_chunk_elements,
                    level=2,
                    parent_title=current_h1
                )
            elif current_h1:
                chunk_list = self._create_chunk(
                    title=f"# {current_h1}",
                    text="\n\n".join(current_chunk_text),
                    elements=current_chunk_elements,
                    level=1
                )
            else:
                # 没有标题，使用简单分块
                chunk_list = self._create_chunk(
                    title="",
                    text="\n\n".join(current_chunk_text),
                    elements=current_chunk_elements,
                    level=0
                )
            chunks.extend(chunk_list)
        
        # 处理剩余的文本段落（没有标题的，且未被处理）
        remaining_text_parts = []
        for text_section in text_sections:
            text_position = text_section.get("position", 0)
            if text_position not in processed_text_positions:
                remaining_text_parts.append(text_section.get("text", ""))
        
        if remaining_text_parts:
            remaining_text = "\n\n".join(remaining_text_parts)
            remaining_chunks = self.chunk_text_with_sliding_window(remaining_text, metadata={
                "chunk_type": "text",
                "has_title": False
            })
            chunks.extend(remaining_chunks)
        
        return chunks
    
    def _simple_chunk_with_elements(self, text_sections: List[Dict], 
                                   tables: List[Dict], images: List[Dict]) -> List[Dict[str, Any]]:
        """简单分块（没有标题时的降级方案）"""
        chunks = []
        
        # 表格单独成块
        for table in tables:
            chunks.append(self._create_table_chunk(table))
        
        # 图片单独成块
        for image in images:
            chunks.append(self._create_image_chunk(image))
        
        # 文本使用滑动窗口分块
        text = "\n\n".join([sec["text"] for sec in text_sections])
        text_chunks = self.chunk_text_with_sliding_window(text)
        chunks.extend(text_chunks)
        
        # 按位置排序
        chunks.sort(key=lambda x: (x.get("metadata", {}).get("page", 0), x.get("metadata", {}).get("position", 0)))
        
        return chunks
    
    def chunk_text_with_sliding_window(self, text: str, metadata: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        文本块滑动窗口分割
        
        Args:
            text: 文本内容
            metadata: 元数据
        
        Returns:
            文本块列表
        """
        if not text:
            return []
        
        chunks = []
        metadata = metadata or {}
        
        # 按段落分割
        paragraphs = re.split(r'\n\s*\n', text)
        
        current_chunk = ""
        chunk_index = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # 如果当前块加上新段落超过大小，保存当前块
            if current_chunk and len(current_chunk) + len(para) > self.chunk_size:
                chunks.append({
                    "text": current_chunk.strip(),
                    "chunk_type": "text",
                    "metadata": {
                        **metadata,
                        "chunk_index": chunk_index,
                        "chunk_size": len(current_chunk)
                    }
                })
                chunk_index += 1
                
                # 保留重叠部分
                if len(current_chunk) > self.chunk_overlap:
                    overlap_text = current_chunk[-self.chunk_overlap:]
                    current_chunk = overlap_text + "\n\n" + para
                else:
                    current_chunk = para
            else:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
        
        # 添加最后一个块
        if current_chunk:
            chunks.append({
                "text": current_chunk.strip(),
                "chunk_type": "text",
                "metadata": {
                    **metadata,
                    "chunk_index": chunk_index,
                    "chunk_size": len(current_chunk)
                }
            })
        
        return chunks
    
    def _create_chunk(self, title: str, text: str, elements: List[Dict], 
                     level: int, parent_title: Optional[str] = None) -> List[Dict[str, Any]]:
        """创建文本块（可能返回多个块，如果文本过长则使用滑动窗口分割）"""
        chunks = []
        
        # 合并文本
        full_text = title + "\n\n" + text if title else text
        
        # 如果文本过长，使用滑动窗口分割
        if len(full_text) > self.chunk_size:
            # 先创建标题块（如果有）
            if title:
                chunks.append({
                    "text": title,
                    "chunk_type": "text",
                    "title": title,
                    "level": level,
                    "parent_title": parent_title,
                    "metadata": {
                        "is_title": True,
                        "has_elements": len(elements) > 0,
                        "element_count": len(elements)
                    }
                })
            
            # 对正文使用滑动窗口分割
            text_chunks = self.chunk_text_with_sliding_window(text, metadata={
                "title": title,
                "level": level,
                "parent_title": parent_title,
                "has_elements": len(elements) > 0
            })
            chunks.extend(text_chunks)
        else:
            # 文本不长，直接创建一个块
            chunks.append({
                "text": full_text.strip(),
                "chunk_type": "text",
                "title": title,
                "level": level,
                "parent_title": parent_title,
                "metadata": {
                    "has_elements": len(elements) > 0,
                    "element_count": len(elements)
                }
            })
        
        return chunks
    
    def _create_table_chunk(self, table: Dict, parent_h1: Optional[str] = None, 
                           parent_h2: Optional[str] = None) -> Dict[str, Any]:
        """创建表格块"""
        table_title = table.get("title", "表格")
        table_html = table.get("html", "")
        table_description = table.get("ai_description", "")
        table_page = table.get("page", 0)
        
        # 构建表格块文本
        text_parts = []
        if parent_h1:
            text_parts.append(f"# {parent_h1}")
        if parent_h2:
            text_parts.append(f"## {parent_h2}")
        text_parts.append(f"### {table_title}")
        if table_description:
            text_parts.append(f"*描述：{table_description}*")
        text_parts.append(table_html)
        
        return {
            "text": "\n\n".join(text_parts),
            "chunk_type": "table",
            "title": table_title,
            "level": 0,
            "parent_title": parent_h1 or parent_h2,
            "metadata": {
                "page": table_page,
                "index": table.get("index", 0),
                "table_html": table_html,
                "ai_description": table_description,
                "bbox": table.get("bbox", {})
            }
        }
    
    def _create_image_chunk(self, image: Dict, parent_h1: Optional[str] = None, 
                           parent_h2: Optional[str] = None) -> Dict[str, Any]:
        """创建图片块"""
        image_title = image.get("title", "图片")
        image_path = image.get("path", "")
        image_description = image.get("ai_description", "")
        context_before = image.get("context_before", "")
        context_after = image.get("context_after", "")
        image_page = image.get("page", 0)
        
        # 构建图片块文本
        text_parts = []
        if parent_h1:
            text_parts.append(f"# {parent_h1}")
        if parent_h2:
            text_parts.append(f"## {parent_h2}")
        text_parts.append(f"### {image_title}")
        
        if context_before:
            text_parts.append(f"*前文：{context_before}*")
        
        text_parts.append(f"![{image_title}]({image_path})")
        
        if image_description:
            text_parts.append(f"*描述：{image_description}*")
        
        if context_after:
            text_parts.append(f"*后文：{context_after}*")
        
        return {
            "text": "\n\n".join(text_parts),
            "chunk_type": "image",
            "title": image_title,
            "level": 0,
            "parent_title": parent_h1 or parent_h2,
            "metadata": {
                "page": image_page,
                "index": image.get("index", 0),
                "image_path": image_path,
                "ai_description": image_description,
                "context_before": context_before,
                "context_after": context_after,
                "bbox": image.get("bbox", {})
            }
        }
    

