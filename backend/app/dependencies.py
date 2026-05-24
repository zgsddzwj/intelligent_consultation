"""依赖注入 - 增强版（异步支持、连接池管理、服务工厂模式）"""
from typing import Generator, Optional, Callable
from functools import lru_cache
from fastapi import Depends, Request
from sqlalchemy.orm import Session
from app.database.session import SessionLocal, get_db_with_retry
from app.config import get_settings
from app.infrastructure.repositories.user_repository import UserRepository
from app.infrastructure.repositories.consultation_repository import ConsultationRepository
from app.infrastructure.repositories.knowledge_repository import KnowledgeRepository
from app.utils.logger import app_logger

settings = get_settings()


# ========== 数据库依赖 ==========

def get_db() -> Generator[Session, None, None]:
    """获取数据库会话（标准版）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_robust() -> Generator[Session, None, None]:
    """获取数据库会话（带重试版，高并发场景使用）"""
    yield from get_db_with_retry()


# ========== Repository依赖 ==========

def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    """获取用户Repository"""
    return UserRepository(db)


def get_consultation_repository(db: Session = Depends(get_db)) -> ConsultationRepository:
    """获取咨询Repository"""
    return ConsultationRepository(db)


def get_knowledge_repository(db: Session = Depends(get_db)) -> KnowledgeRepository:
    """获取知识库Repository"""
    return KnowledgeRepository(db)


# ========== 服务工厂（懒加载单例） ==========

class ServiceFactory:
    """服务工厂 - 提供懒加载的服务实例
    
    避免在应用启动时初始化所有服务，按需创建。
    """
    
    _instances: dict = {}
    _lock = False
    
    @classmethod
    def get_llm_service(cls):
        """获取LLM服务"""
        if "llm" not in cls._instances:
            from app.services.llm_service import llm_service
            cls._instances["llm"] = llm_service
        return cls._instances["llm"]
    
    @classmethod
    def get_redis_service(cls):
        """获取Redis服务"""
        if "redis" not in cls._instances:
            from app.services.redis_service import redis_service
            cls._instances["redis"] = redis_service
        return cls._instances["redis"]
    
    @classmethod
    def get_milvus_service(cls):
        """获取Milvus服务"""
        if "milvus" not in cls._instances:
            from app.services.milvus_service import get_milvus_service
            cls._instances["milvus"] = get_milvus_service()
        return cls._instances["milvus"]
    
    @classmethod
    def get_neo4j_client(cls):
        """获取Neo4j客户端"""
        if "neo4j" not in cls._instances:
            from app.knowledge.graph.neo4j_client import get_neo4j_client
            cls._instances["neo4j"] = get_neo4j_client()
        return cls._instances["neo4j"]
    
    @classmethod
    def get_cache_service(cls):
        """获取缓存服务"""
        if "cache" not in cls._instances:
            from app.services.cache_service import cache_service
            cls._instances["cache"] = cache_service
        return cls._instances["cache"]
    
    @classmethod
    def get_orchestrator(cls):
        """获取Agent编排器"""
        if "orchestrator" not in cls._instances:
            from app.agents.orchestrator import AgentOrchestrator
            cls._instances["orchestrator"] = AgentOrchestrator()
        return cls._instances["orchestrator"]
    
    @classmethod
    def get_context_manager(cls):
        """获取上下文管理器"""
        if "context" not in cls._instances:
            from app.services.context_manager import context_manager
            cls._instances["context"] = context_manager
        return cls._instances["context"]
    
    @classmethod
    def get_hybrid_search(cls):
        """获取混合检索器"""
        if "hybrid_search" not in cls._instances:
            from app.knowledge.rag.hybrid_search import HybridSearch
            cls._instances["hybrid_search"] = HybridSearch()
        return cls._instances["hybrid_search"]
    
    @classmethod
    def reset(cls, service_name: str = None):
        """重置服务实例（用于测试或配置变更后）"""
        if service_name:
            cls._instances.pop(service_name, None)
        else:
            cls._instances.clear()


# ========== FastAPI依赖函数 ==========

def get_current_user_id(request: Request) -> Optional[int]:
    """从请求中获取当前用户ID（支持多种认证方式）"""
    # 从请求头获取
    user_id = request.headers.get("X-User-ID")
    if user_id:
        try:
            return int(user_id)
        except ValueError:
            pass
    
    # 从JWT token获取（如果实现了）
    # TODO: 集成JWT认证
    
    # 从查询参数获取（开发环境）
    user_id = request.query_params.get("user_id")
    if user_id:
        try:
            return int(user_id)
        except ValueError:
            pass
    
    return None


def get_pagination_params(
    page: int = 1,
    page_size: int = 10,
    order_by: str = "-created_at"
):
    """获取分页参数"""
    return {
        "page": max(1, page),
        "page_size": min(max(1, page_size), 100),  # 限制最大100条
        "offset": (max(1, page) - 1) * min(max(1, page_size), 100),
        "limit": min(max(1, page_size), 100),
        "order_by": order_by
    }


# ========== 异步任务依赖 ==========

async def get_async_task_status(task_id: str):
    """获取异步任务状态（预留接口）"""
    # TODO: 集成Celery或RQ
    return {"task_id": task_id, "status": "pending"}
