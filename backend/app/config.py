"""应用配置管理"""
from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置"""
    
    # Application
    APP_NAME: str = "智能医疗管家平台"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/medical_consultation"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 3600
    
    # Neo4j
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "neo4j"
    
    # Milvus
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_COLLECTION_NAME: str = "medical_documents"
    
    # LLM - Qwen
    QWEN_API_KEY: str = ""
    QWEN_MODEL: str = "qwen-turbo"
    QWEN_EMBEDDING_MODEL: str = "text-embedding-v2"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ENCRYPTION_KEY: Optional[str] = None  # 数据加密密钥（Fernet格式）
    ENABLE_RBAC: bool = True  # 启用RBAC
    ENABLE_DATA_ENCRYPTION: bool = False  # 启用数据加密（默认关闭，需要配置密钥）
    ENABLE_AUTH_MIDDLEWARE: bool = False  # 启用认证中间件（默认关闭，开发环境）
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_CALLS: int = 100  # 允许的请求数
    RATE_LIMIT_PERIOD: int = 60  # 时间窗口（秒）
    
    # File Storage
    UPLOAD_DIR: str = "./data/documents"
    MAX_UPLOAD_SIZE: int = 10485760  # 10MB
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/app.log"
    
    # MCP Server
    MCP_SERVER_HOST: str = "localhost"
    MCP_SERVER_PORT: int = 8001
    
    # Advanced RAG Configuration
    ENABLE_ADVANCED_RAG: bool = True
    ENABLE_MULTI_RETRIEVAL: bool = True
    ENABLE_RERANK: bool = True
    ENABLE_ML_RERANK: bool = True
    ENABLE_INTENT_CLASSIFICATION: bool = True
    ENABLE_RELEVANCE_SCORING: bool = True
    ENABLE_QUERY_UNDERSTANDING: bool = True
    ENABLE_RANKING_OPTIMIZATION: bool = True
    
    # Multi-Retrieval Weights
    VECTOR_RETRIEVAL_WEIGHT: float = 0.4
    BM25_RETRIEVAL_WEIGHT: float = 0.3
    SEMANTIC_RETRIEVAL_WEIGHT: float = 0.2
    KG_RETRIEVAL_WEIGHT: float = 0.1
    
    # Reranker Configuration
    BGE_RERANKER_MODEL: str = "BAAI/bge-reranker-base"
    RERANK_TOP_K: int = 10
    
    # ML Models Directory
    ML_MODELS_DIR: str = "./models"
    INTENT_MODEL_DIR: str = "./models/intent"
    RELEVANCE_MODEL_DIR: str = "./models/relevance"
    QUERY_MODEL_DIR: str = "./models/query"
    RANKING_MODEL_DIR: str = "./models/ranking"
    RERANKER_MODEL_DIR: str = "./models/reranker"
    
    # PDF Image Processing
    ENABLE_PDF_IMAGE_PROCESSING: bool = True
    ENABLE_OCR: bool = True
    ENABLE_MULTIMODAL_LLM: bool = True
    
    # Langfuse Configuration
    ENABLE_LANGFUSE: bool = True
    LANGFUSE_PUBLIC_KEY: Optional[str] = None
    LANGFUSE_SECRET_KEY: Optional[str] = None
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"  # 默认使用云服务，也可以使用自托管
    
    # LLM Performance Configuration
    LLM_DEFAULT_TEMPERATURE: float = 0.7
    LLM_DEFAULT_MAX_TOKENS: int = 2000
    LLM_STREAM_ENABLED: bool = True
    LLM_SEMANTIC_CACHE_ENABLED: bool = True
    LLM_SEMANTIC_CACHE_THRESHOLD: float = 0.95  # 相似度阈值
    
    # Context Management
    CONTEXT_MAX_TOKENS: int = 8000  # 最大上下文token数
    CONTEXT_COMPRESSION_ENABLED: bool = True
    CONTEXT_HISTORY_LIMIT: int = 10  # 保留的对话轮次
    
    # Prompt Engineering
    PROMPT_VERSION: str = "v1.0"
    ENABLE_PROMPT_AB_TEST: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """获取配置实例（单例模式）"""
    return Settings()

