"""咨询Repository"""
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.models.consultation import Consultation, ConsultationStatus, AgentType
from app.infrastructure.repositories.base import BaseRepository


class ConsultationRepository(BaseRepository[Consultation]):
    """咨询Repository"""
    
    def __init__(self, db: Session):
        super().__init__(Consultation, db)
    
    def get_by_user_id(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        status: Optional[ConsultationStatus] = None
    ) -> List[Consultation]:
        """根据用户ID获取咨询记录"""
        try:
            query = self.db.query(Consultation).filter(Consultation.user_id == user_id)
            if status:
                query = query.filter(Consultation.status == status)
            return query.order_by(Consultation.created_at.desc()).offset(skip).limit(limit).all()
        except Exception as e:
            self._handle_error("根据用户ID查询咨询失败", e)
    
    def get_by_agent_type(
        self,
        agent_type: AgentType,
        skip: int = 0,
        limit: int = 100
    ) -> List[Consultation]:
        """根据Agent类型获取咨询记录"""
        try:
            return self.db.query(Consultation)\
                .filter(Consultation.agent_type == agent_type)\
                .order_by(Consultation.created_at.desc())\
                .offset(skip).limit(limit).all()
        except Exception as e:
            self._handle_error("根据Agent类型查询咨询失败", e)
    
    def get_active_consultations(self, user_id: Optional[int] = None) -> List[Consultation]:
        """获取进行中的咨询"""
        try:
            query = self.db.query(Consultation).filter(
                Consultation.status == ConsultationStatus.IN_PROGRESS
            )
            if user_id:
                query = query.filter(Consultation.user_id == user_id)
            return query.order_by(Consultation.created_at.desc()).all()
        except Exception as e:
            self._handle_error("查询进行中的咨询失败", e)
    
    def _handle_error(self, message: str, error: Exception):
        """处理错误"""
        from app.utils.logger import app_logger
        from app.common.exceptions import DatabaseException, ErrorCode
        app_logger.error(f"{message}: {error}")
        raise DatabaseException(f"{message}: {str(error)}", error_code=ErrorCode.DATABASE_ERROR)

