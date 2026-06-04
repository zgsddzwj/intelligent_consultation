"""FastAPI应用入口 - 极致优化版（优雅启动、依赖预热、配置校验、健康检查聚合）"""
import asyncio
import time
from contextlib import asynccontextmanager
from typing import Dict, Any, List

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from app.config import get_settings
from app.utils.logger import app_logger
from app.api.middleware import LoggingMiddleware
from app.api.middleware.compression import CompressionMiddleware
from app.common.exceptions import BaseAppException
from app.common.error_handler import (
    app_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    general_exception_handler
)
from app.utils.validators import validate_environment

settings = get_settings()

# ===== 全局启动状态 =====
_startup_state = {
    "start_time": None,
    "ready": False,
    "dependencies": {},
    "warnings": [],
    "errors": [],
}

_metrics_task: asyncio.Task | None = None


class DependencyChecker:
    """依赖服务检查器"""

    CHECKERS = []

    @classmethod
    def register(cls, name: str, checker_func, required: bool = True, timeout: float = 5.0):
        """注册依赖检查器"""
        cls.CHECKERS.append({
            "name": name,
            "func": checker_func,
            "required": required,
            "timeout": timeout,
        })

    @classmethod
    async def check_all(cls) -> Dict[str, Any]:
        """并行检查所有依赖"""
        results = {}

        async def _check_single(checker: dict) -> dict:
            name = checker["name"]
            start = time.time()
            try:
                result = await asyncio.wait_for(
                    checker["func"](),
                    timeout=checker["timeout"]
                )
                latency = time.time() - start
                return {
                    "name": name,
                    "status": result.get("status", "unknown"),
                    "latency_ms": round(latency * 1000, 2),
                    "required": checker["required"],
                    "details": result,
                }
            except asyncio.TimeoutError:
                return {
                    "name": name,
                    "status": "timeout",
                    "latency_ms": round((time.time() - start) * 1000, 2),
                    "required": checker["required"],
                    "error": "检查超时",
                }
            except Exception as e:
                return {
                    "name": name,
                    "status": "error",
                    "latency_ms": round((time.time() - start) * 1000, 2),
                    "required": checker["required"],
                    "error": str(e)[:200],
                }

        tasks = [_check_single(c) for c in cls.CHECKERS]
        check_results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in check_results:
            if isinstance(result, Exception):
                continue
            results[result["name"]] = result

        return results


# ===== 注册依赖检查器 =====

async def _check_postgresql():
    from app.database.session import engine
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "healthy"}


async def _check_redis():
    from app.services.redis_service import redis_service
    result = redis_service.health_check()
    return result


async def _check_neo4j():
    from app.knowledge.graph.neo4j_client import get_neo4j_client
    client = get_neo4j_client()
    health = client.health_check()
    return health if isinstance(health, dict) else {"status": "healthy" if health else "unhealthy"}


async def _check_milvus():
    from app.services.milvus_service import get_milvus_service
    milvus = get_milvus_service()
    return milvus.health_check()


async def _check_llm():
    """轻量级LLM健康检查（仅验证配置，不实际调用）"""
    if settings.LLM_PROVIDER == "qwen" and settings.QWEN_API_KEY:
        return {"status": "healthy", "provider": "qwen", "model": settings.QWEN_MODEL}
    elif settings.LLM_PROVIDER == "deepseek" and settings.DEEPSEEK_API_KEY:
        return {"status": "healthy", "provider": "deepseek", "model": settings.DEEPSEEK_MODEL}
    return {"status": "unhealthy", "error": "LLM未配置"}


DependencyChecker.register("postgresql", _check_postgresql, required=True, timeout=5.0)
DependencyChecker.register("redis", _check_redis, required=False, timeout=3.0)
DependencyChecker.register("neo4j", _check_neo4j, required=False, timeout=5.0)
DependencyChecker.register("milvus", _check_milvus, required=False, timeout=5.0)
DependencyChecker.register("llm", _check_llm, required=True, timeout=2.0)


async def _warmup_services():
    """服务预热 - 提前加载关键资源"""
    app_logger.info("开始服务预热...")
    warmup_tasks = []

    # 预热意图分类器
    if settings.ENABLE_INTENT_CLASSIFICATION:
        async def _warmup_intent():
            try:
                from app.knowledge.ml.intent_classifier import IntentClassifier
                classifier = IntentClassifier(model_dir=settings.INTENT_MODEL_DIR)
                app_logger.info("✓ 意图分类器预热完成")
            except Exception as e:
                app_logger.warning(f"⚠ 意图分类器预热失败: {e}")
        warmup_tasks.append(_warmup_intent())

    # 预热缓存
    async def _warmup_cache():
        try:
            from app.services.cache_service import cache_service
            cache_service.health_check()
            app_logger.info("✓ 缓存服务预热完成")
        except Exception as e:
            app_logger.warning(f"⚠ 缓存预热失败: {e}")
    warmup_tasks.append(_warmup_cache())

    # 并行执行预热
    if warmup_tasks:
        await asyncio.gather(*warmup_tasks, return_exceptions=True)

    app_logger.info("服务预热完成")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理 - 极致优化版"""
    global _metrics_task
    _startup_state["start_time"] = time.time()

    # ===== 启动阶段 =====
    app_logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 启动中...")
    app_logger.info(f"环境: {settings.ENVIRONMENT} | 调试模式: {settings.DEBUG}")

    # 1. 环境配置校验
    is_valid, env_errors = validate_environment()
    if not is_valid:
        app_logger.error("❌ 环境配置校验失败:")
        for err in env_errors:
            app_logger.error(f"  - {err}")
        _startup_state["errors"].extend(env_errors)
    else:
        app_logger.info("✓ 环境配置校验通过")

    # 2. 初始化数据库
    try:
        from app.database.init_db import init_db
        init_db()
        app_logger.info("✓ 数据库表初始化完成")
    except Exception as e:
        app_logger.warning(f"⚠ 数据库表初始化警告: {e}")

    # 3. 依赖服务健康检查（并行）
    app_logger.info("🔍 正在检查依赖服务...")
    dep_results = await DependencyChecker.check_all()
    _startup_state["dependencies"] = dep_results

    all_required_healthy = True
    for name, result in dep_results.items():
        status_icon = "✓" if result["status"] == "healthy" else "⚠" if not result["required"] else "✗"
        latency = result.get("latency_ms", 0)
        app_logger.info(
            f"{status_icon} {name}: {result['status']} ({latency}ms)"
            f"{' [必需]' if result['required'] else ' [可选]'}"
        )
        if result["required"] and result["status"] != "healthy":
            all_required_healthy = False
            _startup_state["errors"].append(f"必需依赖 {name} 不可用: {result.get('error', '未知错误')}")
        elif result["status"] != "healthy":
            _startup_state["warnings"].append(f"可选依赖 {name} 不可用")

    if not all_required_healthy:
        app_logger.error("❌ 部分必需依赖服务不可用，应用可能无法正常工作")
    else:
        app_logger.info("✓ 所有必需依赖服务正常")

    # 生产环境 fail-fast：配置错误或必需依赖不可用则拒绝启动
    if settings.ENVIRONMENT == "production" and settings.STARTUP_FAIL_FAST:
        blocking_errors = list(_startup_state["errors"])
        if not settings.SECRET_KEY:
            blocking_errors.append("SECRET_KEY: 生产环境必须配置 JWT 密钥")
        if blocking_errors:
            for err in blocking_errors:
                app_logger.error(f"启动阻断: {err}")
            raise RuntimeError(
                f"生产环境启动失败，存在 {len(blocking_errors)} 项阻断错误"
            )

    # 4. 服务预热
    await _warmup_services()

    # 5. 初始化监控
    from app.infrastructure.monitoring import init_app_info, update_system_metrics
    init_app_info(settings.APP_VERSION, settings.ENVIRONMENT)

    async def _system_metrics_loop():
        while True:
            update_system_metrics()
            await asyncio.sleep(30)

    _metrics_task = asyncio.create_task(_system_metrics_loop())

    # 6. 标记就绪（开发环境允许降级启动）
    _startup_state["ready"] = all_required_healthy or settings.ENVIRONMENT != "production"
    startup_duration = time.time() - _startup_state["start_time"]
    app_logger.info(f"✅ 应用启动完成，耗时 {startup_duration:.2f}s")

    yield

    # ===== 关闭阶段 =====
    app_logger.info(f"🛑 {settings.APP_NAME} 正在优雅关闭...")
    if _metrics_task:
        _metrics_task.cancel()
        try:
            await _metrics_task
        except asyncio.CancelledError:
            pass
        _metrics_task = None
    await _shutdown_services_async()
    app_logger.info("✅ 应用已关闭")


async def _shutdown_services_async():
    """异步关闭各服务连接"""
    from app.infrastructure.graceful_shutdown import shutdown_manager
    from app.database.session import engine

    shutdown_manager.register(lambda: engine.dispose(), "PostgreSQL")

    # 使用优雅关闭管理器
    shutdown_manager.register(lambda: _close_service("Redis", "app.services.redis_service", "redis_service"), "Redis")
    shutdown_manager.register(lambda: _close_service("Milvus", "app.services.milvus_service", "get_milvus_service"), "Milvus")
    shutdown_manager.register(lambda: _close_service("Neo4j", "app.knowledge.graph.neo4j_client", "get_neo4j_client"), "Neo4j")

    await shutdown_manager.shutdown()


def _close_service(name: str, module_path: str, attr_name: str):
    """关闭单个服务"""
    try:
        module = __import__(module_path, fromlist=[attr_name])
        service = getattr(module, attr_name)
        if callable(service) and not hasattr(service, 'close'):
            service = service()
        if hasattr(service, 'close'):
            service.close()
            app_logger.info(f"✓ {name} 连接已关闭")
    except Exception as e:
        app_logger.warning(f"⚠ 关闭 {name} 连接时出错: {e}")


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="智能医疗管家平台API - 企业级医疗AI解决方案",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)

# 注册全局异常处理器
app.add_exception_handler(BaseAppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    max_age=600,
)

# 生产环境安全中间件
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.TRUSTED_HOSTS,
    )

# 追踪中间件
from app.common.tracing import TracingMiddleware
app.add_middleware(TracingMiddleware)

# 压缩中间件
app.add_middleware(CompressionMiddleware)

# 日志中间件
app.add_middleware(LoggingMiddleware)

# 请求校验中间件
from app.api.middleware.request_validator import RequestValidatorMiddleware
app.add_middleware(RequestValidatorMiddleware)

# 统一响应包装中间件
from app.api.middleware.response_wrapper import UnifiedResponseMiddleware
app.add_middleware(UnifiedResponseMiddleware)

# 增强版限流中间件
if settings.RATE_LIMIT_ENABLED:
    from app.api.middleware.rate_limit_enhanced import RateLimitEnhancedMiddleware
    app.add_middleware(
        RateLimitEnhancedMiddleware,
        default_calls=settings.RATE_LIMIT_CALLS,
        default_period=settings.RATE_LIMIT_PERIOD
    )

# 认证中间件
if settings.ENABLE_AUTH_MIDDLEWARE:
    from app.api.middleware.auth import AuthMiddleware
    app.add_middleware(AuthMiddleware)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """添加安全响应头"""
    response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

    if settings.ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"

    return response


@app.get("/", tags=["根路径"])
async def root():
    """根路径 - 返回应用基本信息"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "status": "running",
        "docs": "/docs" if settings.DEBUG else None,
    }


@app.get("/health", tags=["健康检查"])
async def health_check():
    """综合健康检查端点（K8s probes兼容，实时探测依赖）"""
    if not _startup_state["ready"]:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "starting", "ready": False}
        )

    # 实时并行检查依赖（避免启动后依赖宕机仍报 healthy）
    deps = await DependencyChecker.check_all()
    required_unhealthy = [
        name for name, result in deps.items()
        if result.get("required") and result.get("status") != "healthy"
    ]

    if required_unhealthy:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "ready": True,
                "unhealthy_dependencies": required_unhealthy,
                "dependencies": {
                    name: {"status": r["status"], "latency_ms": r.get("latency_ms")}
                    for name, r in deps.items()
                },
            }
        )

    uptime = time.time() - _startup_state["start_time"] if _startup_state["start_time"] else 0

    return {
        "status": "healthy",
        "ready": True,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "uptime_seconds": round(uptime, 2),
        "dependencies": {
            name: {"status": r["status"], "latency_ms": r.get("latency_ms")}
            for name, r in deps.items()
        },
    }


@app.get("/ready", tags=["健康检查"])
async def readiness_check():
    """就绪检查（K8s readiness probe）"""
    if _startup_state["ready"]:
        return {"status": "ready"}
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "not_ready"}
    )


@app.get("/live", tags=["健康检查"])
async def liveness_check():
    """存活检查（K8s liveness probe）"""
    return {"status": "alive"}


@app.get("/metrics", tags=["监控"])
async def metrics(request: Request):
    """Prometheus指标端点（生产环境需 METRICS_ACCESS_TOKEN）"""
    if settings.METRICS_ACCESS_TOKEN:
        token = request.headers.get("X-Metrics-Token") or request.query_params.get("token")
        if token != settings.METRICS_ACCESS_TOKEN:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid metrics token"},
            )
    from app.infrastructure.monitoring import get_metrics
    return get_metrics()


@app.get("/startup", tags=["健康检查"])
async def startup_info(request: Request):
    """启动信息 - 用于排查启动问题（生产环境需 METRICS_ACCESS_TOKEN）"""
    if settings.ENVIRONMENT == "production":
        if settings.METRICS_ACCESS_TOKEN:
            token = request.headers.get("X-Metrics-Token") or request.query_params.get("token")
            if token != settings.METRICS_ACCESS_TOKEN:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Invalid metrics token"},
                )
        else:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": "Not Found"},
            )

    return {
        "ready": _startup_state["ready"],
        "start_time": _startup_state["start_time"],
        "uptime_seconds": round(time.time() - _startup_state["start_time"], 2) if _startup_state["start_time"] else None,
        "dependencies": _startup_state.get("dependencies", {}),
        "warnings": _startup_state.get("warnings", []),
        "errors": _startup_state.get("errors", []),
    }


@app.get("/favicon.ico")
async def favicon():
    """Favicon图标"""
    return Response(status_code=204)


# 导入路由
from app.api.v1 import consultation, agents, knowledge, users, image_analysis, health
app.include_router(consultation.router, prefix=f"{settings.API_V1_PREFIX}/consultation", tags=["咨询"])
app.include_router(agents.router, prefix=f"{settings.API_V1_PREFIX}/agents", tags=["Agent"])
app.include_router(knowledge.router, prefix=f"{settings.API_V1_PREFIX}/knowledge", tags=["知识库"])
app.include_router(users.router, prefix=f"{settings.API_V1_PREFIX}/users", tags=["用户"])
app.include_router(image_analysis.router, prefix=f"{settings.API_V1_PREFIX}/image", tags=["图片分析"])
app.include_router(health.router, prefix=f"{settings.API_V1_PREFIX}", tags=["监控"])
