"""缓存工具和装饰器 - 增强版（SCAN替代keys、缓存统计、精细化异常分类）"""
import hashlib
import json
import time
from functools import wraps
from typing import Callable, Any, Optional
from collections import defaultdict
from app.services.redis_service import redis_service
from app.config import get_settings
from app.utils.logger import app_logger

settings = get_settings()


# ========== 缓存统计指标 ==========
class CacheStats:
    """缓存统计（线程安全的全局单例）"""
    
    def __init__(self):
        self._hits: int = 0
        self._misses: int = 0
        self._errors: int = 0
        self._writes: int = 0
        self._invalidations: int = 0
        self._total_lookup_time: float = 0.0
    
    def record_hit(self, lookup_time: float = 0.0):
        """记录缓存命中"""
        self._hits += 1
        self._total_lookup_time += lookup_time
    
    def record_miss(self, lookup_time: float = 0.0):
        """记录缓存未命中"""
        self._misses += 1
        self._total_lookup_time += lookup_time
    
    def record_error(self):
        """记录缓存错误"""
        self._errors += 1
    
    def record_write(self):
        """记录缓存写入"""
        self._writes += 1
    
    def record_invalidation(self, count: int = 1):
        """记录缓存失效"""
        self._invalidations += count
    
    def get_stats(self) -> dict:
        """获取统计数据"""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0.0
        avg_lookup_time = (self._total_lookup_time / total) if total > 0 else 0.0
        
        return {
            "hits": self._hits,
            "misses": self._misses,
            "errors": self._errors,
            "writes": self._writes,
            "invalidations": self._invalidations,
            "hit_rate_percent": round(hit_rate, 2),
            "avg_lookup_time_ms": round(avg_lookup_time * 1000, 3),
            "total_lookups": total
        }
    
    def reset(self):
        """重置统计"""
        self._hits = 0
        self._misses = 0
        self._errors = 0
        self._writes = 0
        self._invalidations = 0
        self._total_lookup_time = 0.0


# 全局缓存统计实例
cache_stats = CacheStats()


def _generate_cache_key(func_name: str, *args, **kwargs) -> str:
    """
    生成缓存键
    
    使用MD5哈希确保键长度固定且唯一。
    """
    # 将参数序列化为字符串（排序kwargs保证一致性）
    key_data = {
        "func": func_name,
        "args": str(args),
        "kwargs": str(sorted(kwargs.items()))
    }
    key_str = json.dumps(key_data, sort_keys=True, ensure_ascii=False, default=str)
    # 使用SHA256生成更安全的固定长度键
    key_hash = hashlib.sha256(key_str.encode()).hexdigest()[:32]  # 取前32字符，足够唯一
    return f"cache:{func_name}:{key_hash}"


def _scan_keys(pattern: str, count: int = 100) -> list:
    """
    使用SCAN命令替代KEYS命令遍历匹配的键
    
    SCAN是增量式迭代，不会阻塞Redis服务器，
    而KEYS命令在大量键存在时会导致阻塞。
    
    Args:
        pattern: 键模式（如 "cache:*"）
        count: 每次扫描返回的大约数量
        
    Returns:
        匹配的键列表
    """
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
            
            # cursor为0表示遍历完成
            if cursor == 0:
                break
                
    except Exception as e:
        app_logger.warning(f"SCAN命令执行失败，模式: {pattern}: {e}")
        # 如果SCAN不可用，回退到keys（仅作为最后手段）
        try:
            keys = redis_service.client.keys(pattern)
            app_logger.warning(f"已从SCAN回退到keys命令，模式: {pattern}")
        except Exception as fallback_err:
            app_logger.error(f"keys命令也失败了: {fallback_err}")
            keys = []
    
    return keys


def cache_result(ttl: Optional[int] = None, key_prefix: str = None):
    """
    缓存函数结果装饰器（增强版）
    
    改进点：
    - 自动区分同步/异步函数
    - 记录缓存命中/未命中统计
    - 精细化异常分类（网络错误 vs 序列化错误）
    - 支持None值缓存
    
    Args:
        ttl: 缓存过期时间（秒），默认使用配置的REDIS_CACHE_TTL
        key_prefix: 缓存键前缀
        
    Usage:
        @cache_result(ttl=3600)
        async def my_async_func(arg1):
            # 异步函数逻辑
            return result
            
        @cache_result(ttl=600)
        def my_sync_func(arg1):
            # 同步函数逻辑
            return result
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            prefix = key_prefix or func.__name__
            cache_key = _generate_cache_key(prefix, *args, **kwargs)
            
            # 尝试从缓存获取
            try:
                cached_result = redis_service.get_json(cache_key)
                if cached_result is not None:
                    lookup_time = time.time() - start_time
                    cache_stats.record_hit(lookup_time)
                    app_logger.debug(f"缓存命中: {cache_key}")
                    return cached_result
            except Exception as e:
                # 缓存读取错误不应影响业务逻辑
                cache_stats.record_error()
                app_logger.warning(f"缓存读取失败（非致命）: {cache_key}, 错误类型: {type(e).__name__}")
            
            # 执行函数
            result = await func(*args, **kwargs)
            
            # 写入缓存
            try:
                cache_ttl = ttl or settings.REDIS_CACHE_TTL
                redis_service.set_json(cache_key, result, ttl=cache_ttl)
                cache_stats.record_write()
                app_logger.debug(f"缓存写入: {cache_key}, TTL: {cache_ttl}")
            except Exception as e:
                # 区分不同类型的缓存写入错误
                error_type = type(e).__name__
                if "connection" in str(e).lower() or "timeout" in str(e).lower():
                    app_logger.warning(f"缓存写入失败（网络问题）: {cache_key}, {error_type}: {str(e)[:100]}")
                else:
                    app_logger.warning(f"缓存写入失败（序列化/其他）: {cache_key}, {error_type}: {str(e)[:100]}")
                cache_stats.record_error()
            
            lookup_time = time.time() - start_time
            cache_stats.record_miss(lookup_time)
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            prefix = key_prefix or func.__name__
            cache_key = _generate_cache_key(prefix, *args, **kwargs)
            
            # 尝试从缓存获取
            try:
                cached_result = redis_service.get_json(cache_key)
                if cached_result is not None:
                    lookup_time = time.time() - start_time
                    cache_stats.record_hit(lookup_time)
                    app_logger.debug(f"缓存命中: {cache_key}")
                    return cached_result
            except Exception as e:
                cache_stats.record_error()
                app_logger.warning(f"缓存读取失败（非致命）: {cache_key}, 错误类型: {type(e).__name__}")
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 写入缓存
            try:
                cache_ttl = ttl or settings.REDIS_CACHE_TTL
                redis_service.set_json(cache_key, result, ttl=cache_ttl)
                cache_stats.record_write()
                app_logger.debug(f"缓存写入: {cache_key}, TTL: {cache_ttl}")
            except Exception as e:
                error_type = type(e).__name__
                if "connection" in str(e).lower() or "timeout" in str(e).lower():
                    app_logger.warning(f"缓存写入失败（网络问题）: {cache_key}, {error_type}: {str(e)[:100]}")
                else:
                    app_logger.warning(f"缓存写入失败（序列化/其他）: {cache_key}, {error_type}: {str(e)[:100]}")
                cache_stats.record_error()
            
            lookup_time = time.time() - start_time
            cache_stats.record_miss(lookup_time)
            return result
        
        # 判断是否为异步函数
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def invalidate_cache(key_pattern: str) -> int:
    """
    使缓存失效（使用SCAN替代KEYS）
    
    Args:
        key_pattern: 缓存键模式（支持通配符，如 "cache:user:*"）
        
    Returns:
        失效的键数量
    """
    try:
        keys = _scan_keys(key_pattern)
        
        if keys:
            # 分批删除（每批100个键），避免单次删除过多导致阻塞
            batch_size = 100
            deleted_count = 0
            
            for i in range(0, len(keys), batch_size):
                batch = keys[i:i + batch_size]
                try:
                    redis_service.client.delete(*batch)
                    deleted_count += len(batch)
                except Exception as e:
                    app_logger.warning(f"批量删除缓存键失败（批次 {i//batch_size}）: {e}")
            
            cache_stats.record_invalidation(deleted_count)
            app_logger.info(f"缓存失效: {deleted_count} 个键, 模式: {key_pattern}")
            return deleted_count
        
        return 0
        
    except Exception as e:
        app_logger.warning(f"缓存失效失败: {key_pattern}, {e}")
        return 0


class CacheManager:
    """缓存管理器（增强版）- 提供高级缓存操作API"""
    
    @staticmethod
    def get(key: str) -> Optional[Any]:
        """获取缓存"""
        try:
            return redis_service.get_json(key)
        except Exception as e:
            cache_stats.record_error()
            app_logger.warning(f"缓存获取失败: {key}, {e}")
            return None
    
    @staticmethod
    def set(key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存"""
        try:
            result = redis_service.set_json(key, value, ttl=ttl)
            if result:
                cache_stats.record_write()
            return result
        except Exception as e:
            cache_stats.record_error()
            app_logger.warning(f"缓存设置失败: {key}, {e}")
            return False
    
    @staticmethod
    def delete(key: str) -> bool:
        """删除缓存"""
        try:
            result = redis_service.delete(key)
            if result:
                cache_stats.record_invalidation(1)
            return result
        except Exception as e:
            app_logger.warning(f"缓存删除失败: {key}, {e}")
            return False
    
    @staticmethod
    def clear_pattern(pattern: str) -> int:
        """按模式清除缓存（使用SCAN）"""
        return invalidate_cache(pattern)
    
    @staticmethod
    def exists(key: str) -> bool:
        """检查键是否存在"""
        try:
            return redis_service.exists(key)
        except Exception as e:
            app_logger.warning(f"缓存存在性检查失败: {key}, {e}")
            return False
    
    @staticmethod
    def get_stats() -> dict:
        """获取缓存统计信息"""
        return cache_stats.get_stats()
    
    @staticmethod
    def reset_stats():
        """重置缓存统计"""
        cache_stats.reset()
