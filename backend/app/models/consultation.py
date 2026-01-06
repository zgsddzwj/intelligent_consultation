"""咨询记录模型"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.database.base import Base


class ConsultationStatus(str, enum.Enum):
    """咨询状态枚举"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AgentType(str, enum.Enum):
    """Agent类型枚举"""
    DOCTOR = "doctor"
    HEALTH_MANAGER = "health_manager"
    CUSTOMER_SERVICE = "customer_service"
    OPERATIONS = "operations"


class Consultation(Base):
    """咨询记录表"""
    __tablename__ = "consultations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    agent_type = Column(Enum(AgentType), nullable=False)
    status = Column(Enum(ConsultationStatus), default=ConsultationStatus.PENDING, nullable=False)
    messages = Column(JSON, default=list)  # 存储对话消息
    meta_data = Column("metadata", JSON, default=dict)  # 存储额外信息（如风险等级、来源等）
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    user = relationship("User", backref="consultations")

