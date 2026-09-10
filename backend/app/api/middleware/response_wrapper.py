"""统一响应包装中间件 - 将所有API响应格式化为标准结构"""
import json
import time
from typing import Any, Dict
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse, StreamingResponse
from app.utils.logger import app_logger


class UnifiedResponseMiddleware(BaseHTTPMiddleware):
    """
    统一响应包装中间件

    功能：
    - 自动包装所有JSON响应为标准格式 {success, data, meta}
    - 跳过已包装响应和流式响应
    - 添加请求元信息（trace_id, timestamp, duration）
    """

    # 跳过包装的路径
    SKIP_PATHS = {
        "/docs", "/redoc", "/openapi.json",
        "/metrics", "/health", "/ready", "/live", "/startup",
        "/favicon.ico"
    }

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # 跳过特定路径
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        response = await call_next(request)

        # 跳过非JSON响应。
        # 注意：不能用 isinstance(response, StreamingResponse) 判断——内层的
        # BaseHTTPMiddleware 会让所有响应都变成其子类，导致JSON响应也被跳过；
        # SSE(text/event-stream)等真实流式响应由 content-type 过滤自然排除
        content_type = response.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            return response

        # 跳过已包装的响应
        if response.headers.get("X-Response-Wrapped") == "true":
            return response

        # 包装响应
        try:
            # BaseHTTPMiddleware的call_next返回流式响应（无.body属性），
            # 旧实现读 .body 抛 AttributeError 被下方 except 吞掉，包装从未生效。
            # 先缓冲完整响应体，再重建响应返回。
            body_bytes = b""
            async for chunk in response.body_iterator:
                body_bytes += chunk

            # 透传头时剔除 content-length：重建后响应体长度变化，由Response重新计算
            passthrough_headers = {
                k: v for k, v in response.headers.items()
                if k.lower() != "content-length"
            }

            if body_bytes:
                original_data = json.loads(body_bytes)

                # 如果已经是标准格式，跳过（重建响应：body_iterator已被消费）
                if isinstance(original_data, dict) and "success" in original_data:
                    rebuilt = Response(
                        content=body_bytes,
                        status_code=response.status_code,
                        headers=passthrough_headers,
                        media_type=response.headers.get("content-type", "application/json").split(";")[0],
                    )
                    return rebuilt

                wrapped = {
                    "success": True,
                    "data": original_data,
                    "meta": {
                        "request_id": getattr(request.state, "request_id", None),
                        "timestamp": time.time(),
                        "duration_ms": round((time.time() - start_time) * 1000, 2),
                        "path": request.url.path,
                        "method": request.method
                    }
                }

                new_response = JSONResponse(
                    content=wrapped,
                    status_code=response.status_code,
                    headers=passthrough_headers,
                )
                new_response.headers["X-Response-Wrapped"] = "true"
                return new_response

            # 空响应体：同样需要重建（原body_iterator已耗尽）
            return Response(
                status_code=response.status_code,
                headers=passthrough_headers,
            )

        except Exception as e:
            app_logger.debug(f"响应包装失败（已跳过）: {e}")

        return response
