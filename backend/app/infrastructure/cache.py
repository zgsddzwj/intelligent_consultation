"""缓存工具和装饰器 - 极致优化版（多级缓存、缓存预热、一致性保障、命中率监控）"""
import hashlib
import json
import time
import threading
from functools import wraps
from typing import Callable, Any, Optional, Dict, List
from collections import OrderedDict
from app.services.redis_service import redis_service
from app.config import get_settings
from app.utils.logger import app_logger

settings = get_settings()


# ========== 本地LRU缓存（L1缓存） ==========
class LocalLRUCache:
    """线程安全的本地LRU缓存"""

    def __init__(self, max_size: int = 1000, default_ttl: int = 60):
        self._cache = OrderedDict()
        self._lock = threading.RLock()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            entry = self._cache[key]
            if time.time() > entry["expires_at"]:
                del self._cache[key]
                self._misses += 1
                return None

            self._cache.move_to_end(key)
            self._hits += 1
            return entry["value"]

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= self._max_size:
                    self._cache.popitem(last=False)

            self._cache[key] = {
                "value": value,
                "expires_at": time.time() + (ttl or self._default_ttl)
            }

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self):
        with self._lock:
            self._cache.clear()

    def get_stats(self) -> dict:
        with self._lock:
            total = self._hits + self._misses
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(self._hits / total * 100, 2) if total > 0 else 0
            }


# 全局L1缓存
local_cache = LocalLRUCache(max_size=500, default_ttl=30)


# ========== 缓存统计指标 ==========
class CacheStats:
    """缓存统计 - 增强版（支持多级缓存）"""

    def __init__(self):
        self._hits_l1 = 0
        self._hits_l2 = 0
        self._misses = 0
        self._errors = 0
        self._writes = 0
        self._invalidations = 0
        self._total_lookup_time = 0.0
        self._lock = threading.Lock()

    def record_hit(self, level: str, lookup_time: float = 0.0):
        with self._lock:
            if level == "l1":
                self._hits_l1 += 1
            elif level == "l2":
                self._hits_l2 += 1
            self._total_lookup_time += lookup_time

    def record_miss(self, lookup_time: float = 0.0):
        with self._lock:
            self._misses += 1
            self._total_lookup_time += lookup_time

    def record_error(self):
        with self._lock:
            self._errors += 1

    def record_write(self, level: str = "l2"):
        with self._lock:
            self._writes += 1

    def record_invalidation(self, count: int = 1):
        with self._lock:
            self._invalidations += count

    def get_stats(self) -> dict:
        with self._lock:
            total = self._hits_l1 + self._hits_l2 + self._misses
            hit_rate = ((self._hits_l1 + self._hits_l2) / total * 100) if total > 0 else 0.0
            avg_lookup_time = (self._total_lookup_time / total) if total > 0 else 0.0

            return {
                "hits_l1": self._hits_l1,
                "hits_l2": self._hits_l2,
                "misses": self._misses,
                "errors": self._errors,
                "writes": self._writes,
                "invalidations": self._invalidations,
                "hit_rate_percent": round(hit_rate, 2),
                "avg_lookup_time_ms": round(avg_lookup_time * 1000, 3),
                "total_lookups": total,
                "l1_hit_rate": round(self._hits_l1 / total * 100, 2) if total > 0 else 0,
                "l2_hit_rate": round(self._hits_l2 / total * 100, 2) if total > 0 else 0,
            }

    def reset(self):
        with self._lock:
            self._hits_l1 = 0
            self._hits_l2 = 0
            self._misses = 0
            self._errors = 0
            self._writes = 0
            self._invalidations = 0
            self._total_lookup_time = 0.0


cache_stats = CacheStats()


def _generate_cache_key(func_name: str, *args, **kwargs) -> str:
    key_data = {
        "func": func_name,
        "args": str(args),
        "kwargs": str(sorted(kwargs.items()))
    }
    key_str = json.dumps(key_data, sort_keys=True, ensure_ascii=False, default=str)
    key_hash = hashlib.sha256(key_str.encode()).hexdigest()[:32]
    return f"cache:{func_name}:{key_hash}"


def _scan_keys(pattern: str, count: int = 100) -> list:
    keys = []
    cursor = 0

    try:
        while True:
            cursor, batch = redis_service.client.scan(
                cursor=cursor,
                match=pattern,
                count=count
            )
            keys.extend(batch)
            if cursor == 0:
                break
    except Exception as e:
        app_logger.warning(f"SCAN命令执行失败，模式: {pattern}: {e}")
        try:
            keys = redis_service.client.keys(pattern)
        except Exception as fallback_err:
            app_logger.error(f"keys命令也失败了: {fallback_err}")
            keys = []

    return keys


def cache_result(ttl: Optional[int] = None, key_prefix: str = None,
                 l1_ttl: Optional[int] = None, use_l1: bool = True):
    """
    多级缓存装饰器 - 极致优化版

    L1: 本地LRU缓存（微秒级）
    L2: Redis分布式缓存（毫秒级）

    Args:
        ttl: L2缓存过期时间（秒）
        key_prefix: 缓存键前缀
        l1_ttl: L1缓存过期时间（秒）
        use_l1: 是否启用L1缓存
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            prefix = key_prefix or func.__name__
            cache_key = _generate_cache_key(prefix, *args, **kwargs)

            # L1缓存查找
            if use_l1:
                l1_result = local_cache.get(cache_key)
                if l1_result is not None:
                    lookup_time = time.time() - start_time
                    cache_stats.record_hit("l1", lookup_time)
                    app_logger.debug(f"L1缓存命中: {cache_key}")
                    return l1_result

            # L2缓存查找
            try:
                cached_result = redis_service.get_json(cache_key)
                if cached_result is not None:
                    lookup_time = time.time() - start_time
                    cache_stats.record_hit("l2", lookup_time)
                    app_logger.debug(f"L2缓存命中: {cache_key}")

                    # 回填L1
                    if use_l1:
                        local_cache.set(cache_key, cached_result, ttl=l1_ttl)

                    return cached_result
            except Exception as e:
                cache_stats.record_error()
                app_logger.warning(f"L2缓存读取失败: {cache_key}, {type(e).__name__}")

            # 执行函数
            result = await func(*args, **kwargs)

            # 写入L1
            if use_l1:
                local_cache.set(cache_key, result, ttl=l1_ttl)

            # 写入L2
            try:
                cache_ttl = ttl or settings.REDIS_CACHE_TTL
                redis_service.set_json(cache_key, result, ttl=cache_ttl)
                cache_stats.record_write("l2")
                app_logger.debug(f"L2缓存写入: {cache_key}, TTL: {cache_ttl}")
            except Exception as e:
                error_type = type(e).__name__
                app_logger.warning(f"L2缓存写入失败: {cache_key}, {error_type}: {str(e)[:100]}")
                cache_stats.record_error()

            lookup_time = time.time() - start_time
            cache_stats.record_miss(lookup_time)
            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            prefix = key_prefix or func.__name__
            cache_key = _generate_cache_key(prefix, *args, **kwargs)

            if use_l1:
                l1_result = local_cache.get(cache_key)
                if l1_result is not None:
                    lookup_time = time.time() - start_time
                    cache_stats.record_hit("l1", lookup_time)
                    return l1_result

            try:
                cached_result = redis_service.get_json(cache_key)
                if cached_result is not None:
                    lookup_time = time.time() - start_time
                    cache_stats.record_hit("l2", lookup_time)
                    if use_l1:
                        local_cache.set(cache_key, cached_result, ttl=l1_ttl)
                    return cached_result
            except Exception as e:
                cache_stats.record_error()
                app_logger.warning(f"L2缓存读取失败: {cache_key}, {type(e).__name__}")

            result = func(*args, **kwargs)

            if use_l1:
                local_cache.set(cache_key, result, ttl=l1_ttl)

            try:
                cache_ttl = ttl or settings.REDIS_CACHE_TTL
                redis_service.set_json(cache_key, result, ttl=cache_ttl)
                cache_stats.record_write("l2")
            except Exception as e:
                cache_stats.record_error()

            lookup_time = time.time() - start_time
            cache_stats.record_miss(lookup_time)
            return result

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def invalidate_cache(key_pattern: str, invalidate_l1: bool = True) -> int:
    """使缓存失效（L1 + L2）"""
    deleted_count = 0

    # 失效L1
    if invalidate_l1:
        # L1不支持pattern匹配，这里简单清空（生产环境可优化）
        local_cache.clear()
        app_logger.info("L1本地缓存已清空")

    # 失效L2
    try:
        keys = _scan_keys(key_pattern)

        if keys:
            batch_size = 100
            for i in range(0, len(keys), batch_size):
                batch = keys[i:i + batch_size]
                try:
                    redis_service.client.delete(*batch)
                    deleted_count += len(batch)
                except Exception as e:
                    app_logger.warning(f"批量删除缓存键失败: {e}")

            cache_stats.record_invalidation(deleted_count)
            app_logger.info(f"L2缓存失效: {deleted_count} 个键, 模式: {key_pattern}")

    except Exception as e:
        app_logger.warning(f"缓存失效失败: {key_pattern}, {e}")

    return deleted_count


class CacheWarmer:
    """缓存预热器"""

    @staticmethod
    def warm_cache(keys_and_values: List[Dict[str, Any]], ttl: Optional[int] = None):
        """批量预热缓存"""
        warmed = 0
        for item in keys_and_values:
            key = item.get("key")
            value = item.get("value")
            if key and value is not None:
                try:
                    cache_ttl = ttl or settings.REDIS_CACHE_TTL
                    redis_service.set_json(key, value, ttl=cache_ttl)
                    warmed += 1
                except Exception as e:
                    app_logger.warning(f"缓存预热失败: {key}, {e}")

        app_logger.info(f"缓存预热完成: {warmed}/{len(keys_and_values)} 个键")
        return warmed

    @staticmethod
    def warm_common_queries(warm_data: Dict[str, Any], ttl: int = 3600):
        """预热常用查询"""
        items = [{"key": k, "value": v} for k, v in warm_data.items()]
        return CacheWarmer.warm_cache(items, ttl)


class CacheManager:
    """缓存管理器 - 极致优化版（多级缓存）"""

    @staticmethod
    def get(key: str, use_l1: bool = True) -> Optional[Any]:
        """获取缓存（L1 -> L2）"""
        if use_l1:
            l1_result = local_cache.get(key)
            if l1_result is not None:
                cache_stats.record_hit("l1")
                return l1_result

        try:
            result = redis_service.get_json(key)
            if result is not None:
                cache_stats.record_hit("l2")
                if use_l1:
                    local_cache.set(key, result)
                return result
        except Exception as e:
            cache_stats.record_error()
            app_logger.warning(f"缓存获取失败: {key}, {e}")

        cache_stats.record_miss()
        return None

    @staticmethod
    def set(key: str, value: Any, ttl: Optional[int] = None, use_l1: bool = True) -> bool:
        """设置缓存（L1 + L2）"""
        if use_l1:
            local_cache.set(key, value, ttl=min(ttl or 60, 60))

        try:
            result = redis_service.set_json(key, value, ttl=ttl)
            if result:
                cache_stats.record_write("l2")
            return result
        except Exception as e:
            cache_stats.record_error()
            app_logger.warning(f"缓存设置失败: {key}, {e}")
            return False

    @staticmethod
    def delete(key: str, invalidate_l1: bool = True) -> bool:
        """删除缓存"""
        if invalidate_l1:
            local_cache.delete(key)

        try:
            result = redis_service.delete(key)
            if result:
                cache_stats.record_invalidation(1)
            return result
        except Exception as e:
            app_logger.warning(f"缓存删除失败: {key}, {e}")
            return False

    @staticmethod
    def clear_pattern(pattern: str, invalidate_l1: bool = True) -> int:
        """按模式清除缓存"""
        return invalidate_cache(pattern, invalidate_l1)

    @staticmethod
    def exists(key: str) -> bool:
        try:
            return redis_service.exists(key)
        except Exception as e:
            app_logger.warning(f"缓存存在性检查失败: {key}, {e}")
            return False

    @staticmethod
    def get_stats() -> dict:
        """获取完整缓存统计"""
        stats = cache_stats.get_stats()
        stats["l1_cache"] = local_cache.get_stats()
        return stats

    @staticmethod
    def reset_stats():
        cache_stats.reset()

    @staticmethod
    def clear_all():
        """清空所有缓存"""
        local_cache.clear()
        try:
            redis_service.client.flushdb()
            app_logger.info("所有缓存已清空")
        except Exception as e:
            app_logger.error(f"清空Redis缓存失败: {e}")

    @staticmethod
    def get_cache_key_pattern(func_name: str, *args, **kwargs) -> str:
        """获取缓存键模式"""
        return _generate_cache_key(func_name, *args, **kwargs)
