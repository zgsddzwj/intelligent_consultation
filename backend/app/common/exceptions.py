"""自定义异常类体系"""
from typing import Optional, Dict, Any


class BaseAppException(Exception):
    """应用基础异常类"""
    
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)


class BusinessException(BaseAppException):
    """业务异常"""
    pass


class ValidationException(BaseAppException):
    """验证异常"""
    pass


class NotFoundException(BaseAppException):
    """资源未找到异常"""
    pass


class UnauthorizedException(BaseAppException):
    """未授权异常"""
    pass


class ForbiddenException(BaseAppException):
    """禁止访问异常"""
    pass


class DatabaseException(BaseAppException):
    """数据库异常"""
    pass


class ExternalServiceException(BaseAppException):
    """外部服务异常"""
    pass


class LLMServiceException(ExternalServiceException):
    """LLM服务异常"""
    pass


class CacheException(BaseAppException):
    """缓存异常"""
    pass


class RateLimitException(BaseAppException):
    """限流异常"""
    pass


# 错误码定义
class ErrorCode:
    """错误码常量"""
    # 通用错误 (1000-1999)
    INTERNAL_ERROR = "1000"
    INVALID_REQUEST = "1001"
    VALIDATION_ERROR = "1002"
    
    # 业务错误 (2000-2999)
    CONSULTATION_NOT_FOUND = "2001"
    USER_NOT_FOUND = "2002"
    AGENT_ERROR = "2003"
    
    # 认证授权错误 (3000-3999)
    UNAUTHORIZED = "3001"
    FORBIDDEN = "3002"
    TOKEN_EXPIRED = "3003"
    TOKEN_INVALID = "3004"
    
    # 外部服务错误 (4000-4999)
    LLM_SERVICE_ERROR = "4001"
    DATABASE_ERROR = "4002"
    CACHE_ERROR = "4003"
    RATE_LIMIT_EXCEEDED = "4004"
    
    # 数据错误 (5000-5999)
    DATA_NOT_FOUND = "5001"
    DATA_VALIDATION_ERROR = "5002"

