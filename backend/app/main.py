"""FastAPI应用入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.utils.logger import app_logger
from app.api.middleware import LoggingMiddleware

settings = get_settings()

# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="智能医疗管家平台API",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加日志中间件
app.add_middleware(LoggingMiddleware)


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    app_logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} 启动成功")
    app_logger.info(f"环境: {settings.ENVIRONMENT}")
    app_logger.info(f"调试模式: {settings.DEBUG}")


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


# 导入路由
from app.api.v1 import consultation, agents, knowledge, users, image_analysis
app.include_router(consultation.router, prefix=settings.API_V1_PREFIX, tags=["咨询"])
app.include_router(agents.router, prefix=settings.API_V1_PREFIX, tags=["Agent"])
app.include_router(knowledge.router, prefix=settings.API_V1_PREFIX, tags=["知识库"])
app.include_router(users.router, prefix=settings.API_V1_PREFIX, tags=["用户"])
app.include_router(image_analysis.router, prefix=settings.API_V1_PREFIX, tags=["图片分析"])

