"""响应压缩中间件"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, StreamingResponse
import gzip
from typing import Callable
from app.utils.logger import app_logger


class CompressionMiddleware(BaseHTTPMiddleware):
    """响应压缩中间件（Gzip）"""
    
    MIN_SIZE = 1024  # 最小压缩大小（1KB）
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 检查客户端是否支持压缩
        accept_encoding = request.headers.get("Accept-Encoding", "")
        supports_gzip = "gzip" in accept_encoding
        
        # 处理请求
        response = await call_next(request)
        
        # 跳过流式响应和已压缩的响应
        if isinstance(response, StreamingResponse):
            return response
        
        content_encoding = response.headers.get("Content-Encoding", "")
        if content_encoding:
            return response
        
        # 如果客户端支持gzip且响应体足够大，进行压缩
        if supports_gzip and hasattr(response, "body"):
            try:
                body = response.body
                if body and len(body) > self.MIN_SIZE:
                    # 压缩响应体
                    compressed_body = gzip.compress(body, compresslevel=6)
                    # 只有当压缩后更小时才使用压缩
                    if len(compressed_body) < len(body):
                        response.body = compressed_body
                        response.headers["Content-Encoding"] = "gzip"
                        response.headers["Content-Length"] = str(len(compressed_body))
                        response.headers["Vary"] = "Accept-Encoding"
            except Exception as e:
                app_logger.debug(f"响应压缩失败（已跳过）: {e}")
        
        return response
