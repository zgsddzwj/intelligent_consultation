"""图片处理器 - PDF图片提取、OCR识别、多模态理解"""
from typing import List, Dict, Any, Optional
from pathlib import Path
import base64
import io
from PIL import Image
import pdfplumber
from app.utils.logger import app_logger
import dashscope
from dashscope import MultiModalConversation
from app.config import get_settings

settings = get_settings()
dashscope.api_key = settings.QWEN_API_KEY


class ImageProcessor:
    """图片处理器 - 处理PDF中的图片"""
    
    def __init__(self):
        self.ocr_enabled = True
        self.multimodal_enabled = True
        self._init_ocr()
    
    def _init_ocr(self):
        """初始化OCR工具"""
        try:
            # 尝试导入PaddleOCR
            from paddleocr import PaddleOCR
            self.ocr = PaddleOCR(use_angle_cls=True, lang='ch', use_gpu=False)
            self.ocr_enabled = True
            app_logger.info("PaddleOCR初始化成功")
        except ImportError:
            app_logger.warning("PaddleOCR未安装，OCR功能将不可用")
            self.ocr = None
            self.ocr_enabled = False
        except Exception as e:
            app_logger.warning(f"PaddleOCR初始化失败: {e}")
            self.ocr = None
            self.ocr_enabled = False
    
    def extract_images_from_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """从PDF中提取图片"""
        images = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    # 提取页面中的图片
                    page_images = page.images
                    
                    for img_idx, img_info in enumerate(page_images):
                        try:
                            # 获取图片对象
                            img_obj = page.within_bbox(
                                (img_info['x0'], img_info['top'], 
                                 img_info['x1'], img_info['bottom'])
                            )
                            
                            # 转换为PIL Image
                            # 注意：pdfplumber的图片提取可能需要额外处理
                            # 这里简化处理，实际可能需要使用PyMuPDF等库
                            
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
                            app_logger.warning(f"提取图片失败 (页{page_num}, 图{img_idx}): {e}")
            
            app_logger.info(f"从PDF提取了 {len(images)} 张图片")
            return images
            
        except Exception as e:
            app_logger.error(f"PDF图片提取失败: {e}")
            return []
    
    def ocr_image(self, image_path: str) -> Dict[str, Any]:
        """OCR识别图片中的文字"""
        if not self.ocr_enabled or not self.ocr:
            return {"text": "", "confidence": 0.0, "error": "OCR未启用"}
        
        try:
            # 使用PaddleOCR识别
            result = self.ocr.ocr(image_path, cls=True)
            
            text_lines = []
            confidences = []
            
            if result and result[0]:
                for line in result[0]:
                    if line:
                        text_info = line[1]
                        text = text_info[0]
                        confidence = text_info[1]
                        text_lines.append(text)
                        confidences.append(confidence)
            
            full_text = "\n".join(text_lines)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            return {
                "text": full_text,
                "confidence": avg_confidence,
                "lines": text_lines,
                "line_confidences": confidences
            }
            
        except Exception as e:
            app_logger.error(f"OCR识别失败: {e}")
            return {"text": "", "confidence": 0.0, "error": str(e)}
    
    def ocr_image_bytes(self, image_bytes: bytes) -> Dict[str, Any]:
        """OCR识别图片字节"""
        if not self.ocr_enabled or not self.ocr:
            return {"text": "", "confidence": 0.0, "error": "OCR未启用"}
        
        try:
            # 将字节转换为PIL Image
            image = Image.open(io.BytesIO(image_bytes))
            
            # 保存为临时文件或直接使用
            # PaddleOCR可以直接处理PIL Image或numpy array
            import numpy as np
            img_array = np.array(image)
            
            result = self.ocr.ocr(img_array, cls=True)
            
            text_lines = []
            confidences = []
            
            if result and result[0]:
                for line in result[0]:
                    if line:
                        text_info = line[1]
                        text = text_info[0]
                        confidence = text_info[1]
                        text_lines.append(text)
                        confidences.append(confidence)
            
            full_text = "\n".join(text_lines)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            return {
                "text": full_text,
                "confidence": avg_confidence,
                "lines": text_lines,
                "line_confidences": confidences
            }
            
        except Exception as e:
            app_logger.error(f"OCR识别失败: {e}")
            return {"text": "", "confidence": 0.0, "error": str(e)}
    
    def understand_image_with_llm(self, image_path: str, query: str = "请描述这张图片中的医疗相关内容") -> Dict[str, Any]:
        """使用Qwen-VL理解图片内容"""
        if not self.multimodal_enabled:
            return {"description": "", "error": "多模态功能未启用"}
        
        try:
            # 读取图片并转换为base64
            with open(image_path, 'rb') as f:
                image_bytes = f.read()
            
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # 使用Qwen-VL
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "image": f"data:image/jpeg;base64,{image_base64}"
                        },
                        {
                            "text": query
                        }
                    ]
                }
            ]
            
            response = MultiModalConversation.call(
                model="qwen-vl-max",
                messages=messages
            )
            
            if response.status_code == 200:
                description = response.output.choices[0].message.content
                return {
                    "description": description,
                    "model": "qwen-vl-max"
                }
            else:
                return {
                    "description": "",
                    "error": f"Qwen-VL调用失败: {response.message}"
                }
                
        except Exception as e:
            app_logger.error(f"图片理解失败: {e}")
            return {"description": "", "error": str(e)}
    
    def process_image(self, image_path: str, use_ocr: bool = True, use_llm: bool = True) -> Dict[str, Any]:
        """处理图片：OCR + 多模态理解"""
        result = {
            "image_path": image_path,
            "ocr_text": "",
            "llm_description": "",
            "combined_text": ""
        }
        
        # OCR识别
        if use_ocr:
            ocr_result = self.ocr_image(image_path)
            result["ocr_text"] = ocr_result.get("text", "")
            result["ocr_confidence"] = ocr_result.get("confidence", 0.0)
        
        # LLM理解
        if use_llm:
            llm_result = self.understand_image_with_llm(image_path)
            result["llm_description"] = llm_result.get("description", "")
        
        # 合并文本
        text_parts = []
        if result["ocr_text"]:
            text_parts.append(f"[OCR识别]\n{result['ocr_text']}")
        if result["llm_description"]:
            text_parts.append(f"[图片理解]\n{result['llm_description']}")
        
        result["combined_text"] = "\n\n".join(text_parts)
        
        return result
    
    def extract_medical_terms_from_image(self, image_path: str) -> List[str]:
        """从图片中提取医疗术语"""
        # 先OCR识别
        ocr_result = self.ocr_image(image_path)
        ocr_text = ocr_result.get("text", "")
        
        # 再使用LLM理解
        llm_result = self.understand_image_with_llm(
            image_path, 
            "请识别图片中的医疗相关术语，包括疾病名称、症状、药物名称、检查项目等，并以列表形式返回。"
        )
        llm_text = llm_result.get("description", "")
        
        # 合并文本
        combined_text = f"{ocr_text}\n{llm_text}"
        
        # 简单的术语提取（可以改进为NER模型）
        medical_keywords = [
            "疾病", "症状", "药物", "检查", "诊断", "治疗", "高血压", "糖尿病",
            "心脏病", "癌症", "肿瘤", "炎症", "感染", "疼痛", "发热", "咳嗽"
        ]
        
        found_terms = []
        for keyword in medical_keywords:
            if keyword in combined_text:
                found_terms.append(keyword)
        
        return found_terms

