"""资源管理器 - 连接池管理、资源监控、自动回收"""
import time
import threading
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from app.utils.logger import app_logger


@dataclass
class ResourceStats:
    """资源统计"""
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    use_count: int = 0
    error_count: int = 0


class ResourcePool:
    """通用资源池"""

    def __init__(self, name: str, max_size: int = 10, idle_timeout: float = 300.0):
        self.name = name
        self.max_size = max_size
        self.idle_timeout = idle_timeout
        self._resources: Dict[str, Any] = {}
        self._stats: Dict[str, ResourceStats] = {}
        self._lock = threading.RLock()

    def get(self, key: str, factory: callable) -> Any:
        """获取资源（如果不存在则创建）"""
        with self._lock:
            if key in self._resources:
                resource = self._resources[key]
                self._stats[key].last_used = time.time()
                self._stats[key].use_count += 1
                return resource

            # 创建新资源
            if len(self._resources) >= self.max_size:
                self._evict_oldest()

            try:
                resource = factory()
                self._resources[key] = resource
                self._stats[key] = ResourceStats()
                app_logger.debug(f"资源池 {self.name}: 创建资源 {key}")
                return resource
            except Exception as e:
                app_logger.error(f"资源池 {self.name}: 创建资源失败 {key} - {e}")
                raise

    def release(self, key: str):
        """释放资源"""
        with self._lock:
            if key in self._resources:
                resource = self._resources.pop(key)
                self._stats.pop(key, None)
                if hasattr(resource, 'close'):
                    try:
                        resource.close()
                    except Exception as e:
                        app_logger.warning(f"资源池 {self.name}: 关闭资源失败 {key} - {e}")
                app_logger.debug(f"资源池 {self.name}: 释放资源 {key}")

    def _evict_oldest(self):
        """驱逐最久未使用的资源"""
        if not self._stats:
            return

        oldest_key = min(self._stats.keys(), key=lambda k: self._stats[k].last_used)
        app_logger.info(f"资源池 {self.name}: 驱逐最久未使用资源 {oldest_key}")
        self.release(oldest_key)

    def cleanup_idle(self):
        """清理空闲资源"""
        now = time.time()
        to_release = []

        with self._lock:
            for key, stats in self._stats.items():
                if now - stats.last_used > self.idle_timeout:
                    to_release.append(key)

        for key in to_release:
            self.release(key)

        if to_release:
            app_logger.info(f"资源池 {self.name}: 清理 {len(to_release)} 个空闲资源")

    def get_stats(self) -> Dict[str, Any]:
        """获取资源池统计"""
        with self._lock:
            return {
                "name": self.name,
                "size": len(self._resources),
                "max_size": self.max_size,
                "resources": {
                    key: {
                        "use_count": stat.use_count,
                        "error_count": stat.error_count,
                        "idle_seconds": round(time.time() - stat.last_used, 2)
                    }
                    for key, stat in self._stats.items()
                }
            }


class ResourceMonitor:
    """资源监控器 - 定期检查和报告资源使用情况"""

    def __init__(self, interval: float = 60.0):
        self.interval = interval
        self._pools: List[ResourcePool] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def register_pool(self, pool: ResourcePool):
        """注册资源池"""
        self._pools.append(pool)

    def start(self):
        """启动监控"""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        app_logger.info("资源监控器已启动")

    def stop(self):
        """停止监控"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
        app_logger.info("资源监控器已停止")

    def _monitor_loop(self):
        """监控循环"""
        while self._running:
            try:
                for pool in self._pools:
                    # 清理空闲资源
                    pool.cleanup_idle()
                    # 记录统计
                    stats = pool.get_stats()
                    if stats["size"] > stats["max_size"] * 0.8:
                        app_logger.warning(f"资源池 {pool.name} 使用率过高: {stats['size']}/{stats['max_size']}")
            except Exception as e:
                app_logger.error(f"资源监控异常: {e}")

            time.sleep(self.interval)


# 全局资源管理
resource_monitor = ResourceMonitor()
