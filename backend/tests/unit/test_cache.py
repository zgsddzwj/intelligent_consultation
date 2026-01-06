"""缓存功能测试"""
import pytest
from app.infrastructure.cache import cache_result, CacheManager


def test_cache_result_decorator(mock_redis):
    """测试缓存装饰器"""
    call_count = 0
    
    @cache_result(ttl=60)
    def expensive_function(x, y):
        nonlocal call_count
        call_count += 1
        return x + y
    
    # 第一次调用，应该执行函数
    result1 = expensive_function(1, 2)
    assert result1 == 3
    assert call_count == 1
    
    # 第二次调用，应该从缓存获取
    result2 = expensive_function(1, 2)
    assert result2 == 3
    assert call_count == 1  # 不应该再次执行


def test_cache_manager(mock_redis):
    """测试缓存管理器"""
    # 设置缓存
    CacheManager.set("test_key", {"data": "value"}, ttl=60)
    
    # 获取缓存
    result = CacheManager.get("test_key")
    assert result == {"data": "value"}
    
    # 删除缓存
    CacheManager.delete("test_key")
    result = CacheManager.get("test_key")
    assert result is None

