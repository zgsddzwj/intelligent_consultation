"""认证中间件"""
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from app.utils.security import decode_access_token
from app.common.exceptions import UnauthorizedException, ErrorCode
from app.utils.logger import app_logger


class AuthMiddleware(BaseHTTPMiddleware):
    """认证中间件 - JWT验证"""
    
    # 不需要认证的路径
    PUBLIC_PATHS = [
        "/",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/users/register",
        "/api/v1/users/login",
    ]
    
    async def dispatch(self, request: Request, call_next):
        # 检查是否为公开路径
        if any(request.url.path.startswith(path) for path in self.PUBLIC_PATHS):
            return await call_next(request)
        
        # 获取Token
        authorization = request.headers.get("Authorization")
        if not authorization:
            raise UnauthorizedException(
                "缺少认证令牌",
                error_code=ErrorCode.UNAUTHORIZED
            )
        
        # 解析Token
        try:
            scheme, token = authorization.split()
            if scheme.lower() != "bearer":
                raise UnauthorizedException(
                    "认证方案错误，应使用Bearer",
                    error_code=ErrorCode.UNAUTHORIZED
                )
        except ValueError:
            raise UnauthorizedException(
                "认证令牌格式错误",
                error_code=ErrorCode.UNAUTHORIZED
            )
        
        # 验证Token
        payload = decode_access_token(token)
        if not payload:
            raise UnauthorizedException(
                "认证令牌无效或已过期",
                error_code=ErrorCode.TOKEN_INVALID
            )
        
        # 将用户信息添加到请求状态
        request.state.user_id = payload.get("sub")
        request.state.user_role = payload.get("role")
        
        # 继续处理请求
        return await call_next(request)

