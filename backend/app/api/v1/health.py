"""健康检查API"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.dependencies import get_db
from app.services.redis_service import redis_service
from app.services.milvus_service import get_milvus_service
from app.knowledge.graph.neo4j_client import get_neo4j_client
from app.utils.logger import app_logger

router = APIRouter()

@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(db: Session = Depends(get_db)):
    """
    系统健康检查
    
    返回核心依赖服务的连接状态：
    - database: PostgreSQL数据库
    - redis: Redis缓存服务
    - milvus: 向量数据库
    - neo4j: 知识图谱数据库
    """
    health_status = {
        "status": "healthy",
        "components": {
            "database": "unknown",
            "redis": "unknown",
            "milvus": "unknown",
            "neo4j": "unknown"
        }
    }
    
    # 1. Check Database
    try:
        db.execute(text("SELECT 1"))
        health_status["components"]["database"] = "healthy"
    except Exception as e:
        app_logger.error(f"健康检查 - 数据库连接失败: {e}")
        health_status["components"]["database"] = "unhealthy"
        health_status["status"] = "degraded"

    # 2. Check Redis
    if redis_service.health_check():
        health_status["components"]["redis"] = "healthy"
    else:
        app_logger.warning("健康检查 - Redis不可用")
        health_status["components"]["redis"] = "unhealthy"
        # Redis is optional/degradable, so maybe status is just degraded or we consider it fine?
        # Ideally, degraded.
        health_status["status"] = "degraded"

    # 3. Check Milvus
    milvus = get_milvus_service()
    if milvus.health_check():
        health_status["components"]["milvus"] = "healthy"
    else:
        app_logger.warning("健康检查 - Milvus不可用")
        health_status["components"]["milvus"] = "unhealthy"
        health_status["status"] = "degraded"

    # 4. Check Neo4j
    neo4j = get_neo4j_client()
    if neo4j.health_check():
        health_status["components"]["neo4j"] = "healthy"
    else:
        app_logger.warning("健康检查 - Neo4j不可用")
        health_status["components"]["neo4j"] = "unhealthy"
        health_status["status"] = "degraded"

    return health_status
