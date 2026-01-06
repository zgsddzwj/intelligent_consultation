"""FastAPI应用入口"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
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

# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="智能医疗管家平台API",
    docs_url="/docs",
    redoc_url="/redoc"
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
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    app_logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} 启动成功")
    app_logger.info(f"环境: {settings.ENVIRONMENT}")
    app_logger.info(f"调试模式: {settings.DEBUG}")
    
    # 尝试初始化数据库表（如果不存在）
    try:
        from app.database.init_db import init_db
        init_db()
    except Exception as e:
        app_logger.warning(f"数据库表初始化警告: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    app_logger.info(f"{settings.APP_NAME} 正在关闭...")


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


@app.get("/metrics")
async def metrics():
    """Prometheus指标端点"""
    from app.infrastructure.monitoring import get_metrics
    return get_metrics()


# 导入路由
from app.api.v1 import consultation, agents, knowledge, users, image_analysis
app.include_router(consultation.router, prefix=settings.API_V1_PREFIX, tags=["咨询"])
app.include_router(agents.router, prefix=settings.API_V1_PREFIX, tags=["Agent"])
app.include_router(knowledge.router, prefix=settings.API_V1_PREFIX, tags=["知识库"])
app.include_router(users.router, prefix=settings.API_V1_PREFIX, tags=["用户"])
app.include_router(image_analysis.router, prefix=settings.API_V1_PREFIX, tags=["图片分析"])

