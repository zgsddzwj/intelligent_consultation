"""Agent配置模型"""
from sqlalchemy import Column, Integer, String, DateTime, JSON, Enum
from sqlalchemy.sql import func
import enum
from app.database.base import Base


class AgentType(str, enum.Enum):
    """Agent类型枚举"""
    DOCTOR = "doctor"
    HEALTH_MANAGER = "health_manager"
    CUSTOMER_SERVICE = "customer_service"
    OPERATIONS = "operations"


class AgentLog(Base):
    """Agent日志表"""
    __tablename__ = "agent_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_type = Column(Enum(AgentType), nullable=False, index=True)
    consultation_id = Column(Integer, nullable=True, index=True)  # 关联咨询ID
    input_data = Column(JSON, nullable=False)  # 输入数据
    output_data = Column(JSON, nullable=True)  # 输出数据
    tools_used = Column(JSON, default=list)  # 使用的工具列表
    execution_time = Column(String(20), nullable=True)  # 执行时间（秒）
    error_message = Column(String(500), nullable=True)  # 错误信息
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

