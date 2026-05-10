"""健康检查API - 增强版（并行检测、超时控制、版本信息、精细化降级）"""
import asyncio
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

# 各服务检测超时时间（秒）
CHECK_TIMEOUTS = {
    "database": 3.0,    # 数据库查询超时
    "redis": 2.0,       # Redis ping 超时
    "milvus": 3.0,      # Milvus 检查超时
    "neo4j": 3.0,       # Neo4j 检查超时
}

# 核心服务列表（这些服务不可用会导致状态为 unhealthy）
CORE_SERVICES = {"database"}

# 重要服务列表（不可用会导致状态为 degraded，但系统仍可用）
IMPORTANT_SERVICES = {"redis", "milvus", "neo4j"}


async def _check_database(db: Session) -> dict:
    """检查数据库连接"""
    start_time = time.time()
    try:
        result = db.execute(text("SELECT 1"))
        result.fetchone()
        latency = time.time() - start_time
        return {
            "status": "healthy",
            "latency_ms": round(latency * 1000, 2)
        }
    except Exception as e:
        latency = time.time() - start_time
        return {
            "status": "unhealthy",
            "error": str(e)[:200],  # 限制错误信息长度
            "latency_ms": round(latency * 1000, 2)
        }


async def _check_redis() -> dict:
    """检查Redis连接"""
    start_time = time.time()
    try:
        # 在线程池中执行同步的Redis操作
        loop = asyncio.get_event_loop()
        is_healthy = await loop.run_in_executor(None, redis_service.health_check)
        latency = time.time() - start_time
        
        if is_healthy:
            return {
                "status": "healthy",
                "latency_ms": round(latency * 1000, 2)
            }
        else:
            return {
                "status": "unhealthy",
                "error": "Connection failed or timed out",
                "latency_ms": round(latency * 1000, 2)
            }
    except Exception as e:
        latency = time.time() - start_time
        return {
            "status": "unhealthy",
            "error": str(e)[:200],
            "latency_ms": round(latency * 1000, 2)
        }


async def _check_milvus() -> dict:
    """检查Milvus连接"""
    start_time = time.time()
    try:
        milvus = get_milvus_service()
        is_healthy = milvus.health_check()
        latency = time.time() - start_time
        
        if is_healthy:
            # 尝试获取集合实体数量作为额外健康指标
            entity_count = 0
            try:
                if milvus._collection:
                    entity_count = milvus._collection.num_entities
            except Exception:
                pass
            
            return {
                "status": "healthy",
                "latency_ms": round(latency * 1000, 2),
                "entity_count": entity_count
            }
        else:
            return {
                "status": "unhealthy",
                "error": "Health check returned false",
                "latency_ms": round(latency * 1000, 2)
            }
    except Exception as e:
        latency = time.time() - start_time
        return {
            "status": "unhealthy",
            "error": str(e)[:200],
            "latency_ms": round(latency * 1000, 2)
        }


async def _check_neo4j() -> dict:
    """检查Neo4j连接"""
    start_time = time.time()
    try:
        neo4j = get_neo4j_client()
        is_healthy = neo4j.health_check()
        latency = time.time() - start_time
        
        if is_healthy:
            return {
                "status": "healthy",
                "latency_ms": round(latency * 1000, 2)
            }
        else:
            return {
                "status": "unhealthy",
                "error": "Health check returned false",
                "latency_ms": round(latency * 1000, 2)
            }
    except Exception as e:
        latency = time.time() - start_time
        return {
            "status": "unhealthy",
            "error": str(e)[:200],
            "latency_ms": round(latency * 1000, 2)
        }


async def _check_with_timeout(check_func, name: str, timeout: float) -> tuple:
    """
    带超时的服务检查
    
    Args:
        check_func: 异步检查函数
        name: 服务名称
        timeout: 超时时间（秒）
        
    Returns:
        (服务名称, 检查结果字典)
    """
    try:
        result = await asyncio.wait_for(check_func(), timeout=timeout)
        return (name, result)
    except asyncio.TimeoutError:
        return (name, {
            "status": "unhealthy",
            "error": f"Check timed out after {timeout}s",
            "latency_ms": round(timeout * 1000, 2)
        })
    except Exception as e:
        return (name, {
            "status": "unhealthy",
            "error": f"Unexpected error: {str(e)[:100]}",
            "latency_ms": 0
        })


def _determine_overall_status(components: dict) -> str:
    """
    根据各组件状态确定整体状态
    
    状态判定规则：
    - healthy: 所有核心服务正常（可选服务异常不影响）
    - degraded: 核心服务正常但重要服务有异常
    - unhealthy: 核心服务异常
    """
    has_core_unhealthy = any(
        components.get(s, {}).get("status") == "unhealthy"
        for s in CORE_SERVICES
    )
    
    if has_core_unhealthy:
        return "unhealthy"
    
    has_important_unhealthy = any(
        components.get(s, {}).get("status") == "unhealthy"
        for s in IMPORTANT_SERVICES
    )
    
    if has_important_unhealthy:
        return "degraded"
    
    return "healthy"


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(db: Session = Depends(get_db)):
    """
    系统健康检查（增强版）
    
    改进点：
    - 并行执行所有服务检测，减少总耗时
    - 每个服务独立超时控制
    - 返回各服务的延迟信息
    - 包含版本信息和启动时间
    - 精细化的降级策略（区分核心/重要/可选服务）
    
    返回格式：
    ```json
    {
      "status": "healthy|degraded|unhealthy",
      "version": "0.1.1",
      "uptime_seconds": 3600,
      "total_check_ms": 50,
      "components": {
        "database": { "status": "healthy", "latency_ms": 5.2 },
        ...
      }
    }
    ```
    """
    overall_start = time.time()
    
    # 并行执行所有服务检查
    check_tasks = [
        _check_with_timeout(_check_database, "database", CHECK_TIMEOUTS["database"]),
        _check_with_timeout(_check_redis, "redis", CHECK_TIMEOUTS["redis"]),
        _check_with_timeout(_check_milvus, "milvus", CHECK_TIMEOUTS["milvus"]),
        _check_with_timeout(_check_neo4j, "neo4j", CHECK_TIMEOUTS["neo4j"]),
    ]
    
    results = await asyncio.gather(*check_tasks, return_exceptions=True)
    
    components = {}
    for result in results:
        if isinstance(result, tuple):
            name, data = result
            components[name] = data
        else:
            # 不应该发生，但做防御性处理
            app_logger.error(f"健康检查返回了意外结果: {result}")
    
    total_latency = time.time() - overall_start
    
    # 记录各服务状态日志
    for name, info in components.items():
        if info["status"] == "unhealthy":
            log_method = app_logger.error if name in CORE_SERVICES else app_logger.warning
            log_method(
                f"健康检查 - {name}不可用: {info.get('error', 'unknown')}, "
                f"延迟: {info.get('latency_ms', 0)}ms"
            )
    
    health_status = {
        "status": _determine_overall_status(components),
        "version": settings.APP_VERSION,
        "uptime_seconds": int(time.time() - _get_start_time()),
        "total_check_ms": round(total_latency * 1000, 2),
        "components": components
    }
    
    return health_status


@router.get("/health/ready", status_code=status.HTTP_200_OK)
async def readiness_check():
    """
    就绪探针（Kubernetes Readiness Probe）
    
    只检查核心依赖是否就绪，用于K8s流量路由判断。
    比 /health 更轻量。
    """
    # 核心服务：数据库
    try:
        from app.database.session import SessionLocal
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            return {"status": "ready"}
        finally:
            db.close()
    except Exception as e:
        app_logger.warning(f"就绪探针失败: {e}")
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "reason": str(e)[:200]}
        )


@router.get("/health/live", status_code=status.HTTP_200_OK)
async def liveness_check():
    """
    存活探针（Kubernetes Liveness Probe）
    
    最轻量的检查，仅确认进程存活。
    用于判断是否需要重启容器。
    """
    return {"status": "alive"}


# 应用启动时间记录（模块级别）
_app_start_time = time.time()


def _get_start_time() -> float:
    """获取应用启动时间"""
    global _app_start_time
    return _app_start_time


def set_start_time(t: float = None):
    """设置应用启动时间（在应用启动时调用）"""
    global _app_start_time
    _app_start_time = t or time.time()
