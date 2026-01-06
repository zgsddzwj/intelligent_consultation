"""用户Repository"""
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.user import User
from app.infrastructure.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """用户Repository"""
    
    def __init__(self, db: Session):
        super().__init__(User, db)
    
    def get_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        try:
            return self.db.query(User).filter(User.email == email).first()
        except Exception as e:
            self._handle_error("根据邮箱查询用户失败", e)
    
    def get_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        try:
            return self.db.query(User).filter(User.username == username).first()
        except Exception as e:
            self._handle_error("根据用户名查询用户失败", e)
    
    def _handle_error(self, message: str, error: Exception):
        """处理错误"""
        from app.utils.logger import app_logger
        from app.common.exceptions import DatabaseException, ErrorCode
        app_logger.error(f"{message}: {error}")
        raise DatabaseException(f"{message}: {str(error)}", error_code=ErrorCode.DATABASE_ERROR)

