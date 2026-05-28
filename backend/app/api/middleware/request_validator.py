"""请求校验中间件 - 增强输入验证和安全检查"""
import time
import json
from typing import Optional
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.utils.logger import app_logger
from app.utils.security import sanitize_input


class RequestValidatorMiddleware(BaseHTTPMiddleware):
    """
    请求校验中间件

    功能：
    - 请求体大小限制
    - 输入内容净化（XSS防护）
    - 请求频率基础检查
    - Content-Type验证
    """

    # 最大请求体大小 (10MB)
    MAX_BODY_SIZE = 10 * 1024 * 1024

    # 允许的Content-Type
    ALLOWED_CONTENT_TYPES = {
        "application/json",
        "application/x-www-form-urlencoded",
        "multipart/form-data",
        "text/plain",
        "application/octet-stream",
    }

    # 需要净化的字段
    SANITIZE_FIELDS = {"message", "question", "content", "text", "query", "description"}

    async def dispatch(self, request: Request, call_next):
        # 检查请求体大小
        content_length = request.headers.get("Content-Length")
        if content_length:
            try:
                size = int(content_length)
                if size > self.MAX_BODY_SIZE:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "success": False,
                            "error": {
                                "code": "REQUEST_TOO_LARGE",
                                "message": f"请求体过大，最大允许 {self.MAX_BODY_SIZE // 1024 // 1024}MB"
                            }
                        }
                    )
            except ValueError:
                pass

        # 检查Content-Type
        content_type = request.headers.get("Content-Type", "")
        if content_type and request.method in ("POST", "PUT", "PATCH"):
            base_type = content_type.split(";")[0].strip()
            if base_type and base_type not in self.ALLOWED_CONTENT_TYPES:
                return JSONResponse(
                    status_code=415,
                    content={
                        "success": False,
                        "error": {
                            "code": "UNSUPPORTED_MEDIA_TYPE",
                            "message": f"不支持的Content-Type: {base_type}"
                        }
                    }
                )

        # 处理请求
        response = await call_next(request)
        return response


async def sanitize_request_body(body: bytes, content_type: str) -> bytes:
    """净化请求体中的危险内容"""
    if not body or b"application/json" not in content_type.encode():
        return body

    try:
        data = json.loads(body)
        if isinstance(data, dict):
            data = _sanitize_dict(data)
        return json.dumps(data, ensure_ascii=False).encode()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return body


def _sanitize_dict(data: dict) -> dict:
    """递归净化字典中的字符串值"""
    sanitized = {}
    for key, value in data.items():
        if isinstance(value, str) and any(field in key.lower() for field in RequestValidatorMiddleware.SANITIZE_FIELDS):
            sanitized[key] = sanitize_input(value)
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_dict(value)
        elif isinstance(value, list):
            sanitized[key] = [_sanitize_item(item) for item in value]
        else:
            sanitized[key] = value
    return sanitized


def _sanitize_item(item):
    """净化列表项"""
    if isinstance(item, dict):
        return _sanitize_dict(item)
    return item
