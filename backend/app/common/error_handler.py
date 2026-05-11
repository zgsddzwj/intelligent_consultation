"""全局异常处理器"""
import traceback
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
from app.common.tracing import get_request_id


def _safe_error_response(exc: Exception, status_code: int, error_code: str, message: str, details: dict = None) -> JSONResponse:
    """构建统一的错误响应"""
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": error_code,
                "message": message,
                "details": details or {},
                "request_id": get_request_id()
            },
            "data": None
        }
    )


async def app_exception_handler(request: Request, exc: BaseAppException) -> JSONResponse:
    """应用异常处理器"""
    app_logger.error(
        f"应用异常: {exc.error_code} - {exc.message}",
        extra={
            "error_code": exc.error_code,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method,
            "request_id": get_request_id()
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

    return _safe_error_response(
        exc=exc,
        status_code=status_code,
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """请求验证异常处理器"""
    errors = exc.errors()
    # 简化错误信息，便于前端展示
    simplified_errors = []
    for err in errors:
        loc = " -> ".join(str(x) for x in err.get("loc", []))
        msg = err.get("msg", "")
        simplified_errors.append(f"{loc}: {msg}")

    app_logger.warning(
        f"请求验证失败: {request.url.path}",
        extra={
            "errors": errors,
            "path": request.url.path,
            "request_id": get_request_id()
        }
    )

    return _safe_error_response(
        exc=exc,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_code=ErrorCode.VALIDATION_ERROR,
        message=f"请求参数验证失败: {'; '.join(simplified_errors)}",
        details={"errors": errors}
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
            extra={
                "status_code": exc.status_code,
                "path": request.url.path,
                "request_id": get_request_id()
            }
        )

    # 对500+错误隐藏详细内容，避免泄露内部信息
    message = exc.detail
    if exc.status_code >= 500:
        message = "服务器内部错误，请稍后重试"

    return _safe_error_response(
        exc=exc,
        status_code=exc.status_code,
        error_code=f"HTTP_{exc.status_code}",
        message=message
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """通用异常处理器（兜底）"""
    # 记录详细堆栈到日志
    stack_trace = traceback.format_exc()
    app_logger.exception(
        f"未处理的异常: {type(exc).__name__} - {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "request_id": get_request_id(),
            "traceback": stack_trace
        }
    )

    return _safe_error_response(
        exc=exc,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code=ErrorCode.INTERNAL_ERROR,
        message="服务器内部错误，请稍后重试",
        details={"type": type(exc).__name__} if settings.DEBUG else {}
    )


# 延迟导入 settings，避免循环依赖
from app.config import get_settings
settings = get_settings()
