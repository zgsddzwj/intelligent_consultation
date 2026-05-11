"""多层缓存服务 - L1本地缓存 + L2 Redis缓存策略"""
import json
import time
import hashlib
from typing import Optional, Any, Dict, Callable
from functools import wraps
from app.services.redis_service import redis_service
from app.utils.logger import app_logger


class LocalCache:
    """L1本地内存缓存 - 超高性能"""
    
    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, tuple] = {}  # (value, ttl_time)
        self.max_size = max_size
        self.access_count = {}  # 用于LRU淘汰
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key in self.cache:
            value, ttl_time = self.cache[key]
            # 检查是否过期
            if ttl_time > 0 and time.time() > ttl_time:
                del self.cache[key]
                return None
            
            self.access_count[key] = time.time()
            return value
        return None
    
    def set(self, key: str, value: Any, ttl: int = 3600):
        """设置缓存值"""
        # 如果达到最大大小，淘汰最少访问的项
        if len(self.cache) >= self.max_size:
            lru_key = min(self.access_count, key=self.access_count.get)
            del self.cache[lru_key]
            del self.access_count[lru_key]
        
        ttl_time = time.time() + ttl if ttl > 0 else -1
        self.cache[key] = (value, ttl_time)
        self.access_count[key] = time.time()
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        if key in self.cache:
            del self.cache[key]
            del self.access_count.get(key, None)
            return True
        return False
    
    def clear(self):
        """清空缓存"""
        self.cache.clear()
        self.access_count.clear()
    
    def get_stats(self) -> Dict[str, int]:
        """获取缓存统计"""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "utilization_percent": int((len(self.cache) / self.max_size) * 100)
        }


class MultiLayerCacheService:
    """多层缓存服务 - L1本地 + L2 Redis"""
    
    def __init__(self, enable_l1: bool = True, enable_l2: bool = True):
        self.enable_l1 = enable_l1
        self.enable_l2 = enable_l2
        self.l1_cache = LocalCache(max_size=1000) if enable_l1 else None
        
        # 缓存键的前缀配置
        self.prefix = "mlc:"
        
        # 统计数据
        self.stats = {
            "l1_hits": 0,
            "l1_misses": 0,
            "l2_hits": 0,
            "l2_misses": 0,
            "total_requests": 0,
        }
    
    def _make_key(self, namespace: str, key: str) -> str:
        """生成缓存键"""
        return f"{self.prefix}{namespace}:{key}"
    
    def get(self, namespace: str, key: str) -> Optional[Any]:
        """获取缓存值（优先L1，再L2）"""
        self.stats["total_requests"] += 1
        full_key = self._make_key(namespace, key)
        
        # L1查询
        if self.enable_l1:
            value = self.l1_cache.get(full_key)
            if value is not None:
                self.stats["l1_hits"] += 1
                app_logger.debug(f"✓ L1缓存命中: {full_key}")
                return value
            else:
                self.stats["l1_misses"] += 1
        
        # L2查询
        if self.enable_l2:
            try:
                value = redis_service.get_json(full_key)
                if value is not None:
                    self.stats["l2_hits"] += 1
                    # 回源到L1
                    if self.enable_l1:
                        self.l1_cache.set(full_key, value, ttl=300)
                    app_logger.debug(f"✓ L2缓存命中: {full_key}")
                    return value
                else:
                    self.stats["l2_misses"] += 1
            except Exception as e:
                app_logger.warning(f"L2缓存查询失败: {e}")
        
        return None
    
    def set(self, namespace: str, key: str, value: Any, 
            l1_ttl: int = 300, l2_ttl: int = 3600):
        """设置多层缓存"""
        full_key = self._make_key(namespace, key)
        
        # 写入L2（Redis）
        if self.enable_l2:
            try:
                redis_service.set_json(full_key, value if isinstance(value, dict) else {"value": value}, ttl=l2_ttl)
                app_logger.debug(f"✓ L2缓存写入: {full_key} (TTL={l2_ttl}s)")
            except Exception as e:
                app_logger.warning(f"L2缓存写入失败: {e}")
        
        # 写入L1（本地）
        if self.enable_l1:
            self.l1_cache.set(full_key, value, ttl=l1_ttl)
            app_logger.debug(f"✓ L1缓存写入: {full_key} (TTL={l1_ttl}s)")
    
    def delete(self, namespace: str, key: str) -> bool:
        """删除多层缓存"""
        full_key = self._make_key(namespace, key)
        
        # 删除L1
        l1_result = True
        if self.enable_l1:
            l1_result = self.l1_cache.delete(full_key)
        
        # 删除L2
        l2_result = True
        if self.enable_l2:
            try:
                l2_result = redis_service.delete(full_key)
            except Exception as e:
                app_logger.warning(f"L2缓存删除失败: {e}")
                l2_result = False
        
        app_logger.info(f"✓ 缓存已删除: {full_key}")
        return l1_result and l2_result
    
    def delete_pattern(self, namespace: str, pattern: str) -> int:
        """删除匹配模式的缓存"""
        full_pattern = self._make_key(namespace, pattern)
        
        # 删除L2中的模式匹配键
        count = 0
        if self.enable_l2:
            try:
                count = redis_service.delete_pattern(full_pattern)
            except Exception as e:
                app_logger.warning(f"L2模式删除失败: {e}")
        
        app_logger.info(f"✓ 已删除 {count} 个匹配的缓存键: {full_pattern}")
        return count
    
    def clear(self, namespace: Optional[str] = None) -> bool:
        """清空缓存"""
        if namespace:
            pattern = self._make_key(namespace, "*")
            self.delete_pattern(namespace, "*")
        
        if self.enable_l1:
            self.l1_cache.clear()
        
        app_logger.info(f"✓ 缓存已清空: {namespace or '全部'}")
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        l1_hit_rate = 0
        l2_hit_rate = 0
        
        total_l1 = self.stats["l1_hits"] + self.stats["l1_misses"]
        if total_l1 > 0:
            l1_hit_rate = (self.stats["l1_hits"] / total_l1) * 100
        
        total_l2 = self.stats["l2_hits"] + self.stats["l2_misses"]
        if total_l2 > 0:
            l2_hit_rate = (self.stats["l2_hits"] / total_l2) * 100
        
        return {
            "total_requests": self.stats["total_requests"],
            "l1": {
                "hits": self.stats["l1_hits"],
                "misses": self.stats["l1_misses"],
                "hit_rate": f"{l1_hit_rate:.2f}%",
                "stats": self.l1_cache.get_stats() if self.l1_cache else {}
            },
            "l2": {
                "hits": self.stats["l2_hits"],
                "misses": self.stats["l2_misses"],
                "hit_rate": f"{l2_hit_rate:.2f}%"
            }
        }
    
    def warm_up(self, namespace: str, data: Dict[str, Any], ttl: int = 3600):
        """缓存预热 - 批量加载数据"""
        count = 0
        for key, value in data.items():
            self.set(namespace, key, value, l2_ttl=ttl)
            count += 1
        
        app_logger.info(f"✓ 缓存预热完成: {namespace} ({count} 项)")


class CacheDecorator:
    """缓存装饰器 - 为函数结果自动缓存"""
    
    def __init__(self, cache_service: MultiLayerCacheService, 
                 namespace: str, ttl: int = 3600):
        self.cache_service = cache_service
        self.namespace = namespace
        self.ttl = ttl
    
    def __call__(self, func: Callable) -> Callable:
        """装饰函数"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键（基于函数名和参数）
            cache_key = self._make_cache_key(func.__name__, args, kwargs)
            
            # 尝试从缓存获取
            cached_value = self.cache_service.get(self.namespace, cache_key)
            if cached_value is not None:
                app_logger.debug(f"✓ 函数缓存命中: {func.__name__}")
                return cached_value
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 缓存结果
            if result is not None:
                self.cache_service.set(
                    self.namespace,
                    cache_key,
                    result,
                    l2_ttl=self.ttl
                )
            
            return result
        
        return wrapper
    
    @staticmethod
    def _make_cache_key(func_name: str, args: tuple, kwargs: dict) -> str:
        """生成缓存键"""
        key_parts = [func_name]
        
        # 添加位置参数
        for arg in args:
            if isinstance(arg, (str, int, float, bool)):
                key_parts.append(str(arg))
        
        # 添加关键字参数
        for k, v in sorted(kwargs.items()):
            if isinstance(v, (str, int, float, bool)):
                key_parts.append(f"{k}={v}")
        
        # 使用MD5哈希缩短键
        key_str = "|".join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()


# 全局缓存服务实例
cache_service = MultiLayerCacheService(enable_l1=True, enable_l2=True)


# 便捷装饰器工厂
def cached(namespace: str, ttl: int = 3600):
    """缓存装饰器工厂"""
    return CacheDecorator(cache_service, namespace, ttl)
