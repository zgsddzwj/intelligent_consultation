"""API v1 路由模块

包含所有v1版本API路由：
- consultation: 咨询相关
- agents: Agent管理
- knowledge: 知识库
- users: 用户管理
- image_analysis: 图片分析
- health: 健康检查与监控
"""

from .consultation import router as consultation_router
from .agents import router as agents_router
from .knowledge import router as knowledge_router
from .users import router as users_router
from .image_analysis import router as image_analysis_router
from .health import router as health_router

__all__ = [
    "consultation_router",
    "agents_router",
    "knowledge_router",
    "users_router",
    "image_analysis_router",
    "health_router",
]
