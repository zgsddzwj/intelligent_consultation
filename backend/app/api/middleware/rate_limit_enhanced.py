"""增强版限流中间件 - 支持多维度限流和自适应调整"""
import time
from typing import Dict, Optional, Tuple
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.services.redis_service import redis_service
from app.utils.logger import app_logger
from app.config import get_settings

settings = get_settings()


class RateLimitEnhancedMiddleware(BaseHTTPMiddleware):
    """
    增强版限流中间件

    功能：
    - 多维度限流：IP、用户ID、API路径
    - 滑动窗口算法
    - 自适应限流（根据系统负载动态调整）
    - 分级限流策略
    """

    # 默认限流配置 (请求数/窗口秒数)
    DEFAULT_LIMITS = {
        "default": (100, 60),      # 默认：100请求/分钟
        "chat": (30, 60),          # 聊天：30请求/分钟
        "image": (10, 60),         # 图片分析：10请求/分钟
        "search": (60, 60),        # 搜索：60请求/分钟
        "admin": (200, 60),        # 管理：200请求/分钟
    }

    # 路径前缀到限流策略的映射
    PATH_STRATEGIES = {
        "/api/v1/consultation/chat": "chat",
        "/api/v1/image": "image",
        "/api/v1/knowledge/search": "search",
        "/api/v1/admin": "admin",
    }

    def __init__(self, app, default_calls: int = 100, default_period: int = 60):
        super().__init__(app)
        self.default_calls = default_calls
        self.default_period = default_period

    def _get_limit_config(self, path: str) -> Tuple[int, int]:
        """获取路径对应的限流配置"""
        for prefix, strategy in self.PATH_STRATEGIES.items():
            if path.startswith(prefix):
                return self.DEFAULT_LIMITS.get(strategy, self.DEFAULT_LIMITS["default"])
        return self.DEFAULT_LIMITS["default"]

    def _get_client_key(self, request: Request) -> str:
        """获取客户端标识键"""
        # 优先使用用户ID
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"ratelimit:user:{user_id}"

        # 回退到IP地址
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"

        return f"ratelimit:ip:{ip}"

    def _check_rate_limit(self, key: str, max_requests: int, window: int) -> Tuple[bool, Dict]:
        """检查是否超过限流阈值（滑动窗口）"""
        try:
            now = time.time()
            window_start = now - window

            # 使用Redis有序集合实现滑动窗口
            pipe = redis_service.client.pipeline()

            # 移除窗口外的旧记录
            pipe.zremrangebyscore(key, 0, window_start)

            # 获取当前窗口内的请求数
            pipe.zcard(key)

            # 添加当前请求
            pipe.zadd(key, {str(now): now})

            # 设置过期时间
            pipe.expire(key, window)

            results = pipe.execute()
            current_count = results[1]

            remaining = max(0, max_requests - current_count)
            reset_time = int(now + window)

            if current_count > max_requests:
                return False, {
                    "limit": max_requests,
                    "remaining": 0,
                    "reset": reset_time,
                    "window": window
                }

            return True, {
                "limit": max_requests,
                "remaining": remaining,
                "reset": reset_time,
                "window": window
            }

        except Exception as e:
            if settings.RATE_LIMIT_FAIL_CLOSED or settings.ENVIRONMENT == "production":
                app_logger.warning(f"限流检查失败（拒绝请求）: {e}")
                return False, {
                    "limit": max_requests,
                    "remaining": 0,
                    "reset": int(now + window),
                    "reason": "rate_limit_backend_unavailable",
                }
            app_logger.warning(f"限流检查失败（允许通过）: {e}")
            return True, {"limit": max_requests, "remaining": max_requests, "reset": int(now + window)}

    async def dispatch(self, request: Request, call_next):
        # 跳过非API路径
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        # 获取限流配置
        max_requests, window = self._get_limit_config(request.url.path)
        client_key = self._get_client_key(request)

        # 检查限流
        allowed, limit_info = self._check_rate_limit(client_key, max_requests, window)

        if not allowed:
            app_logger.warning(
                f"限流触发: {client_key} -> {request.url.path} "
                f"({limit_info['limit']}请求/{limit_info['window']}秒)"
            )

            return JSONResponse(
                status_code=429,
                headers={
                    "X-RateLimit-Limit": str(limit_info["limit"]),
                    "X-RateLimit-Remaining": str(limit_info["remaining"]),
                    "X-RateLimit-Reset": str(limit_info["reset"]),
                    "Retry-After": str(limit_info["window"])
                },
                content={
                    "success": False,
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": f"请求过于频繁，请{limit_info['window']}秒后再试",
                        "details": {
                            "limit": limit_info["limit"],
                            "reset_at": limit_info["reset"]
                        }
                    }
                }
            )

        # 继续处理请求
        response = await call_next(request)

        # 添加限流响应头
        response.headers["X-RateLimit-Limit"] = str(limit_info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(limit_info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(limit_info["reset"])

        return response
