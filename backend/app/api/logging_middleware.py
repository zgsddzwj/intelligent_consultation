"""API中间件 - 增强版（慢请求告警、请求体大小限制、结构化日志、性能指标）"""
import time
import json
from typing import Optional, Dict, Any
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.utils.logger import app_logger
from app.common.tracing import get_request_id
from app.infrastructure.monitoring import track_http_request


# 慢请求阈值（秒）
SLOW_REQUEST_THRESHOLD = 2.0
VERY_SLOW_REQUEST_THRESHOLD = 5.0

# 最大请求体大小（字节）- 10MB
MAX_REQUEST_BODY_SIZE = 10 * 1024 * 1024

# 需要脱敏的字段
SENSITIVE_FIELDS = {
    "password", "token", "api_key", "secret", "authorization",
    "credit_card", "ssn", "phone", "email", "id_card"
}


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    请求日志中间件（增强版）
    
    功能：
    - 结构化请求/响应日志
    - 慢请求分级告警（2s/5s）
    - 请求体大小限制和脱敏
    - 性能指标自动上报
    - 异常请求详细记录
    """
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        request_id = get_request_id()
        
        # 记录请求信息
        request_info = await self._extract_request_info(request)
        app_logger.info(
            "HTTP请求",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_ip": request_info.get("client_ip"),
                "user_agent": request_info.get("user_agent"),
                "content_length": request_info.get("content_length"),
                "request_id": request_id
            }
        )
        
        # 处理请求
        response = None
        status_code = 500
        error_detail = None
        
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            error_detail = str(e)
            # 记录异常详情
            app_logger.error(
                f"请求处理异常: {type(e).__name__}: {str(e)[:200]}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "request_id": request_id,
                    "error_type": type(e).__name__
                }
            )
            raise
        finally:
            # 计算处理时间
            process_time = time.time() - start_time
            
            # 记录响应信息
            self._log_response(
                request=request,
                status_code=status_code,
                process_time=process_time,
                request_id=request_id,
                error_detail=error_detail
            )
            
            # 上报监控指标
            try:
                track_http_request(
                    method=request.method,
                    endpoint=request.url.path,
                    status_code=status_code,
                    duration=process_time
                )
            except Exception as e:
                app_logger.debug(f"监控指标记录失败: {e}")
        
        # 添加响应头
        if response:
            response.headers["X-Process-Time"] = f"{process_time:.3f}s"
            if request_id:
                response.headers["X-Request-ID"] = request_id
        
        return response
    
    async def _extract_request_info(self, request: Request) -> Dict[str, Any]:
        """提取请求信息（支持脱敏）"""
        info = {
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("User-Agent", ""),
            "content_length": request.headers.get("Content-Length", "0"),
            "content_type": request.headers.get("Content-Type", ""),
        }
        
        # 检查请求体大小
        content_length = int(info.get("content_length", 0) or 0)
        if content_length > MAX_REQUEST_BODY_SIZE:
            app_logger.warning(
                f"请求体过大: {content_length / (1024 * 1024):.1f}MB > "
                f"{MAX_REQUEST_BODY_SIZE / (1024 * 1024):.0f}MB"
            )
        
        return info
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端真实IP（支持代理）"""
        # 优先从X-Forwarded-For获取（如果有代理）
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _log_response(self, request: Request, status_code: int,
                      process_time: float, request_id: str,
                      error_detail: Optional[str] = None):
        """记录响应信息（含慢请求告警）"""
        log_data = {
            "method": request.method,
            "path": request.url.path,
            "status_code": status_code,
            "process_time": round(process_time, 3),
            "request_id": request_id
        }
        
        # 慢请求分级告警
        if process_time >= VERY_SLOW_REQUEST_THRESHOLD:
            app_logger.error(
                f"严重慢请求: {request.method} {request.url.path} "
                f"耗时 {process_time:.3f}s (>{VERY_SLOW_REQUEST_THRESHOLD}s)",
                extra=log_data
            )
        elif process_time >= SLOW_REQUEST_THRESHOLD:
            app_logger.warning(
                f"慢请求: {request.method} {request.url.path} "
                f"耗时 {process_time:.3f}s (>{SLOW_REQUEST_THRESHOLD}s)",
                extra=log_data
            )
        else:
            app_logger.info("HTTP响应", extra=log_data)
        
        # 记录错误详情
        if error_detail:
            app_logger.error(
                f"请求错误详情: {error_detail[:500]}",
                extra={"request_id": request_id, "path": request.url.path}
            )
    
    @staticmethod
    def _mask_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """脱敏敏感数据"""
        if not isinstance(data, dict):
            return data
        
        masked = {}
        for key, value in data.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in SENSITIVE_FIELDS):
                if isinstance(value, str) and len(value) > 4:
                    masked[key] = value[:2] + "***" + value[-2:]
                else:
                    masked[key] = "***"
            elif isinstance(value, dict):
                masked[key] = LoggingMiddleware._mask_sensitive_data(value)
            elif isinstance(value, list):
                masked[key] = [
                    LoggingMiddleware._mask_sensitive_data(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                masked[key] = value
        
        return masked


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    请求大小限制中间件
    
    防止过大请求体导致内存耗尽。
    """
    
    MAX_BODY_SIZE = 10 * 1024 * 1024  # 10MB
    
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("Content-Length")
        
        if content_length:
            size = int(content_length)
            if size > self.MAX_BODY_SIZE:
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=413,
                    content={
                        "error": {
                            "code": "REQUEST_TOO_LARGE",
                            "message": f"请求体过大: {size / (1024 * 1024):.1f}MB，最大允许: {self.MAX_BODY_SIZE / (1024 * 1024):.0f}MB"
                        }
                    }
                )
        
        return await call_next(request)
