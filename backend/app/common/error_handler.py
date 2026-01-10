"""全局异常处理器"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.common.exceptions import (
    BaseAppException,
    BusinessException,
    ValidationException,
    NotFoundException,
    UnauthorizedException,
    ForbiddenException,
    DatabaseException,
    ExternalServiceException,
    RateLimitException,
    ErrorCode
)
from app.utils.logger import app_logger


async def app_exception_handler(request: Request, exc: BaseAppException) -> JSONResponse:
    """应用异常处理器"""
    app_logger.error(
        f"应用异常: {exc.error_code} - {exc.message}",
        extra={
            "error_code": exc.error_code,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    status_code_map = {
        ValidationException: status.HTTP_400_BAD_REQUEST,
        NotFoundException: status.HTTP_404_NOT_FOUND,
        UnauthorizedException: status.HTTP_401_UNAUTHORIZED,
        ForbiddenException: status.HTTP_403_FORBIDDEN,
        DatabaseException: status.HTTP_500_INTERNAL_SERVER_ERROR,
        ExternalServiceException: status.HTTP_502_BAD_GATEWAY,
        RateLimitException: status.HTTP_429_TOO_MANY_REQUESTS,
        BusinessException: status.HTTP_400_BAD_REQUEST,
    }
    
    status_code = status_code_map.get(type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details
            },
            "data": None
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """请求验证异常处理器"""
    errors = exc.errors()
    app_logger.warning(
        f"请求验证失败: {request.url.path}",
        extra={"errors": errors, "path": request.url.path}
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": ErrorCode.VALIDATION_ERROR,
                "message": "请求参数验证失败",
                "details": {
                    "errors": errors
                }
            },
            "data": None
        }
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """HTTP异常处理器"""
    # 常见的静态资源404错误不记录为警告
    common_static_paths = ["/favicon.ico", "/robots.txt", "/apple-touch-icon.png"]
    if exc.status_code == 404 and request.url.path in common_static_paths:
        app_logger.debug(f"静态资源未找到: {request.url.path}")
    else:
    app_logger.warning(
        f"HTTP异常: {exc.status_code} - {exc.detail}",
        extra={"status_code": exc.status_code, "path": request.url.path}
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "details": {}
            },
            "data": None
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """通用异常处理器（兜底）"""
    app_logger.exception(
        f"未处理的异常: {type(exc).__name__} - {str(exc)}",
        extra={"path": request.url.path, "method": request.method}
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": ErrorCode.INTERNAL_ERROR,
                "message": "服务器内部错误，请稍后重试",
                "details": {}
            },
            "data": None
        }
    )

