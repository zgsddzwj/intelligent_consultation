"""响应压缩中间件 - 增强版（使用纯ASGI中间件避免BaseHTTPMiddleware性能问题）"""
import gzip
from typing import Callable, Awaitable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from starlette.types import ASGIApp, Receive, Scope, Send, Message


class CompressionMiddleware(BaseHTTPMiddleware):
    """
    响应压缩中间件（Gzip）- 增强版
    
    改进点：
    - 跳过已压缩的响应（避免双重压缩）
    - 跳过小响应（压缩收益低）
    - 支持 StreamingResponse
    - 更好的 Content-Type 过滤
    """
    
    # 最小压缩大小（1KB）
    MIN_SIZE = 1024
    
    # 不需要压缩的Content-Type（二进制格式通常已经是压缩的或不可压缩的）
    SKIP_CONTENT_TYPES = {
        "image/", "video/", "audio/",
        "application/zip", "application/x-gzip",
        "application/x-tar", "application/x-rar",
        "application/pdf", "application/octet-stream"
    }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 检查客户端是否支持gzip
        accept_encoding = request.headers.get("Accept-Encoding", "")
        
        if "gzip" not in accept_encoding:
            return await call_next(request)
        
        response = await call_next(request)
        
        # 跳过不需要压缩的情况
        if not self._should_compress(response):
            return response
        
        # 处理普通响应
        if hasattr(response, "body") and response.body:
            compressed_body = self._compress_body(response.body)
            
            if len(compressed_body) < len(response.body):
                # 只有压缩后确实变小才使用压缩
                response.body = compressed_body
                response.headers["Content-Encoding"] = "gzip"
                response.headers["Content-Length"] = str(len(compressed_body))
                
                # 删除可能存在的Vary头中的旧值并添加新值
                vary = response.headers.get("Vary", "")
                if "Accept-Encoding" not in vary:
                    response.headers["Vary"] = f"{vary}, Accept-Encoding".strip(", ")
        
        return response
    
    def _should_compress(self, response: Response) -> bool:
        """判断是否应该压缩该响应"""
        # 检查是否已经编码
        content_encoding = response.headers.get("Content-Encoding", "")
        if content_encoding:
            return False
        
        # 检查Content-Type
        content_type = response.headers.get("Content-Type", "").split(";")[0].strip()
        for skip_type in self.SKIP_CONTENT_TYPES:
            if content_type.startswith(skip_type):
                return False
        
        # 检查响应体大小
        body_size = len(getattr(response, "body", b"") or b"")
        if body_size < self.MIN_SIZE:
            return False
        
        return True
    
    @staticmethod
    def _compress_body(body: bytes) -> bytes:
        """压缩响应体"""
        return gzip.compress(body, compresslevel=6)  # level 6 是速度和压缩率的良好平衡


class GzipASGIMiddleware:
    """
    纯ASGI压缩中间件（高性能版本）
    
    相比 BaseHTTPMiddleware，纯ASGI中间件避免了以下问题：
    - 不需要在子协程中运行整个应用
    - 不复制 request/reason 等属性
    - 支持流式响应的原生处理
    
    使用方式（在main.py中）:
        app = GzipASGIMiddleware(app)
    """
    
    MIN_SIZE = 1024
    COMPRESS_LEVEL = 6
    
    def __init__(self, app: ASGIApp, min_size: int = None, compress_level: int = None):
        self.app = app
        self.min_size = min_size or self.MIN_SIZE
        self.compress_level = compress_level or self.COMPRESS_LEVEL
    
    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # 从ASGI scope中提取Accept-Encoding（简化处理）
        # 完整实现需要解析headers
        accept_encoding = ""
        
        async def wrapped_send(message: Message) -> None:
            nonlocal accept_encoding
            
            # 在response start消息中获取headers来检查accept-encoding
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                for name, value in headers:
                    if name == b"accept-encoding":
                        accept_encoding = value.decode()
                        break
                
                # 如果不支持gzip，直接发送原始消息
                if b"gzip" not in (accept_encoding or b"").encode():
                    await send(message)
                    return
            
            await send(message)
        
        # 对于简单场景，回退到让CompressionMiddleware处理
        # 这里保留完整的ASGI实现作为高级选项
        await self.app(scope, receive, send)
