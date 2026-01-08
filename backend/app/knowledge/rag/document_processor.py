"""文档处理器 - 增强版，支持PDF图片解析"""
import pdfplumber
from docx import Document
from pathlib import Path
from typing import List, Dict, Any, Optional
import re
from app.utils.logger import app_logger
from app.knowledge.rag.image_processor import ImageProcessor
from app.knowledge.rag.pdf_parser import PDFParserFactory


class DocumentProcessor:
    """文档处理器"""
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50, 
                 enable_image_processing: bool = True):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.enable_image_processing = enable_image_processing
        self.image_processor = ImageProcessor() if enable_image_processing else None
        # 初始化PDF解析器（支持MinerU和pdfplumber）
        try:
            self.pdf_parser = PDFParserFactory.create_parser_with_fallback()
        except Exception as e:
            app_logger.warning(f"PDF解析器初始化失败，使用默认pdfplumber: {e}")
            from app.knowledge.rag.pdfplumber_parser import PDFPlumberParser
            self.pdf_parser = PDFPlumberParser(enable_image_processing=enable_image_processing)
    
    def extract_text_from_pdf(self, file_path: str, extract_images: bool = True) -> Dict[str, Any]:
        """从PDF提取文本和图片（使用配置的PDF解析器）"""
        try:
            # 使用PDF解析器工厂创建的解析器
            parser_result = self.pdf_parser.parse_pdf(file_path, extract_images=extract_images)
            
            # 转换结果格式以保持向后兼容
            text = parser_result.get("text", "")
            images = parser_result.get("images", [])
            
            # 处理图片文本（如果有AI描述）
            image_texts = []
            if images and extract_images:
                for img_info in images:
                    if img_info.get("ai_description"):
                        image_texts.append(img_info.get("ai_description"))
                    elif img_info.get("description"):
                        image_texts.append(img_info.get("description"))
            
            # 如果使用MinerU解析器，尝试使用markdown格式
            if parser_result.get("markdown") and self.pdf_parser.get_parser_type() == "mineru":
                # 可以选择使用markdown格式的文本
                text = parser_result.get("markdown", text)
            
            return {
                "text": text,
                "image_texts": image_texts,
                "has_images": len(images) > 0 or parser_result.get("has_images", False),
                "tables": parser_result.get("tables", []),
                "images": images,
                "metadata": parser_result.get("metadata", {})
            }
        except Exception as e:
            app_logger.error(f"PDF提取失败: {e}")
            # 如果失败且有错误结果，返回错误信息
            if hasattr(e, 'error') and isinstance(e.error, dict):
                return {
                    "text": "",
                    "image_texts": [],
                    "has_images": False,
                    "error": str(e)
                }
            raise
    
    def extract_text_from_docx(self, file_path: str) -> str:
        """从Word文档提取文本"""
        try:
            doc = Document(file_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text
        except Exception as e:
            app_logger.error(f"Word文档提取失败: {e}")
            raise
    
    def extract_text(self, file_path: str, extract_images: bool = True) -> str:
        """根据文件类型提取文本（兼容旧接口）"""
        path = Path(file_path)
        suffix = path.suffix.lower()
        
        if suffix == ".pdf":
            result = self.extract_text_from_pdf(file_path, extract_images)
            # 合并文本和图片文本
            text = result["text"]
            if result.get("image_texts"):
                text += "\n\n[图片内容]\n" + "\n\n".join(result["image_texts"])
            return text
        elif suffix in [".docx", ".doc"]:
            return self.extract_text_from_docx(file_path)
        else:
            raise ValueError(f"不支持的文件类型: {suffix}")
    
    def split_text(self, text: str, source: str = "", metadata: Dict = None) -> List[Dict[str, Any]]:
        """智能分块"""
        # 按段落分割
        paragraphs = re.split(r'\n\s*\n', text)
        
        chunks = []
        current_chunk = ""
        current_metadata = metadata or {}
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # 如果当前块加上新段落超过大小，保存当前块
            if len(current_chunk) + len(para) > self.chunk_size and current_chunk:
                chunks.append({
                    "text": current_chunk.strip(),
                    "source": source,
                    "metadata": {**current_metadata, "chunk_index": len(chunks)}
                })
                # 保留重叠部分
                overlap_text = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else current_chunk
                current_chunk = overlap_text + " " + para
            else:
                current_chunk += " " + para if current_chunk else para
        
        # 添加最后一个块
        if current_chunk:
            chunks.append({
                "text": current_chunk.strip(),
                "source": source,
                "metadata": {**current_metadata, "chunk_index": len(chunks)}
            })
        
        return chunks
    
    def process_document(self, file_path: str, source: str = "", metadata: Dict = None, 
                        extract_images: bool = True) -> List[Dict[str, Any]]:
        """处理文档：提取文本和图片，并分块"""
        app_logger.info(f"处理文档: {file_path}")
        
        # 提取文本（包括图片）
        path = Path(file_path)
        suffix = path.suffix.lower()
        
        if suffix == ".pdf":
            # PDF文件，使用新的PDF解析器
            pdf_result = self.extract_text_from_pdf(file_path, extract_images=extract_images)
            text = pdf_result["text"]
            
            # 处理图片和表格（如果有）
            if pdf_result.get("has_images"):
                app_logger.info(f"检测到PDF中的图片，数量: {len(pdf_result.get('images', []))}")
            if pdf_result.get("tables"):
                app_logger.info(f"检测到PDF中的表格，数量: {len(pdf_result.get('tables', []))}")
        else:
            # 其他文件类型或图片处理未启用
            text = self.extract_text(file_path, extract_images=False)
        
        # 更新元数据
        doc_metadata = metadata or {}
        doc_metadata["file_path"] = file_path
        doc_metadata["file_name"] = Path(file_path).name
        doc_metadata["has_images"] = extract_images and suffix == ".pdf"
        
        # 分块
        chunks = self.split_text(text, source, doc_metadata)
        
        app_logger.info(f"文档处理完成，生成 {len(chunks)} 个文本块")
        return chunks
    
    def process_document_from_storage(self, object_key: str, source: str = "", 
                                     metadata: Dict = None, 
                                     extract_images: bool = True) -> List[Dict[str, Any]]:
        """
        从对象存储处理文档
        
        Args:
            object_key: 对象存储键
            source: 文档来源
            metadata: 元数据
            extract_images: 是否提取图片
        
        Returns:
            文档块列表
        """
        temp_file_path = None
        try:
            # 1. 从对象存储下载文件到临时位置
            file_data = object_storage_service.download_document(object_key)
            
            # 2. 保存到临时文件
            file_ext = Path(object_key).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
                temp_file.write(file_data)
                temp_file_path = temp_file.name
            
            # 3. 处理文档（使用现有方法）
            chunks = self.process_document(temp_file_path, source, metadata, extract_images)
            
            # 4. 更新元数据，添加对象存储信息
            for chunk in chunks:
                chunk["metadata"]["object_storage_key"] = object_key
                chunk["metadata"]["storage_type"] = object_storage_service.storage_type
            
            return chunks
            
        except Exception as e:
            app_logger.error(f"从对象存储处理文档失败: {object_key}, {e}")
            raise
        finally:
            # 5. 清理临时文件
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except Exception as e:
                    app_logger.warning(f"清理临时文件失败: {temp_file_path}, {e}")

