"""PDF数据导出器 - 多格式导出和缓存管理"""
import json
import csv
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd
from app.config import get_settings
from app.utils.logger import app_logger

settings = get_settings()


class PDFDataExporter:
    """PDF数据导出器"""
    
    def __init__(self):
        """初始化导出器"""
        self.export_dir = Path(settings.PDF_EXPORT_DIR)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self.enabled = settings.ENABLE_PDF_EXPORT
    
    def export_to_csv(self, doc_id: str, data: Dict[str, Any], 
                     tables: Optional[List[Dict]] = None,
                     images: Optional[List[Dict]] = None) -> Dict[str, Path]:
        """
        导出数据到CSV文件
        
        Args:
            doc_id: 文档ID
            data: 主数据字典
            tables: 表格列表
            images: 图片列表
        
        Returns:
            导出的文件路径字典
        """
        if not self.enabled:
            return {}
        
        exported_files = {}
        
        try:
            # 1. 导出主数据
            main_data_file = self.export_dir / f"{doc_id}_pdf_data.csv"
            main_rows = []
            
            # 提取文本块（如果有）
            if "text" in data:
                main_rows.append({
                    "type": "text",
                    "content": data["text"],
                    "page": data.get("metadata", {}).get("page", ""),
                    "index": 0
                })
            
            if main_rows:
                df_main = pd.DataFrame(main_rows)
                df_main.to_csv(main_data_file, index=False, encoding='utf-8-sig')
                exported_files["main_data"] = main_data_file
                app_logger.info(f"主数据已导出: {main_data_file}")
            
            # 2. 导出表格数据
            if tables:
                tables_file = self.export_dir / f"{doc_id}_tables.csv"
                tables_rows = []
                
                for table in tables:
                    tables_rows.append({
                        "page": table.get("page", ""),
                        "index": table.get("index", ""),
                        "title": table.get("title", ""),
                        "html": table.get("html", ""),
                        "description": table.get("ai_description", ""),
                        "bbox": json.dumps(table.get("bbox", {}), ensure_ascii=False)
                    })
                
                if tables_rows:
                    df_tables = pd.DataFrame(tables_rows)
                    df_tables.to_csv(tables_file, index=False, encoding='utf-8-sig')
                    exported_files["tables"] = tables_file
                    app_logger.info(f"表格数据已导出: {tables_file}")
            
            # 3. 导出图片数据
            if images:
                images_file = self.export_dir / f"{doc_id}_images.csv"
                images_rows = []
                
                for image in images:
                    images_rows.append({
                        "page": image.get("page", ""),
                        "index": image.get("index", ""),
                        "title": image.get("title", ""),
                        "path": image.get("path", ""),
                        "description": image.get("ai_description", ""),
                        "context_before": image.get("context_before", ""),
                        "context_after": image.get("context_after", ""),
                        "bbox": json.dumps(image.get("bbox", {}), ensure_ascii=False)
                    })
                
                if images_rows:
                    df_images = pd.DataFrame(images_rows)
                    df_images.to_csv(images_file, index=False, encoding='utf-8-sig')
                    exported_files["images"] = images_file
                    app_logger.info(f"图片数据已导出: {images_file}")
            
            return exported_files
        
        except Exception as e:
            app_logger.error(f"CSV导出失败: {e}")
            return exported_files
    
    def export_metadata_to_json(self, doc_id: str, metadata: Dict[str, Any]) -> Optional[Path]:
        """
        导出元数据到JSON文件
        
        Args:
            doc_id: 文档ID
            metadata: 元数据字典
        
        Returns:
            导出的JSON文件路径，如果失败则返回None
        """
        if not self.enabled:
            return None
        
        try:
            metadata_file = self.export_dir / f"{doc_id}_metadata.json"
            
            # 添加时间戳
            metadata_with_timestamp = {
                **metadata,
                "exported_at": datetime.now().isoformat()
            }
            
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata_with_timestamp, f, ensure_ascii=False, indent=2)
            
            app_logger.info(f"元数据已导出: {metadata_file}")
            return metadata_file
        
        except Exception as e:
            app_logger.error(f"JSON导出失败: {e}")
            return None
    
    def save_to_cache(self, doc_id: str, parsed_data: Dict[str, Any]) -> Path:
        """
        保存解析结果到缓存
        
        Args:
            doc_id: 文档ID
            parsed_data: 解析结果数据
        
        Returns:
            缓存文件路径
        """
        cache_dir = self.export_dir / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        cache_file = cache_dir / f"{doc_id}_parsed.json"
        
        try:
            # 添加时间戳
            cached_data = {
                **parsed_data,
                "cached_at": datetime.now().isoformat()
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cached_data, f, ensure_ascii=False, indent=2)
            
            app_logger.info(f"解析结果已缓存: {cache_file}")
            return cache_file
        
        except Exception as e:
            app_logger.error(f"缓存保存失败: {e}")
            raise
    
    def load_from_cache(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        从缓存加载解析结果
        
        Args:
            doc_id: 文档ID
        
        Returns:
            解析结果数据，如果不存在则返回None
        """
        cache_dir = self.export_dir / "cache"
        cache_file = cache_dir / f"{doc_id}_parsed.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            
            app_logger.info(f"从缓存加载: {cache_file}")
            return cached_data
        
        except Exception as e:
            app_logger.error(f"缓存加载失败: {e}")
            return None
    
    def export_all(self, doc_id: str, parsed_data: Dict[str, Any]) -> Dict[str, Path]:
        """
        导出所有数据（主数据、表格、图片、元数据）
        
        Args:
            doc_id: 文档ID
            parsed_data: 解析结果数据
        
        Returns:
            所有导出文件的路径字典
        """
        exported_files = {}
        
        # 提取数据
        tables = parsed_data.get("tables", [])
        images = parsed_data.get("images", [])
        metadata = parsed_data.get("metadata", {})
        
        # 导出CSV
        csv_files = self.export_to_csv(
            doc_id=doc_id,
            data=parsed_data,
            tables=tables,
            images=images
        )
        exported_files.update(csv_files)
        
        # 导出JSON元数据
        metadata_file = self.export_metadata_to_json(doc_id=doc_id, metadata=metadata)
        if metadata_file:
            exported_files["metadata"] = metadata_file
        
        # 保存到缓存
        try:
            cache_file = self.save_to_cache(doc_id=doc_id, parsed_data=parsed_data)
            exported_files["cache"] = cache_file
        except Exception as e:
            app_logger.warning(f"缓存保存失败: {e}")
        
        return exported_files


# 全局实例
pdf_data_exporter = PDFDataExporter() if settings.ENABLE_PDF_EXPORT else None

