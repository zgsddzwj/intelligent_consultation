"""请求追踪和分布式追踪"""
import uuid
import contextvars
import time
from typing import Optional
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from app.utils.logger import app_logger

# 请求ID上下文变量
request_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar('request_id', default=None)
# 请求开始时间上下文变量（用于内部耗时追踪）
request_start_var: contextvars.ContextVar[Optional[float]] = contextvars.ContextVar('request_start', default=None)


def get_request_id() -> Optional[str]:
    """获取当前请求ID"""
    return request_id_var.get()


def set_request_id(request_id: str):
    """设置请求ID"""
    request_id_var.set(request_id)


def generate_request_id() -> str:
    """生成请求ID"""
    return str(uuid.uuid4())


def get_request_start_time() -> Optional[float]:
    """获取当前请求开始时间"""
    return request_start_var.get()


class TracingMiddleware(BaseHTTPMiddleware):
    """请求追踪中间件 - 支持请求ID传递和耗时追踪"""

    async def dispatch(self, request: Request, call_next):
        # 从请求头获取或生成请求ID（支持上游服务传入，便于链路追踪）
        request_id = request.headers.get("X-Request-ID") or generate_request_id()

        # 设置到上下文
        set_request_id(request_id)
        request_start_var.set(time.time())

        # 添加到请求状态
        request.state.request_id = request_id

        # 处理请求
        response = await call_next(request)

        # 添加请求ID到响应头
        response.headers["X-Request-ID"] = request_id

        # 记录总耗时
        start_time = get_request_start_time()
        if start_time:
            total_time = time.time() - start_time
            response.headers["X-Process-Time"] = f"{total_time:.3f}s"

            # 慢请求告警（超过2秒）
            if total_time > 2.0:
                app_logger.warning(
                    f"慢请求告警: {request.method} {request.url.path} 耗时 {total_time:.3f}s",
                    extra={
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "duration": total_time,
                    }
                )

        return response


class TraceContext:
    """追踪上下文管理器"""

    def __init__(self, request_id: Optional[str] = None):
        self.request_id = request_id or generate_request_id()
        self._token = None

    def __enter__(self):
        self._token = request_id_var.set(self.request_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._token:
            request_id_var.reset(self._token)

    @classmethod
    def current(cls) -> Optional[str]:
        """获取当前追踪ID"""
        return get_request_id()


def trace_span(name: str):
    """简单的函数级追踪装饰器，记录函数耗时"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                return await func(*args, **kwargs)
            finally:
                duration = time.time() - start
                req_id = get_request_id()
                if duration > 0.5:  # 仅记录较慢的调用
                    app_logger.debug(
                        f"Trace [{name}] 耗时: {duration:.3f}s",
                        extra={"span": name, "duration": duration, "request_id": req_id}
                    )

        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.time() - start
                req_id = get_request_id()
                if duration > 0.5:
                    app_logger.debug(
                        f"Trace [{name}] 耗时: {duration:.3f}s",
                        extra={"span": name, "duration": duration, "request_id": req_id}
                    )

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator
