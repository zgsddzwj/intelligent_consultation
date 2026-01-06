"""知识库Repository"""
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.knowledge import KnowledgeDocument
from app.infrastructure.repositories.base import BaseRepository


class KnowledgeRepository(BaseRepository[KnowledgeDocument]):
    """知识库Repository"""
    
    def __init__(self, db: Session):
        super().__init__(KnowledgeDocument, db)
    
    def get_by_source(self, source: str) -> List[KnowledgeDocument]:
        """根据来源获取文档"""
        try:
            return self.db.query(KnowledgeDocument)\
                .filter(KnowledgeDocument.source == source)\
                .all()
        except Exception as e:
            self._handle_error("根据来源查询文档失败", e)
    
    def search_by_title(self, keyword: str) -> List[KnowledgeDocument]:
        """根据标题关键词搜索"""
        try:
            return self.db.query(KnowledgeDocument)\
                .filter(KnowledgeDocument.title.contains(keyword))\
                .all()
        except Exception as e:
            self._handle_error("根据标题搜索文档失败", e)
    
    def _handle_error(self, message: str, error: Exception):
        """处理错误"""
        from app.utils.logger import app_logger
        from app.common.exceptions import DatabaseException, ErrorCode
        app_logger.error(f"{message}: {error}")
        raise DatabaseException(f"{message}: {str(error)}", error_code=ErrorCode.DATABASE_ERROR)

