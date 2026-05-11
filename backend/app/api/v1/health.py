"""健康检查API"""
import time
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.dependencies import get_db
from app.services.redis_service import redis_service
from app.services.milvus_service import get_milvus_service
from app.knowledge.graph.neo4j_client import get_neo4j_client
from app.config import get_settings
from app.utils.logger import app_logger

router = APIRouter()
settings = get_settings()

# 核心服务：失败会导致系统不可用
CORE_SERVICES = {"database", "redis"}
# 可选服务：失败仅导致功能降级
OPTIONAL_SERVICES = {"milvus", "neo4j"}


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(db: Session = Depends(get_db)):
    """
    系统健康检查

    返回核心依赖服务的连接状态及详细指标：
    - database: PostgreSQL数据库
    - redis: Redis缓存服务
    - milvus: 向量数据库（可选）
    - neo4j: 知识图谱数据库（可选）

    状态说明：
    - healthy: 所有核心服务正常
    - degraded: 部分可选服务异常，系统降级运行
    - unhealthy: 核心服务异常，系统不可用
    """
    start_time = time.time()
    components: dict = {}
    core_healthy = True

    # 1. Check Database (核心服务)
    try:
        db_start = time.time()
        db.execute(text("SELECT 1"))
        components["database"] = {
            "status": "healthy",
            "response_time_ms": round((time.time() - db_start) * 1000, 2),
        }
    except Exception as e:
        app_logger.error(f"健康检查 - 数据库连接失败: {e}")
        components["database"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        core_healthy = False

    # 2. Check Redis (核心服务)
    try:
        redis_start = time.time()
        redis_info = redis_service.health_check()
        if redis_info.get("status") == "healthy":
            components["redis"] = {
                "status": "healthy",
                "response_time_ms": round((time.time() - redis_start) * 1000, 2),
                "version": redis_info.get("version"),
                "connected_clients": redis_info.get("connected_clients"),
            }
        else:
            raise Exception(redis_info.get("reason", "未知错误"))
    except Exception as e:
        app_logger.warning(f"健康检查 - Redis不可用: {e}")
        components["redis"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        core_healthy = False

    # 3. Check Milvus (可选服务)
    try:
        milvus_start = time.time()
        milvus = get_milvus_service()
        milvus_info = milvus.health_check()
        if milvus_info.get("status") == "healthy":
            components["milvus"] = {
                "status": "healthy",
                "response_time_ms": round((time.time() - milvus_start) * 1000, 2),
                "entity_count": milvus_info.get("entity_count"),
                "dimension": milvus_info.get("dimension"),
            }
        else:
            raise Exception(milvus_info.get("reason", "未知错误"))
    except Exception as e:
        app_logger.warning(f"健康检查 - Milvus不可用: {e}")
        components["milvus"] = {
            "status": "unhealthy",
            "error": str(e),
        }

    # 4. Check Neo4j (可选服务)
    try:
        neo4j_start = time.time()
        neo4j = get_neo4j_client()
        if neo4j.health_check():
            components["neo4j"] = {
                "status": "healthy",
                "response_time_ms": round((time.time() - neo4j_start) * 1000, 2),
            }
        else:
            raise Exception("健康检查返回False")
    except Exception as e:
        app_logger.warning(f"健康检查 - Neo4j不可用: {e}")
        components["neo4j"] = {
            "status": "unhealthy",
            "error": str(e),
        }

    # 判定总体状态
    if core_healthy:
        overall_status = "healthy" if all(
            c.get("status") == "healthy" for c in components.values()
        ) else "degraded"
    else:
        overall_status = "unhealthy"

    return {
        "status": overall_status,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "response_time_ms": round((time.time() - start_time) * 1000, 2),
        "components": components,
    }


@router.get("/health/ready", status_code=status.HTTP_200_OK)
async def readiness_probe(db: Session = Depends(get_db)):
    """
    K8s Readiness Probe 专用端点

    仅检查核心服务，确保Pod可以接收流量。
    """
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        return {"status": "not ready", "reason": "database unavailable"}

    try:
        if redis_service.health_check().get("status") != "healthy":
            return {"status": "not ready", "reason": "redis unavailable"}
    except Exception:
        return {"status": "not ready", "reason": "redis unavailable"}

    return {"status": "ready"}


@router.get("/health/live", status_code=status.HTTP_200_OK)
async def liveness_probe():
    """
    K8s Liveness Probe 专用端点

    仅检查应用本身是否存活，不检查外部依赖。
    如果此端点失败，K8s 将重启 Pod。
    """
    return {"status": "alive"}
