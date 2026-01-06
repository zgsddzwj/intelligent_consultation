"""迁移到对象存储 - 将现有文档从本地文件系统迁移到对象存储"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.database.session import SessionLocal
from app.models.knowledge import KnowledgeDocument
from app.services.object_storage import object_storage_service
from app.utils.logger import app_logger


def migrate_documents_to_object_storage():
    """将现有文档从本地文件系统迁移到对象存储"""
    db: Session = SessionLocal()
    
    try:
        # 查询所有使用本地文件路径的文档
        documents = db.query(KnowledgeDocument).filter(
            KnowledgeDocument.file_path.isnot(None),
            KnowledgeDocument.object_storage_key.is_(None)
        ).all()
        
        app_logger.info(f"找到 {len(documents)} 个需要迁移的文档")
        
        migrated_count = 0
        failed_count = 0
        
        for doc in documents:
            try:
                file_path = Path(doc.file_path)
                
                # 检查文件是否存在
                if not file_path.exists():
                    app_logger.warning(f"文件不存在，跳过: {doc.file_path}")
                    continue
                
                # 读取文件
                with open(file_path, "rb") as f:
                    file_data = f.read()
                
                # 上传到对象存储
                upload_result = object_storage_service.upload_document(
                    file_data=file_data,
                    filename=file_path.name
                )
                
                # 更新数据库记录
                doc.object_storage_key = upload_result["object_key"]
                doc.storage_type = upload_result["storage_type"]
                doc.storage_bucket = upload_result.get("bucket", "")
                doc.file_size = upload_result["file_size"]
                
                db.commit()
                
                app_logger.info(f"已迁移文档: {doc.title} -> {upload_result['object_key']}")
                migrated_count += 1
                
                # 可选：删除本地文件（谨慎操作）
                # file_path.unlink()
                
            except Exception as e:
                app_logger.error(f"迁移文档失败: {doc.title}, {e}")
                failed_count += 1
                db.rollback()
        
        app_logger.info(f"迁移完成: 成功 {migrated_count} 个, 失败 {failed_count} 个")
        
    except Exception as e:
        app_logger.error(f"迁移过程出错: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    migrate_documents_to_object_storage()

