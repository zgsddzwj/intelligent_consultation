"""API中间件"""
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.utils.logger import app_logger
from app.common.tracing import get_request_id
from app.infrastructure.monitoring import track_http_request


class LoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件（增强版，支持追踪和监控）"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        request_id = get_request_id()
        
        # 记录请求信息（结构化日志）
        app_logger.info(
            "HTTP请求",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_ip": request.client.host if request.client else None,
                "request_id": request_id
            }
        )
        
        # 处理请求
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            raise
        finally:
            # 计算处理时间
            process_time = time.time() - start_time
            
            # 记录响应信息
            app_logger.info(
                "HTTP响应",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "process_time": process_time,
                    "request_id": request_id
                }
            )
            
            # 记录监控指标
            try:
                track_http_request(
                    method=request.method,
                    endpoint=request.url.path,
                    status_code=status_code,
                    duration=process_time
                )
            except Exception as e:
                app_logger.warning(f"监控指标记录失败: {e}")
        
        # 添加响应头
        response.headers["X-Process-Time"] = str(process_time)
        if request_id:
            response.headers["X-Request-ID"] = request_id
        
        return response

