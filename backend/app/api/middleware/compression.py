"""响应压缩中间件"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import gzip
from typing import Callable


class CompressionMiddleware(BaseHTTPMiddleware):
    """响应压缩中间件（Gzip）"""
    
    MIN_SIZE = 1024  # 最小压缩大小（1KB）
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 检查客户端是否支持压缩
        accept_encoding = request.headers.get("Accept-Encoding", "")
        supports_gzip = "gzip" in accept_encoding
        
        # 处理请求
        response = await call_next(request)
        
        # 如果客户端支持gzip且响应体足够大，进行压缩
        if supports_gzip and hasattr(response, "body"):
            body = response.body
            if len(body) > self.MIN_SIZE:
                # 压缩响应体
                compressed_body = gzip.compress(body)
                response.body = compressed_body
                response.headers["Content-Encoding"] = "gzip"
                response.headers["Content-Length"] = str(len(compressed_body))
        
        return response

