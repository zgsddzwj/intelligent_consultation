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

        # 跳过流式响应
        if isinstance(response, StreamingResponse):
            return response

        # 跳过非JSON响应
        content_type = response.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            return response

        # 跳过已包装的响应
        if response.headers.get("X-Response-Wrapped") == "true":
            return response

        # 包装响应
        try:
            body = response.body
            if body:
                original_data = json.loads(body)

                # 如果已经是标准格式，跳过
                if isinstance(original_data, dict) and "success" in original_data:
                    return response

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
                    headers=dict(response.headers)
                )
                new_response.headers["X-Response-Wrapped"] = "true"
                return new_response

        except Exception as e:
            app_logger.debug(f"响应包装失败（已跳过）: {e}")

        return response
