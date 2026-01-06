"""日志服务"""
from typing import Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.agent import AgentLog, AgentType
from app.utils.logger import app_logger


class LoggingService:
    """日志服务类"""
    
    @staticmethod
    def log_agent_execution(
        db: Session,
        agent_type: str,
        consultation_id: int,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        tools_used: list,
        execution_time: float,
        error_message: str = None
    ):
        """记录Agent执行日志"""
        try:
            agent_log = AgentLog(
                agent_type=AgentType(agent_type),
                consultation_id=consultation_id,
                input_data=input_data,
                output_data=output_data,
                tools_used=tools_used,
                execution_time=f"{execution_time:.3f}",
                error_message=error_message
            )
            db.add(agent_log)
            db.commit()
            app_logger.info(f"Agent执行日志已记录: {agent_type}, 咨询ID: {consultation_id}")
        except Exception as e:
            app_logger.error(f"记录Agent日志失败: {e}")
            db.rollback()
    
    @staticmethod
    def log_api_request(
        method: str,
        path: str,
        status_code: int,
        execution_time: float,
        user_id: int = None
    ):
        """记录API请求日志"""
        log_data = {
            "method": method,
            "path": path,
            "status_code": status_code,
            "execution_time": f"{execution_time:.3f}s",
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        }
        app_logger.info(f"API请求: {log_data}")
    
    @staticmethod
    def log_error(
        error_type: str,
        error_message: str,
        context: Dict[str, Any] = None
    ):
        """记录错误日志"""
        log_data = {
            "error_type": error_type,
            "error_message": error_message,
            "context": context or {},
            "timestamp": datetime.now().isoformat()
        }
        app_logger.error(f"错误日志: {log_data}")

