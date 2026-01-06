"""Redis服务"""
import redis
import json
from typing import Optional, Any
from app.config import get_settings

settings = get_settings()


class RedisService:
    """Redis服务类"""
    
    def __init__(self):
        self.client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            encoding="utf-8"
        )
    
    def get(self, key: str) -> Optional[str]:
        """获取值"""
        return self.client.get(key)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置值"""
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        ttl = ttl or settings.REDIS_CACHE_TTL
        return self.client.setex(key, ttl, value)
    
    def delete(self, key: str) -> bool:
        """删除键"""
        return bool(self.client.delete(key))
    
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        return bool(self.client.exists(key))
    
    def get_json(self, key: str) -> Optional[dict]:
        """获取JSON值"""
        value = self.get(key)
        if value:
            return json.loads(value)
        return None
    
    def set_json(self, key: str, value: dict, ttl: Optional[int] = None) -> bool:
        """设置JSON值"""
        return self.set(key, value, ttl)


# 全局Redis实例
redis_service = RedisService()

