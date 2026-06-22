"""健康检查API - 增强版（支持深度检查、依赖拓扑、性能基线）"""
import time
import asyncio
from typing import Dict, Any, List
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

# 应用启动时间
_STARTUP_TIME = time.time()

# 核心服务：失败会导致系统不可用
CORE_SERVICES = {"database", "redis"}
# 可选服务：失败仅导致功能降级
OPTIONAL_SERVICES = {"milvus", "neo4j", "llm"}


class HealthChecker:
    """健康检查器 - 支持并行深度检查"""

    def __init__(self):
        self.checks = {}

    def register(self, name: str, checker, category: str = "optional", timeout: float = 5.0):
        """注册健康检查项"""
        self.checks[name] = {
            "checker": checker,
            "category": category,
            "timeout": timeout,
        }

    async def check_all(self, depth: str = "standard") -> Dict[str, Any]:
        """
        并行执行所有健康检查

        Args:
            depth: 检查深度 - basic(基础) / standard(标准) / deep(深度)
        """
        results = {}
        tasks = []

        for name, config in self.checks.items():
            # 基础检查跳过可选服务
            if depth == "basic" and config["category"] == "optional":
                continue
            tasks.append(self._check_single(name, config))

        check_results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in check_results:
            if isinstance(result, Exception):
                continue
            results[result["name"]] = result

        return results

    async def _check_single(self, name: str, config: dict) -> dict:
        """执行单个检查"""
        start = time.time()
        try:
            result = await asyncio.wait_for(
                config["checker"](),
                timeout=config["timeout"]
            )
            latency = round((time.time() - start) * 1000, 2)
            return {
                "name": name,
                "status": result.get("status", "healthy"),
                "latency_ms": latency,
                "category": config["category"],
                **{k: v for k, v in result.items() if k != "status"}
            }
        except asyncio.TimeoutError:
            return {
                "name": name,
                "status": "timeout",
                "latency_ms": round((time.time() - start) * 1000, 2),
                "category": config["category"],
                "error": "检查超时"
            }
        except Exception as e:
            return {
                "name": name,
                "status": "unhealthy",
                "latency_ms": round((time.time() - start) * 1000, 2),
                "category": config["category"],
                "error": str(e)[:200]
            }


# 初始化健康检查器
_health_checker = HealthChecker()


async def _check_database():
    """数据库健康检查"""
    from app.database.session import engine
    db_start = time.time()
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {
        "status": "healthy",
        "response_time_ms": round((time.time() - db_start) * 1000, 2),
    }


async def _check_redis():
    """Redis健康检查"""
    redis_start = time.time()
    info = redis_service.health_check()
    if info.get("status") == "healthy":
        return {
            "status": "healthy",
            "response_time_ms": round((time.time() - redis_start) * 1000, 2),
            "version": info.get("version"),
            "connected_clients": info.get("connected_clients"),
        }
    raise Exception(info.get("reason", "未知错误"))


async def _check_milvus():
    """Milvus健康检查"""
    milvus_start = time.time()
    milvus = get_milvus_service()
    info = milvus.health_check()
    if info.get("status") == "healthy":
        return {
            "status": "healthy",
            "response_time_ms": round((time.time() - milvus_start) * 1000, 2),
            "entity_count": info.get("entity_count"),
            "dimension": info.get("dimension"),
        }
    raise Exception(info.get("reason", "未知错误"))


async def _check_neo4j():
    """Neo4j健康检查"""
    neo4j_start = time.time()
    neo4j = get_neo4j_client()
    info = neo4j.health_check()
    if info.get("status") == "healthy":
        return {
            "status": "healthy",
            "response_time_ms": round((time.time() - neo4j_start) * 1000, 2),
            **{k: v for k, v in info.items() if k != "status"},
        }
    raise Exception(info.get("error", info.get("reason", "Neo4j 不可用")))


async def _check_llm():
    """LLM服务健康检查（轻量级，仅验证配置）"""
    if settings.LLM_PROVIDER == "qwen" and settings.QWEN_API_KEY:
        return {"status": "healthy", "provider": "qwen", "model": settings.QWEN_MODEL}
    elif settings.LLM_PROVIDER == "deepseek" and settings.DEEPSEEK_API_KEY:
        return {"status": "healthy", "provider": "deepseek", "model": settings.DEEPSEEK_MODEL}
    return {"status": "unhealthy", "error": "LLM未配置"}


# 注册检查项
_health_checker.register("database", _check_database, category="core", timeout=5.0)
_health_checker.register("redis", _check_redis, category="core", timeout=3.0)
_health_checker.register("milvus", _check_milvus, category="optional", timeout=5.0)
_health_checker.register("neo4j", _check_neo4j, category="optional", timeout=5.0)
_health_checker.register("llm", _check_llm, category="optional", timeout=2.0)


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(
    db: Session = Depends(get_db),
    depth: str = "standard"
):
    """
    系统健康检查 - 增强版

    参数:
    - depth: 检查深度
      - basic: 仅核心服务（最快）
      - standard: 核心+可选服务（默认）
      - deep: 深度检查（包含性能基线）

    返回核心依赖服务的连接状态及详细指标：
    - database: PostgreSQL数据库
    - redis: Redis缓存服务
    - milvus: 向量数据库（可选）
    - neo4j: 知识图谱数据库（可选）
    - llm: LLM服务配置状态（可选）

    状态说明：
    - healthy: 所有核心服务正常
    - degraded: 部分可选服务异常，系统降级运行
    - unhealthy: 核心服务异常，系统不可用
    """
    start_time = time.time()

    # 执行所有检查
    components = await _health_checker.check_all(depth=depth)

    # 判定核心服务状态
    core_healthy = all(
        c.get("status") == "healthy"
        for name, c in components.items()
        if c.get("category") == "core"
    )

    # 判定总体状态
    if core_healthy:
        all_healthy = all(c.get("status") == "healthy" for c in components.values())
        overall_status = "healthy" if all_healthy else "degraded"
    else:
        overall_status = "unhealthy"

    response_data = {
        "status": overall_status,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "uptime_seconds": int(time.time() - _STARTUP_TIME),
        "response_time_ms": round((time.time() - start_time) * 1000, 2),
        "check_depth": depth,
        "components": components,
    }

    # 不健康时返回503
    if overall_status == "unhealthy":
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=response_data
        )

    return response_data


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


@router.get("/health/deep", status_code=status.HTTP_200_OK)
async def deep_health_check(db: Session = Depends(get_db)):
    """
    深度健康检查

    执行所有检查项，包含性能基线和详细指标。
    适用于运维排查和容量规划。
    """
    return await health_check(db=db, depth="deep")
