"""FastAPI应用入口"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.exceptions import RequestValidationError
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

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理（替代已废弃的 @app.on_event）"""
    # ===== 启动阶段 =====
    app_logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} 启动成功")
    app_logger.info(f"环境: {settings.ENVIRONMENT}")
    app_logger.info(f"调试模式: {settings.DEBUG}")

    # 初始化数据库表（如果不存在）
    try:
        from app.database.init_db import init_db
        init_db()
    except Exception as e:
        app_logger.warning(f"数据库表初始化警告: {e}")

    # 依赖服务健康检查
    await _check_dependencies()

    yield

    # ===== 关闭阶段 =====
    app_logger.info(f"{settings.APP_NAME} 正在关闭...")
    _shutdown_services()


async def _check_dependencies():
    """检查核心依赖服务状态"""
    # PostgreSQL 检查
    try:
        from app.database.session import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        app_logger.info("✓ PostgreSQL 连接正常")
    except Exception as e:
        app_logger.error(f"✗ PostgreSQL 连接失败: {e}")

    # Redis 检查
    try:
        from app.services.redis_service import redis_service
        if redis_service.health_check().get("status") == "healthy":
            app_logger.info("✓ Redis 连接正常")
        else:
            app_logger.warning("⚠ Redis 健康检查未通过")
    except Exception as e:
        app_logger.warning(f"⚠ Redis 连接失败（将降级处理）: {e}")

    # Neo4j 检查（弱依赖）
    try:
        from app.knowledge.graph.neo4j_client import get_neo4j_client
        client = get_neo4j_client()
        if client.health_check():
            app_logger.info("✓ Neo4j 连接正常")
        else:
            app_logger.warning("⚠ Neo4j 健康检查未通过")
    except Exception as e:
        app_logger.warning(f"⚠ Neo4j 连接失败（知识图谱功能将降级）: {e}")

    # Milvus 检查（弱依赖）
    try:
        from app.services.milvus_service import get_milvus_service
        milvus = get_milvus_service()
        stats = milvus.health_check()
        if stats.get("status") == "healthy":
            app_logger.info(f"✓ Milvus 连接正常，实体数: {stats.get('entity_count', 0)}")
        else:
            app_logger.warning("⚠ Milvus 健康检查未通过")
    except Exception as e:
        app_logger.warning(f"⚠ Milvus 连接失败（向量检索功能将降级）: {e}")


def _shutdown_services():
    """关闭各服务连接"""
    # 关闭 Redis 连接池
    try:
        from app.services.redis_service import redis_service
        redis_service.close()
    except Exception as e:
        app_logger.warning(f"关闭 Redis 连接时出错: {e}")

    # 关闭 Milvus 连接
    try:
        from app.services.milvus_service import get_milvus_service
        milvus = get_milvus_service()
        milvus.close()
    except Exception as e:
        app_logger.warning(f"关闭 Milvus 连接时出错: {e}")


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="智能医疗管家平台API",
    docs_url="/docs",
    redoc_url="/redoc",
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
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=600,
)

# 添加可信主机中间件（生产环境）
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # 可配置为具体域名
    )

# 添加追踪中间件（最外层，最先执行）
from app.common.tracing import TracingMiddleware
app.add_middleware(TracingMiddleware)

# 添加压缩中间件
app.add_middleware(CompressionMiddleware)

# 添加日志中间件
app.add_middleware(LoggingMiddleware)

# 添加限流中间件
if settings.RATE_LIMIT_ENABLED:
    from app.infrastructure.rate_limit import RateLimitMiddleware
    app.add_middleware(
        RateLimitMiddleware,
        calls=settings.RATE_LIMIT_CALLS,
        period=settings.RATE_LIMIT_PERIOD
    )

# 添加认证中间件（可选，生产环境启用）
if settings.ENABLE_AUTH_MIDDLEWARE:
    from app.api.middleware.auth import AuthMiddleware
    app.add_middleware(AuthMiddleware)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """添加安全响应头"""
    response = await call_next(request)
    
    # 安全头配置
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    
    # 仅在HTTPS环境下启用HSTS
    if settings.ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    return response


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/metrics")
async def metrics():
    """Prometheus指标端点"""
    from app.infrastructure.monitoring import get_metrics
    return get_metrics()


@app.get("/favicon.ico")
async def favicon():
    """Favicon图标（避免404错误）"""
    return Response(status_code=204)


# 导入路由
from app.api.v1 import consultation, agents, knowledge, users, image_analysis, health
app.include_router(consultation.router, prefix=f"{settings.API_V1_PREFIX}/consultation", tags=["咨询"])
app.include_router(agents.router, prefix=f"{settings.API_V1_PREFIX}/agents", tags=["Agent"])
app.include_router(knowledge.router, prefix=f"{settings.API_V1_PREFIX}/knowledge", tags=["知识库"])
app.include_router(users.router, prefix=f"{settings.API_V1_PREFIX}/users", tags=["用户"])
app.include_router(image_analysis.router, prefix=f"{settings.API_V1_PREFIX}/image", tags=["图片分析"])
app.include_router(health.router, prefix=f"{settings.API_V1_PREFIX}", tags=["监控"])

# 覆盖根路径 /health
@app.get("/health", tags=["监控"])
async def root_health_check():
    """根健康检查（兼容 K8s probes）"""
    return {"status": "healthy", "detail_url": f"{settings.API_V1_PREFIX}/health"}
