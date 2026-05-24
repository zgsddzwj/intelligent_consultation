"""API v1版本路由 - 统一响应格式与标准化处理"""
from fastapi import APIRouter
from app.api.v1 import consultation, agents, health, image_analysis, knowledge, users

# 创建v1路由
api_v1_router = APIRouter(prefix="/v1")

# 注册各模块路由
api_v1_router.include_router(consultation.router, prefix="/consultation", tags=["咨询"])
api_v1_router.include_router(agents.router, prefix="/agents", tags=["Agent管理"])
api_v1_router.include_router(health.router, prefix="/health", tags=["健康检查"])
api_v1_router.include_router(image_analysis.router, prefix="/image", tags=["图像分析"])
api_v1_router.include_router(knowledge.router, prefix="/knowledge", tags=["知识库"])
api_v1_router.include_router(users.router, prefix="/users", tags=["用户管理"])
