"""认证中间件"""
from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.utils.security import decode_access_token
from app.common.exceptions import ErrorCode
from app.common.tracing import get_request_id


class AuthMiddleware(BaseHTTPMiddleware):
    """认证中间件 - JWT验证"""

    EXACT_PUBLIC_PATHS = {
        "/",
        "/health",
        "/ready",
        "/live",
        "/startup",
        "/docs",
        "/redoc",
        "/openapi.json",
    }

    PREFIX_PUBLIC_PATHS = (
        "/api/v1/health",
        "/api/v1/users/register",
        "/api/v1/users/login",
    )

    @classmethod
    def _is_public_path(cls, path: str) -> bool:
        if path in cls.EXACT_PUBLIC_PATHS:
            return True
        return any(path.startswith(prefix) for prefix in cls.PREFIX_PUBLIC_PATHS)

    @staticmethod
    def _unauthorized_response(message: str, error_code: str) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "success": False,
                "error": {
                    "code": error_code,
                    "message": message,
                    "details": {},
                    "request_id": get_request_id(),
                },
                "data": None,
            },
        )

    async def dispatch(self, request: Request, call_next):
        if self._is_public_path(request.url.path):
            return await call_next(request)

        authorization = request.headers.get("Authorization")
        if not authorization:
            return self._unauthorized_response("缺少认证令牌", ErrorCode.UNAUTHORIZED)

        try:
            scheme, token = authorization.split()
            if scheme.lower() != "bearer":
                return self._unauthorized_response(
                    "认证方案错误，应使用Bearer",
                    ErrorCode.UNAUTHORIZED,
                )
        except ValueError:
            return self._unauthorized_response(
                "认证令牌格式错误",
                ErrorCode.UNAUTHORIZED,
            )

        payload = decode_access_token(token)
        if not payload:
            return self._unauthorized_response(
                "认证令牌无效或已过期",
                ErrorCode.TOKEN_INVALID,
            )

        request.state.user_id = payload.get("sub")
        request.state.user_role = payload.get("role")

        return await call_next(request)
