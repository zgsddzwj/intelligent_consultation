"""缓存工具和装饰器"""
import hashlib
import json
from functools import wraps
from typing import Callable, Any, Optional
from app.services.redis_service import redis_service
from app.config import get_settings
from app.utils.logger import app_logger

settings = get_settings()


def _generate_cache_key(func_name: str, *args, **kwargs) -> str:
    """生成缓存键"""
    # 将参数序列化为字符串
    key_data = {
        "func": func_name,
        "args": str(args),
        "kwargs": str(sorted(kwargs.items()))
    }
    key_str = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
    # 使用MD5生成固定长度的键
    key_hash = hashlib.md5(key_str.encode()).hexdigest()
    return f"cache:{func_name}:{key_hash}"


def cache_result(ttl: Optional[int] = None, key_prefix: str = None):
    """
    缓存函数结果装饰器
    
    Args:
        ttl: 缓存过期时间（秒），默认使用配置的REDIS_CACHE_TTL
        key_prefix: 缓存键前缀
    
    Usage:
        @cache_result(ttl=3600)
        def my_function(arg1, arg2):
            # 函数逻辑
            return result
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 生成缓存键
            prefix = key_prefix or func.__name__
            cache_key = _generate_cache_key(prefix, *args, **kwargs)
            
            # 尝试从缓存获取
            try:
                cached_result = redis_service.get_json(cache_key)
                if cached_result is not None:
                    app_logger.debug(f"缓存命中: {cache_key}")
                    return cached_result
            except Exception as e:
                app_logger.warning(f"缓存读取失败: {e}")
            
            # 执行函数
            result = await func(*args, **kwargs)
            
            # 写入缓存
            try:
                cache_ttl = ttl or settings.REDIS_CACHE_TTL
                redis_service.set_json(cache_key, result, ttl=cache_ttl)
                app_logger.debug(f"缓存写入: {cache_key}, TTL: {cache_ttl}")
            except Exception as e:
                app_logger.warning(f"缓存写入失败: {e}")
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 生成缓存键
            prefix = key_prefix or func.__name__
            cache_key = _generate_cache_key(prefix, *args, **kwargs)
            
            # 尝试从缓存获取
            try:
                cached_result = redis_service.get_json(cache_key)
                if cached_result is not None:
                    app_logger.debug(f"缓存命中: {cache_key}")
                    return cached_result
            except Exception as e:
                app_logger.warning(f"缓存读取失败: {e}")
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 写入缓存
            try:
                cache_ttl = ttl or settings.REDIS_CACHE_TTL
                redis_service.set_json(cache_key, result, ttl=cache_ttl)
                app_logger.debug(f"缓存写入: {cache_key}, TTL: {cache_ttl}")
            except Exception as e:
                app_logger.warning(f"缓存写入失败: {e}")
            
            return result
        
        # 判断是否为异步函数
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def invalidate_cache(key_pattern: str):
    """
    使缓存失效
    
    Args:
        key_pattern: 缓存键模式（支持通配符）
    """
    try:
        # 注意：Redis的keys命令在生产环境可能影响性能
        # 建议使用SCAN命令或维护缓存键列表
        keys = redis_service.client.keys(key_pattern)
        if keys:
            redis_service.client.delete(*keys)
            app_logger.info(f"缓存失效: {len(keys)} 个键")
    except Exception as e:
        app_logger.warning(f"缓存失效失败: {e}")


class CacheManager:
    """缓存管理器"""
    
    @staticmethod
    def get(key: str) -> Optional[Any]:
        """获取缓存"""
        try:
            return redis_service.get_json(key)
        except Exception as e:
            app_logger.warning(f"缓存获取失败: {key}, {e}")
            return None
    
    @staticmethod
    def set(key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存"""
        try:
            return redis_service.set_json(key, value, ttl=ttl)
        except Exception as e:
            app_logger.warning(f"缓存设置失败: {key}, {e}")
            return False
    
    @staticmethod
    def delete(key: str) -> bool:
        """删除缓存"""
        try:
            return redis_service.delete(key)
        except Exception as e:
            app_logger.warning(f"缓存删除失败: {key}, {e}")
            return False
    
    @staticmethod
    def clear_pattern(pattern: str) -> int:
        """按模式清除缓存"""
        try:
            keys = redis_service.client.keys(pattern)
            if keys:
                redis_service.client.delete(*keys)
                return len(keys)
            return 0
        except Exception as e:
            app_logger.warning(f"缓存清除失败: {pattern}, {e}")
            return 0

