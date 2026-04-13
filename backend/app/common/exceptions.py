"""自定义异常类体系

提供统一的异常处理机制，支持：
- 分层异常继承（BaseAppException -> 具体异常）
- 结构化错误码（ErrorCode枚举）
- 详细错误信息（message + error_code + details）
- HTTP状态码映射
"""
from typing import Optional, Dict, Any, Type


# HTTP状态码映射
HTTP_STATUS_MAP: Dict[Type[BaseAppException], int] = {
    'ValidationException': 422,
    'NotFoundException': 404,
    'UnauthorizedException': 401,
    'ForbiddenException': 403,
    'RateLimitException': 429,
}


class BaseAppException(Exception):
    """应用基础异常类
    
    所有业务异常的基类，提供统一的错误信息格式。
    
    Attributes:
        message: 错误描述信息
        error_code: 错误码，用于程序化处理
        details: 额外的错误详情字典
        http_status: HTTP响应状态码
    """
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None, 
        details: Optional[Dict[str, Any]] = None,
        http_status: Optional[int] = 500
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.http_status = http_status
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，用于API响应"""
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "details": self.details
            },
            "http_status": self.http_status
        }
    
    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"


class BusinessException(BaseAppException):
    """业务逻辑异常
    
    用于处理业务规则违反等场景。
    """
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(message, error_code, details, http_status=400)


class ValidationException(BaseAppException):
    """数据验证异常
    
    用于请求数据校验失败场景。
    """
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(message, error_code, details, http_status=422)


class NotFoundException(BaseAppException):
    """资源未找到异常
    
    用于查询的资源不存在场景。
    """
    def __init__(self, message: str = "资源未找到", error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(message, error_code, details, http_status=404)


class UnauthorizedException(BaseAppException):
    """未授权异常
    
    用于用户未登录或token无效场景。
    """
    def __init__(self, message: str = "未授权访问", error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(message, error_code, details, http_status=401)


class ForbiddenException(BaseAppException):
    """禁止访问异常
    
    用于用户权限不足场景。
    """
    def __init__(self, message: str = "权限不足", error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(message, error_code, details, http_status=403)


class DatabaseException(BaseAppException):
    """数据库操作异常
    
    用于数据库连接、查询失败等场景。
    """
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(message, error_code, details, http_status=500)


class ExternalServiceException(BaseAppException):
    """外部服务调用异常
    
    用于LLM、知识图谱等外部服务调用失败。
    """
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(message, error_code, details, http_status=502)


class LLMServiceException(ExternalServiceException):
    """LLM服务异常
    
    用于Qwen/DeepSeek等LLM服务调用失败。
    """
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        default_code = error_code or ErrorCode.LLM_SERVICE_ERROR
        super().__init__(message, default_code, details)


class KnowledgeGraphException(ExternalServiceException):
    """知识图谱服务异常
    
    用于Neo4j操作失败场景。
    """
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        default_code = error_code or ErrorCode.KNOWLEDGE_GRAPH_ERROR
        super().__init__(message, default_code, details)


class VectorStoreException(ExternalServiceException):
    """向量数据库异常
    
    用于Milvus操作失败场景。
    """
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        default_code = error_code or ErrorCode.VECTOR_STORE_ERROR
        super().__init__(message, default_code, details)


class CacheException(BaseAppException):
    """缓存操作异常
    
    用于Redis缓存读写失败。
    """
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(message, error_code, details, http_status=500)


class RateLimitException(BaseAppException):
    """限流异常
    
    用于请求频率超限场景。
    """
    def __init__(self, message: str = "请求过于频繁，请稍后重试", error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(message, error_code, details, http_status=429)


class DocumentProcessingException(BaseAppException):
    """文档处理异常
    
    用于PDF解析、OCR识别等文档处理失败。
    """
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(message, error_code, details, http_status=422)


class ConfigException(BaseAppException):
    """配置异常
    
    用于系统配置缺失或无效。
    """
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(message, error_code, details, http_status=500)


# 错误码定义
class ErrorCode:
    """错误码常量定义
    
    错误码分段规则：
    - 1xxx: 通用/系统错误
    - 2xxx: 业务逻辑错误  
    - 3xxx: 认证授权错误
    - 4xxx: 外部服务错误
    - 5xxx: 数据相关错误
    - 6xxx: 知识库/RAG错误
    """
    
    # ========== 通用错误 (1000-1999) ==========
    INTERNAL_ERROR = "1000"           # 内部服务器错误
    INVALID_REQUEST = "1001"          # 无效请求
    VALIDATION_ERROR = "1002"         # 数据验证失败
    CONFIG_ERROR = "1003"             # 配置错误
    NOT_IMPLEMENTED = "1004"          # 功能未实现
    
    # ========== 业务错误 (2000-2999) ==========
    CONSULTATION_NOT_FOUND = "2001"   # 咨询记录不存在
    USER_NOT_FOUND = "2002"           # 用户不存在
    AGENT_ERROR = "2003"              # Agent执行错误
    INVALID_CONSULTATION_TYPE = "2004"  # 无效的咨询类型
    CONTEXT_TOO_LONG = "2005"         # 上下文过长
    EMPTY_USER_INPUT = "2006"         # 用户输入为空
    
    # ========== 认证授权错误 (3000-3999) ==========
    UNAUTHORIZED = "3001"             # 未认证
    FORBIDDEN = "3002"                # 禁止访问
    TOKEN_EXPIRED = "3003"            # Token过期
    TOKEN_INVALID = "3004"            # Token无效
    INSUFFICIENT_PERMISSIONS = "3005" # 权限不足
    
    # ========== 外部服务错误 (4000-4999) ==========
    LLM_SERVICE_ERROR = "4001"        # LLM服务错误
    DATABASE_ERROR = "4002"           # 数据库错误
    CACHE_ERROR = "4003"              # 缓存错误
    RATE_LIMIT_EXCEEDED = "4004"      # 限流
    KNOWLEDGE_GRAPH_ERROR = "4005"    # 知识图谱错误
    VECTOR_STORE_ERROR = "4006"       # 向量数据库错误
    EMBEDDING_ERROR = "4007"          # 向量化错误
    OCR_ERROR = "4008"                # OCR识别错误
    
    # ========== 数据错误 (5000-5999) ==========
    DATA_NOT_FOUND = "5001"           # 数据不存在
    DATA_VALIDATION_ERROR = "5002"    # 数据验证失败
    DUPLICATE_DATA = "5003"           # 重复数据
    DATA_CORRUPTION = "5004"          # 数据损坏
    
    # ========== 知识库/RAG错误 (6000-6999) ==========
    RETRIEVAL_ERROR = "6001"          # 检索错误
    RERANK_ERROR = "6002"             # 重排序错误
    CHUNK_ERROR = "6003"              # 文本分块错误
    PARSER_ERROR = "6004"             # 文档解析错误
    NO_RELEVANT_RESULTS = "6005"      # 无相关检索结果

