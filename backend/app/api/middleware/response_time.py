"""API响应时间监控中间件

记录每个API请求的响应时间，并记录慢请求告警
"""
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.utils.logger import app_logger, get_request_id


class ResponseTimeMiddleware(BaseHTTPMiddleware):
    """响应时间监控中间件
    
    记录API请求的响应时间，对慢请求进行告警
    """
    
    def __init__(self, app, slow_threshold: float = 1.0):
        super().__init__(app)
        self.slow_threshold = slow_threshold  # 慢请求阈值（秒）
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        request_id = get_request_id()
        
        try:
            response = await call_next(request)
            
            # 计算响应时间
            duration = time.time() - start_time
            
            # 添加到响应头
            response.headers["X-Response-Time"] = f"{duration:.3f}s"
            response.headers["X-Request-ID"] = request_id
            
            # 记录慢请求
            if duration > self.slow_threshold:
                app_logger.warning(
                    f"慢请求告警 | {request.method} {request.url.path} | "
                    f"耗时: {duration:.3f}s | 请求ID: {request_id}"
                )
            else:
                app_logger.info(
                    f"{request.method} {request.url.path} | "
                    f"耗时: {duration:.3f}s | 状态: {response.status_code} | "
                    f"请求ID: {request_id}"
                )
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            app_logger.error(
                f"请求异常 | {request.method} {request.url.path} | "
                f"耗时: {duration:.3f}s | 错误: {str(e)} | "
                f"请求ID: {request_id}"
            )
            raise
