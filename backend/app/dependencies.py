"""依赖注入 - 增强版（异步支持、连接池管理、服务工厂模式）"""
from typing import Generator, Optional, Callable
from functools import lru_cache
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
import threading
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
    使用线程锁保证并发安全，防止多个请求同时创建同一服务实例。
    """
    
    _instances: dict = {}
    _lock = threading.Lock()
    
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
        """获取Agent编排器（线程安全单例）"""
        # 双重检查锁定，避免并发请求重复创建
        if "orchestrator" not in cls._instances:
            with cls._lock:
                if "orchestrator" not in cls._instances:
                    from app.agents.orchestrator import AgentOrchestrator
                    app_logger.info("正在创建 AgentOrchestrator 实例...")
                    cls._instances["orchestrator"] = AgentOrchestrator()
                    app_logger.info("AgentOrchestrator 实例创建完成")
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
    def get_rag_tool(cls):
        """获取RAG检索工具（线程安全单例，避免每请求重建整个检索栈）"""
        if "rag_tool" not in cls._instances:
            with cls._lock:
                if "rag_tool" not in cls._instances:
                    from app.agents.tools.rag_tool import RAGTool
                    app_logger.info("正在创建 RAGTool 实例...")
                    cls._instances["rag_tool"] = RAGTool()
                    app_logger.info("RAGTool 实例创建完成")
        return cls._instances["rag_tool"]

    @classmethod
    def get_intent_classifier(cls):
        """获取意图分类器（全局单例；warmup预热的实例由此存取，避免模型重复加载）"""
        if "intent_classifier" not in cls._instances:
            with cls._lock:
                if "intent_classifier" not in cls._instances:
                    from app.config import get_settings
                    from app.knowledge.ml.intent_classifier import IntentClassifier
                    cls._instances["intent_classifier"] = IntentClassifier(
                        model_dir=get_settings().INTENT_MODEL_DIR
                    )
        return cls._instances["intent_classifier"]

    @classmethod
    def get_document_processor(cls):
        """获取文档处理器单例"""
        if "document_processor" not in cls._instances:
            with cls._lock:
                if "document_processor" not in cls._instances:
                    from app.knowledge.rag.document_processor import DocumentProcessor
                    cls._instances["document_processor"] = DocumentProcessor()
        return cls._instances["document_processor"]

    @classmethod
    def get_embedder(cls):
        """获取Embedder单例（嵌入模型/客户端只加载一次）"""
        if "embedder" not in cls._instances:
            with cls._lock:
                if "embedder" not in cls._instances:
                    from app.knowledge.rag.embedder import Embedder
                    cls._instances["embedder"] = Embedder()
        return cls._instances["embedder"]

    @classmethod
    def reset(cls, service_name: str = None):
        """重置服务实例（用于测试或配置变更后）"""
        if service_name:
            cls._instances.pop(service_name, None)
        else:
            cls._instances.clear()


# ========== FastAPI依赖函数 ==========

# ========== 认证依赖 ==========

def get_current_user(request: Request) -> dict:
    """获取当前认证用户（自足式：优先取认证中间件注入的状态，否则自行解析JWT）

    Returns:
        {"user_id": int, "username": str, "role": str}

    Raises:
        HTTPException: 401 未认证
    """
    from app.utils.security import decode_access_token

    user_id = getattr(request.state, "user_id", None)
    user_role = getattr(request.state, "user_role", None)
    username = getattr(request.state, "username", None)

    if user_id is None:
        authorization = request.headers.get("Authorization", "")
        if authorization.lower().startswith("bearer "):
            payload = decode_access_token(authorization.split(" ", 1)[1])
            if payload:
                user_id = payload.get("sub")
                user_role = payload.get("role")
                username = payload.get("username")

    if user_id is None:
        raise HTTPException(status_code=401, detail="未认证：缺少有效的访问令牌")

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="认证信息无效")

    return {"user_id": user_id, "username": username, "role": user_role}


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """要求管理员角色（用于 /admin 等敏感端点）"""
    from app.utils.logger import app_logger

    if current_user.get("role") != "admin":
        app_logger.warning(
            f"非管理员访问管理端点被拒绝: user_id={current_user['user_id']}, role={current_user.get('role')}"
        )
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


def get_optional_current_user(request: Request) -> Optional[dict]:
    """获取当前用户（可选版本）：无有效认证时返回 None 而非 401

    用于咨询对话等允许匿名（仅限开发环境）的端点，配合归属校验使用。
    """
    try:
        return get_current_user(request)
    except HTTPException:
        return None


def require_roles(*roles: str):
    """要求当前用户属于指定角色之一（用于知识库维护等敏感写操作）"""
    def dependency(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user.get("role") not in roles:
            from app.utils.logger import app_logger
            app_logger.warning(
                f"角色权限不足被拒绝: user_id={current_user['user_id']}, role={current_user.get('role')}, required={roles}"
            )
            raise HTTPException(status_code=403, detail=f"需要以下角色之一: {', '.join(roles)}")
        return current_user
    return dependency


def get_current_user_id(request: Request) -> Optional[int]:
    """从请求中获取当前用户ID（JWT 优先，开发环境可降级）"""
    from app.config import get_settings
    settings = get_settings()

    # 认证中间件注入的 JWT 用户信息
    jwt_user_id = getattr(request.state, "user_id", None)
    if jwt_user_id is not None:
        try:
            return int(jwt_user_id)
        except (TypeError, ValueError):
            pass

    # 仅开发环境允许简易身份头/查询参数（生产应启用 ENABLE_AUTH_MIDDLEWARE）
    if settings.ENVIRONMENT == "development":
        user_id = request.headers.get("X-User-ID")
        if user_id:
            try:
                return int(user_id)
            except ValueError:
                pass

        user_id = request.query_params.get("user_id")
        if user_id:
            try:
                return int(user_id)
            except ValueError:
                pass

    return None


def get_orchestrator():
    """获取 Agent 编排器单例（延迟加载）"""
    return ServiceFactory.get_orchestrator()


def get_pagination_params(
    page: int = 1,
    page_size: int = 10,
    order_by: str = "-created_at"
):
    """获取分页参数"""
    # 计算一次，避免重复 max/min 调用
    safe_page = max(1, page)
    safe_page_size = min(max(1, page_size), 100)  # 限制最大100条
    return {
        "page": safe_page,
        "page_size": safe_page_size,
        "offset": (safe_page - 1) * safe_page_size,
        "limit": safe_page_size,
        "order_by": order_by
    }


# ========== 异步任务依赖 ==========

async def get_async_task_status(task_id: str):
    """获取异步任务状态（预留接口）"""
    # TODO: 集成Celery或RQ
    return {"task_id": task_id, "status": "pending"}
