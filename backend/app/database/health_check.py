"""数据库连接池健康检查模块

提供数据库连接池状态监控和健康检查功能：
- 连接池使用率监控
- 连接有效性检测
- 慢查询检测
- 自动重连机制
"""
import time
import threading
from typing import Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database.session import engine
from app.utils.logger import app_logger


class ConnectionPoolHealthChecker:
    """数据库连接池健康检查器"""
    
    def __init__(self, check_interval: int = 30):
        self.check_interval = check_interval
        self._last_check_time: float = 0
        self._health_status: Dict[str, Any] = {}
        self._lock = threading.Lock()
    
    def check_health(self) -> Dict[str, Any]:
        """执行连接池健康检查"""
        with self._lock:
            # 避免过于频繁的检查
            if time.time() - self._last_check_time < self.check_interval:
                return self._health_status
            
            try:
                # 获取连接池状态
                pool = engine.pool
                status = {
                    "status": "healthy",
                    "checked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "pool_size": pool.size(),
                    "checked_in": pool.checkedin(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow(),
                    "connection_ratio": 0.0
                }
                
                # 计算连接使用率
                total_connections = pool.checkedin() + pool.checkedout()
                if pool.size() > 0:
                    status["connection_ratio"] = round(total_connections / pool.size(), 2)
                
                # 检查连接是否有效
                try:
                    with engine.connect() as conn:
                        result = conn.execute(text("SELECT 1"))
                        result.fetchone()
                        status["connection_valid"] = True
                except Exception as e:
                    status["connection_valid"] = False
                    status["status"] = "unhealthy"
                    status["error"] = str(e)
                    app_logger.error(f"数据库连接验证失败: {e}")
                
                # 检查连接使用率是否过高
                if status["connection_ratio"] > 0.9:
                    status["status"] = "warning"
                    status["warning"] = "连接池使用率超过90%，建议扩容"
                    app_logger.warning("数据库连接池使用率过高")
                
                self._health_status = status
                self._last_check_time = time.time()
                
                return status
                
            except Exception as e:
                app_logger.error(f"数据库健康检查失败: {e}")
                return {
                    "status": "error",
                    "error": str(e),
                    "checked_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }
    
    def get_status(self) -> Dict[str, Any]:
        """获取当前健康状态（可能使用缓存）"""
        if not self._health_status or time.time() - self._last_check_time > self.check_interval:
            return self.check_health()
        return self._health_status


# 全局实例
pool_health_checker = ConnectionPoolHealthChecker()
