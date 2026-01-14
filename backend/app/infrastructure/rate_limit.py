"""API限流中间件"""
import time
from functools import wraps
from typing import Optional, Callable
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from app.services.redis_service import redis_service
from app.config import get_settings
from app.utils.logger import app_logger
from app.common.exceptions import RateLimitException, ErrorCode

settings = get_settings()


def get_client_identifier(request: Request) -> str:
    """获取客户端标识"""
    # 优先使用用户ID（如果已认证）
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"
    
    # 使用IP地址
    client_ip = request.client.host if request.client else "unknown"
    return f"ip:{client_ip}"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """限流中间件"""
    
    def __init__(
        self,
        app,
        calls: int = 100,  # 允许的请求数
        period: int = 60,  # 时间窗口（秒）
        key_func: Optional[Callable[[Request], str]] = None
    ):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.key_func = key_func or get_client_identifier
    
    async def dispatch(self, request: Request, call_next):
        # 跳过健康检查和文档页面
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json", "/"]:
            return await call_next(request)
        
        # 如果Redis不可用，跳过限流检查（降级策略）
        if not redis_service.enabled:
            return await call_next(request)
        
        # 获取客户端标识
        identifier = self.key_func(request)
        cache_key = f"rate_limit:{identifier}"
        
        try:
            # 获取当前计数
            current = redis_service.get(cache_key)
            current_count = int(current) if current else 0
            
            # 检查是否超过限制
            if current_count >= self.calls:
                app_logger.warning(f"限流触发: {identifier}, 当前计数: {current_count}")
                raise RateLimitException(
                    f"请求过于频繁，请稍后再试。限制: {self.calls} 次/{self.period}秒",
                    error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
                    details={
                        "limit": self.calls,
                        "period": self.period,
                        "retry_after": self.period
                    }
                )
            
            # 增加计数
            if current_count == 0:
                # 第一次请求，设置过期时间
                redis_service.set(cache_key, "1", ttl=self.period)
            else:
                # 增加计数，保持原有TTL
                redis_service.client.incr(cache_key)
            
            # 处理请求
            response = await call_next(request)
            
            # 添加限流头信息
            remaining = self.calls - (current_count + 1)
            response.headers["X-RateLimit-Limit"] = str(self.calls)
            response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
            response.headers["X-RateLimit-Reset"] = str(int(time.time()) + self.period)
            
            return response
            
        except RateLimitException:
            raise
        except Exception as e:
            # 限流中间件出错时，记录警告但不阻塞请求（降级策略）
            app_logger.debug(f"限流中间件错误（已降级）: {e}")
            # 允许请求通过
            return await call_next(request)


def rate_limit(calls: int = 100, period: int = 60, key_func: Optional[Callable[[Request], str]] = None):
    """
    限流装饰器（用于单个路由）
    
    Args:
        calls: 允许的请求数
        period: 时间窗口（秒）
        key_func: 获取客户端标识的函数
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # 如果Redis不可用，跳过限流检查
            if not redis_service.enabled:
                return await func(request, *args, **kwargs)
            
            identifier = (key_func or get_client_identifier)(request)
            cache_key = f"rate_limit:{identifier}:{func.__name__}"
            
            try:
                current = redis_service.get(cache_key)
                current_count = int(current) if current else 0
                
                if current_count >= calls:
                    raise RateLimitException(
                        f"请求过于频繁，请稍后再试",
                        error_code=ErrorCode.RATE_LIMIT_EXCEEDED
                    )
                
                if current_count == 0:
                    redis_service.set(cache_key, "1", ttl=period)
                else:
                    if redis_service.client:
                        redis_service.client.incr(cache_key)
                
                return await func(request, *args, **kwargs)
            except RateLimitException:
                raise
            except Exception as e:
                app_logger.debug(f"限流装饰器错误（已降级）: {e}")
                # 降级：允许请求通过
                return await func(request, *args, **kwargs)
        
        return wrapper
    return decorator

