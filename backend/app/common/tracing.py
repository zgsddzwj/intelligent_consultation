"""请求追踪和分布式追踪"""
import uuid
import contextvars
from typing import Optional
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from app.utils.logger import app_logger

# 请求ID上下文变量
request_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar('request_id', default=None)


def get_request_id() -> Optional[str]:
    """获取当前请求ID"""
    return request_id_var.get()


def set_request_id(request_id: str):
    """设置请求ID"""
    request_id_var.set(request_id)


def generate_request_id() -> str:
    """生成请求ID"""
    return str(uuid.uuid4())


class TracingMiddleware(BaseHTTPMiddleware):
    """请求追踪中间件"""
    
    async def dispatch(self, request: Request, call_next):
        # 从请求头获取或生成请求ID
        request_id = request.headers.get("X-Request-ID") or generate_request_id()
        
        # 设置到上下文
        set_request_id(request_id)
        
        # 添加到请求状态
        request.state.request_id = request_id
        
        # 处理请求
        response = await call_next(request)
        
        # 添加请求ID到响应头
        response.headers["X-Request-ID"] = request_id
        
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

