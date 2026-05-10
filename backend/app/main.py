"""FastAPI应用入口 - 增强版（使用lifespan替代废弃的on_event）"""
from contextlib import asynccontextmanager
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理（替代废弃的 on_event）
    
    FastAPI 0.111+ 推荐使用 lifespan 上下文管理器，
    相比 on_event 提供更好的类型支持和资源清理能力。
    """
    # ========== 启动阶段 ==========
    app_logger.info("=" * 50)
    app_logger.info(f"正在启动 {settings.APP_NAME} v{settings.APP_VERSION}...")
    
    # 记录启动时间（用于健康检查的uptime计算）
    from app.api.v1.health import set_start_time
    set_start_time()
    
    app_logger.info(f"环境: {settings.ENVIRONMENT}")
    app_logger.info(f"调试模式: {settings.DEBUG}")
    
    # 初始化数据库表
    try:
        from app.database.init_db import init_db
        init_db()
    except Exception as e:
        app_logger.warning(f"数据库表初始化警告: {e}")
    
    # 预加载限流Lua脚本到Redis
    try:
        if settings.RATE_LIMIT_ENABLED:
            from app.infrastructure.rate_limit import RateLimitMiddleware
            # 在中间件初始化时自动注册脚本
            app_logger.info("限流系统初始化完成")
    except Exception as e:
        app_logger.warning(f"限流系统初始化警告: {e}")
    
    # 预热LLM服务连接
    try:
        from app.services.llm_service import llm_service
        app_logger.info(f"LLM服务已就绪: {llm_service.provider}/{llm_service.model}")
    except Exception as e:
        app_logger.warning(f"LLM服务预热失败: {e}")
    
    app_logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} 启动成功")
    app_logger.info("=" * 50)
    
    yield  # 应用运行中...
    
    # ========== 关闭阶段 ==========
    app_logger.info(f"{settings.APP_NAME} 正在关闭...")
    
    # 清理资源
    try:
        # 可以在这里添加清理逻辑，如：
        # - 关闭数据库连接池
        # - 刷新缓存数据
        # - 停止后台任务
        pass
    except Exception as e:
        app_logger.warning(f"资源清理警告: {e}")
    
    app_logger.info(f"{settings.APP_NAME} 已关闭")


# 创建FastAPI应用（使用lifespan）
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="智能医疗管家平台API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan  # 使用新的生命周期管理
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
    from starlette.responses import Response
    return Response(status_code=204)  # No Content


# 导入路由
from app.api.v1 import consultation, agents, knowledge, users, image_analysis, health
app.include_router(consultation.router, prefix=f"{settings.API_V1_PREFIX}/consultation", tags=["咨询"])
app.include_router(agents.router, prefix=f"{settings.API_V1_PREFIX}/agents", tags=["Agent"])
app.include_router(knowledge.router, prefix=f"{settings.API_V1_PREFIX}/knowledge", tags=["知识库"])
app.include_router(users.router, prefix=f"{settings.API_V1_PREFIX}/users", tags=["用户"])
app.include_router(image_analysis.router, prefix=f"{settings.API_V1_PREFIX}/image", tags=["图片分析"])
app.include_router(health.router, prefix=f"{settings.API_V1_PREFIX}", tags=["监控"])  # /api/v1/health

# 覆盖根路径 /health
@app.get("/health", tags=["监控"])
async def root_health_check():
    """根健康检查（重定向到API v1）"""
    return {"status": "healthy", "detail_url": f"{settings.API_V1_PREFIX}/health"}
