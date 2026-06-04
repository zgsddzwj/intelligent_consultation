"""基础设施层 - 企业级运维组件

包含核心组件：
- cache: 多级缓存系统（本地LRU + Redis）
- monitoring: 监控与告警（Prometheus指标、告警状态机）
- rate_limit: 限流控制
- retry: 重试策略
- graceful_shutdown: 优雅关闭管理
- resource_manager: 资源池管理与监控
- repositories: 数据访问层
"""

from .cache import CacheManager

# 向后兼容别名
MultiLevelCache = CacheManager
from .monitoring import init_app_info, get_metrics
from .graceful_shutdown import shutdown_manager, GracefulShutdownManager
from .resource_manager import ResourcePool, ResourceMonitor, resource_monitor

__all__ = [
    "MultiLevelCache",
    "init_app_info",
    "get_metrics",
    "shutdown_manager",
    "GracefulShutdownManager",
    "ResourcePool",
    "ResourceMonitor",
    "resource_monitor",
]
