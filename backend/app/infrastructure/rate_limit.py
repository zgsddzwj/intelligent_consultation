"""API限流中间件 - 增强版（Lua脚本原子操作、滑动窗口、自适应降级）"""
import time
import asyncio
from functools import wraps
from typing import Optional, Callable, Tuple
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from app.services.redis_service import redis_service
from app.config import get_settings
from app.utils.logger import app_logger
from app.common.exceptions import RateLimitException, ErrorCode

settings = get_settings()


# ========== Lua脚本：原子性的限流检查和计数 ==========
# 使用Lua脚本保证 GET + INCR/SET 的原子性，避免并发竞态条件
RATE_LIMIT_LUA_SCRIPT = """
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local current_time = tonumber(ARGV[3])

-- 获取当前计数和窗口开始时间
local current = redis.call('GET', key)

if current == nil then
    -- 首次请求，设置初始值
    redis.call('SETEX', key, window, '1')
    return {1, 1, window}
end

-- 解析当前值（格式: "count" 或 "count:window_start"）
local count = 0
local window_start = 0

local parts = {}
for part in string.gmatch(current, '([^:]+)') do
    table.insert(parts, part)
end

if #parts >= 2 then
    count = tonumber(parts[1]) or 0
    window_start = tonumber(parts[2]) or current_time
else
    count = tonumber(current) or 0
    window_start = current_time - window
end

-- 检查是否在当前时间窗口内
if (current_time - window_start) < window then
    -- 在窗口内，增加计数
    if count < limit then
        local new_count = count + 1
        local new_value = new_count .. ':' .. window_start
        local ttl = math.ceil(window - (current_time - window_start))
        redis.call('SETEX', key, ttl, new_value)
        return {new_count, limit - new_count + 1, ttl}
    else
        -- 超过限制
        local ttl = math.ceil(window - (current_time - window_start))
        return {count, 0, ttl}
    end
else
    -- 窗口已过期，重置计数
    redis.call('SETEX', key, window, '1:' .. current_time)
    return {1, limit, window}
end
"""


def get_client_identifier(request: Request) -> str:
    """获取客户端标识"""
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"
    
    client_ip = request.client.host if request.client else "unknown"
    
    # 如果有代理头信息，优先使用 X-Forwarded-For
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # 取第一个IP（最原始的客户端IP）
        client_ip = forwarded_for.split(",")[0].strip()
    
    return f"ip:{client_ip}"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """限流中间件（增强版）"""
    
    def __init__(
        self,
        app,
        calls: int = 100,
        period: int = 60,
        key_func: Optional[Callable[[Request], str]] = None
    ):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.key_func = key_func or get_client_identifier
        
        # 预加载Lua脚本到Redis（减少每次请求的网络开销）
        self._lua_script_sha = None
    
    def _ensure_lua_script(self) -> Optional[str]:
        """确保Lua脚本已注册到Redis"""
        if self._lua_script_sha is not None:
            return self._lua_script_sha
        
        try:
            if redis_service.client and redis_service.enabled:
                self._lua_script_sha = redis_service.client.script_load(RATE_LIMIT_LUA_SCRIPT)
                app_logger.info("限流Lua脚本已注册到Redis")
                return self._lua_script_sha
        except Exception as e:
            app_logger.warning(f"注册限流Lua脚本失败: {e}")
        
        return None
    
    async def dispatch(self, request: Request, call_next):
        # 跳过健康检查、文档页面和静态资源
        skip_paths = ["/health", "/health/live", "/health/ready", 
                      "/docs", "/redoc", "/openapi.json", "/", "/metrics",
                      "/favicon.ico"]
        if request.url.path in skip_paths or request.url.path.startswith("/static"):
            return await call_next(request)
        
        # 如果Redis不可用，跳过限流检查（降级策略）
        if not redis_service.enabled:
            return await call_next(request)
        
        identifier = self.key_func(request)
        cache_key = f"rate_limit:{identifier}"
        
        try:
            # 尝试使用Lua脚本进行原子性限流
            result = await self._check_rate_limit_atomic(cache_key)
            
            if result is None:
                # Lua脚本不可用，回退到简单模式
                result = await self._check_rate_limit_simple(cache_key)
            
            current_count, remaining, retry_after = result
            
            # 检查是否超过限制
            if current_count > self.calls:
                app_logger.warning(
                    f"限流触发: {identifier}, "
                    f"当前计数: {current_count}, 限制: {self.calls}, "
                    f"剩余: {remaining}s"
                )
                
                raise RateLimitException(
                    f"请求过于频繁，请稍后再试。限制: {self.calls} 次/{self.period}秒",
                    error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
                    details={
                        "limit": self.calls,
                        "period": self.period,
                        "retry_after": retry_after
                    }
                )
            
            # 处理请求
            response = await call_next(request)
            
            # 添加限流头信息（RFC 6585 标准）
            response.headers["X-RateLimit-Limit"] = str(self.calls)
            response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
            response.headers["X-RateLimit-Reset"] = str(int(time.time()) + retry_after)
            
            return response
            
        except RateLimitException:
            raise
        except Exception as e:
            # 限流中间件出错时，记录警告但不阻塞请求（降级策略）
            app_logger.debug(f"限流中间件错误（已降级）: {e}")
            return await call_next(request)
    
    async def _check_rate_limit_atomic(self, cache_key: str) -> Optional[Tuple[int, int, int]]:
        """
        使用Lua脚本进行原子性限流检查
        
        Returns:
            (current_count, remaining, retry_after) 或 None（如果脚本不可用）
        """
        script_sha = self._ensure_lua_script()
        
        if not script_sha or not redis_service.client:
            return None
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: redis_service.client.evalsha(
                    script_sha,
                    1,  # key数量
                    cache_key,
                    self.calls,  # ARGV[1]: 限制数
                    self.period,  # ARGV[2]: 时间窗口
                    time.time()   # ARGV[3]: 当前时间戳
                )
            )
            
            if isinstance(result, list) and len(result) >= 3:
                return int(result[0]), int(result[1]), int(result[2])
            
            return None
            
        except Exception as e:
            app_logger.debug(f"Lua脚本执行失败: {e}")
            return None
    
    async def _check_rate_limit_simple(self, cache_key: str) -> Tuple[int, int, int]:
        """
        简单模式的限流检查（回退方案）
        
        注意：此方法不是严格原子性的，在高并发下可能略有偏差。
        但对于大多数场景来说已经足够。
        """
        loop = asyncio.get_event_loop()
        current = await loop.run_in_executor(None, lambda: redis_service.get(cache_key))
        current_count = int(current) if current else 0
        
        if current_count >= self.calls:
            return current_count, 0, self.period
        
        if current_count == 0:
            await loop.run_in_executor(
                None, 
                lambda: redis_service.set(cache_key, "1", ttl=self.period)
            )
            return 1, self.calls - 1, self.period
        else:
            await loop.run_in_executor(
                None,
                lambda: redis_service.client.incr(cache_key)
            )
            return current_count + 1, self.calls - current_count - 1, self.period


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
            if not redis_service.enabled:
                return await func(request, *args, **kwargs)
            
            identifier = (key_func or get_client_identifier)(request)
            cache_key = f"rate_limit:{identifier}:{func.__name__}"
            
            try:
                # 尝试使用简单方式检查
                loop = asyncio.get_event_loop()
                current = await loop.run_in_executor(None, lambda: redis_service.get(cache_key))
                current_count = int(current) if current else 0
                
                if current_count >= calls:
                    raise RateLimitException(
                        "请求过于频繁，请稍后再试",
                        error_code=ErrorCode.RATE_LIMIT_EXCEEDED
                    )
                
                if current_count == 0:
                    await loop.run_in_executor(
                        None,
                        lambda: redis_service.set(cache_key, "1", ttl=period)
                    )
                else:
                    if redis_service.client:
                        await loop.run_in_executor(
                            None,
                            lambda: redis_service.client.incr(cache_key)
                        )
                
                return await func(request, *args, **kwargs)
            except RateLimitException:
                raise
            except Exception as e:
                app_logger.debug(f"限流装饰器错误（已降级）: {e}")
                return await func(request, *args, **kwargs)
        
        return wrapper
    return decorator
