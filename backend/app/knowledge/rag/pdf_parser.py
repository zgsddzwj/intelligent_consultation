"""PDF解析器接口和工厂"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from pathlib import Path
from app.config import get_settings
from app.utils.logger import app_logger

settings = get_settings()


class BasePDFParser(ABC):
    """PDF解析器抽象基类"""
    
    @abstractmethod
    def parse_pdf(self, file_path: str, extract_images: bool = True) -> Dict[str, Any]:
        """
        解析PDF文件
        
        Args:
            file_path: PDF文件路径
            extract_images: 是否提取图片
        
        Returns:
            解析结果字典，包含：
                - text: 提取的文本
                - images: 图片列表（如果有）
                - tables: 表格列表（如果有）
                - metadata: 元数据
        """
        pass
    
    @abstractmethod
    def get_parser_type(self) -> str:
        """返回解析器类型"""
        pass


class PDFParserFactory:
    """PDF解析器工厂"""
    
    @staticmethod
    def create_parser(parser_type: Optional[str] = None) -> BasePDFParser:
        """
        创建PDF解析器实例
        
        Args:
            parser_type: 解析器类型（"pdfplumber" | "mineru"），如果为None则从配置读取
        
        Returns:
            PDF解析器实例
        """
        if parser_type is None:
            parser_type = settings.PDF_PARSER_TYPE
        
        parser_type = parser_type.lower()
        
        if parser_type == "mineru":
            if not settings.ENABLE_MINERU:
                app_logger.warning("MinerU未启用，回退到pdfplumber")
                parser_type = "pdfplumber"
            else:
                try:
                    from app.knowledge.rag.mineru_parser import MinerUParser
                    return MinerUParser()
                except ImportError as e:
                    app_logger.error(f"无法导入MinerUParser: {e}，回退到pdfplumber")
                    parser_type = "pdfplumber"
        
        if parser_type == "pdfplumber":
            from app.knowledge.rag.pdfplumber_parser import PDFPlumberParser
            return PDFPlumberParser()
        
        raise ValueError(f"不支持的解析器类型: {parser_type}")
    
    @staticmethod
    def create_parser_with_fallback() -> BasePDFParser:
        """
        创建解析器，支持回退机制
        
        Returns:
            PDF解析器实例
        """
        parser_type = settings.PDF_PARSER_TYPE.lower()
        
        if parser_type == "mineru" and settings.ENABLE_MINERU:
            try:
                parser = PDFParserFactory.create_parser("mineru")
                return parser
            except Exception as e:
                app_logger.error(f"MinerU解析器创建失败: {e}")
                if settings.PDF_PARSER_FALLBACK:
                    app_logger.info("回退到pdfplumber解析器")
                    return PDFParserFactory.create_parser("pdfplumber")
                raise
        
        return PDFParserFactory.create_parser(parser_type)

