"""文档处理器"""
import pdfplumber
from docx import Document
from pathlib import Path
from typing import List, Dict, Any
import re
from app.utils.logger import app_logger


class DocumentProcessor:
    """文档处理器"""
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """从PDF提取文本"""
        try:
            text = ""
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return text
        except Exception as e:
            app_logger.error(f"PDF提取失败: {e}")
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
    
    def extract_text(self, file_path: str) -> str:
        """根据文件类型提取文本"""
        path = Path(file_path)
        suffix = path.suffix.lower()
        
        if suffix == ".pdf":
            return self.extract_text_from_pdf(file_path)
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
    
    def process_document(self, file_path: str, source: str = "", metadata: Dict = None) -> List[Dict[str, Any]]:
        """处理文档：提取文本并分块"""
        app_logger.info(f"处理文档: {file_path}")
        
        # 提取文本
        text = self.extract_text(file_path)
        
        # 更新元数据
        doc_metadata = metadata or {}
        doc_metadata["file_path"] = file_path
        doc_metadata["file_name"] = Path(file_path).name
        
        # 分块
        chunks = self.split_text(text, source, doc_metadata)
        
        app_logger.info(f"文档处理完成，生成 {len(chunks)} 个文本块")
        return chunks

