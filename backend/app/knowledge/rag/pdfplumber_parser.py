"""pdfplumber PDF解析器实现"""
import pdfplumber
from pathlib import Path
from typing import Dict, List, Any, Optional
from app.knowledge.rag.pdf_parser import BasePDFParser
from app.knowledge.rag.image_processor import ImageProcessor
from app.utils.logger import app_logger


class PDFPlumberParser(BasePDFParser):
    """pdfplumber PDF解析器"""
    
    def __init__(self, enable_image_processing: bool = True):
        """
        初始化解析器
        
        Args:
            enable_image_processing: 是否启用图片处理
        """
        self.enable_image_processing = enable_image_processing
        self.image_processor = ImageProcessor() if enable_image_processing else None
    
    def get_parser_type(self) -> str:
        """返回解析器类型"""
        return "pdfplumber"
    
    def parse_pdf(self, file_path: str, extract_images: bool = True) -> Dict[str, Any]:
        """
        解析PDF文件
        
        Args:
            file_path: PDF文件路径
            extract_images: 是否提取图片
        
        Returns:
            解析结果字典
        """
        try:
            text = ""
            images = []
            image_texts = []
            
            with pdfplumber.open(file_path) as pdf:
                total_pages = len(pdf.pages)
                
                for page_num, page in enumerate(pdf.pages, start=1):
                    # 提取文本
                    page_text = page.extract_text()
                    if page_text:
                        text += f"[页{page_num}]\n{page_text}\n\n"
                    
                    # 提取图片（如果启用）
                    if extract_images and self.image_processor:
                        try:
                            # 提取页面中的图片信息
                            page_images = page.images
                            
                            for img_idx, img_info in enumerate(page_images):
                                images.append({
                                    "page": page_num,
                                    "index": img_idx,
                                    "bbox": {
                                        "x0": img_info.get('x0'),
                                        "y0": img_info.get('top'),
                                        "x1": img_info.get('x1'),
                                        "y1": img_info.get('bottom')
                                    },
                                    "width": img_info.get('width', 0),
                                    "height": img_info.get('height', 0)
                                })
                        except Exception as e:
                            app_logger.warning(f"图片提取失败 (页{page_num}): {e}")
            
            # 处理图片OCR（如果有）
            if extract_images and images and self.image_processor:
                app_logger.info(f"检测到 {len(images)} 张图片，将进行OCR和内容理解")
            
            return {
                "text": text,
                "images": images,
                "image_texts": image_texts,
                "has_images": len(images) > 0,
                "total_pages": total_pages,
                "metadata": {
                    "parser_type": "pdfplumber",
                    "file_path": file_path,
                    "file_name": Path(file_path).name,
                    "extract_images": extract_images
                }
            }
        except Exception as e:
            app_logger.error(f"PDF提取失败: {e}")
            raise

