"""Redis服务"""
import redis
import json
from typing import Optional, Any
from app.config import get_settings
from app.utils.logger import app_logger

settings = get_settings()


class RedisService:
    """Redis服务类"""
    
    def __init__(self):
        self.client = None
        self.enabled = False
        
        # 如果REDIS_URL未配置或为空，使用默认本地Redis
        redis_url = settings.REDIS_URL or "redis://localhost:6379/0"
        
        try:
        self.client = redis.from_url(
                redis_url,
            decode_responses=True,
                encoding="utf-8",
                socket_connect_timeout=2,
                socket_timeout=2,
                retry_on_timeout=False
            )
            # 测试连接
            self.client.ping()
            self.enabled = True
            app_logger.info(f"Redis连接成功: {redis_url}")
        except redis.ConnectionError as e:
            app_logger.warning(f"Redis连接失败: {e}，限流和缓存功能将不可用")
            self.enabled = False
            self.client = None
        except redis.AuthenticationError as e:
            app_logger.warning(f"Redis认证失败: {e}，请检查REDIS_URL中的密码配置")
            self.enabled = False
            self.client = None
        except Exception as e:
            app_logger.warning(f"Redis初始化失败: {e}，限流和缓存功能将不可用")
            self.enabled = False
            self.client = None
    
    def get(self, key: str) -> Optional[str]:
        """获取值"""
        if not self.enabled or not self.client:
            return None
        try:
        return self.client.get(key)
        except Exception as e:
            app_logger.warning(f"Redis get操作失败: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置值"""
        if not self.enabled or not self.client:
            return False
        try:
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        ttl = ttl or settings.REDIS_CACHE_TTL
        return self.client.setex(key, ttl, value)
        except Exception as e:
            app_logger.warning(f"Redis set操作失败: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """删除键"""
        if not self.enabled or not self.client:
            return False
        try:
        return bool(self.client.delete(key))
        except Exception as e:
            app_logger.warning(f"Redis delete操作失败: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if not self.enabled or not self.client:
            return False
        try:
        return bool(self.client.exists(key))
        except Exception as e:
            app_logger.warning(f"Redis exists操作失败: {e}")
            return False
    
    def get_json(self, key: str) -> Optional[dict]:
        """获取JSON值"""
        if not self.enabled:
            return None
        value = self.get(key)
        if value:
            try:
            return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None
    
    def set_json(self, key: str, value: dict, ttl: Optional[int] = None) -> bool:
        """设置JSON值"""
        if not self.enabled:
            return False
        return self.set(key, value, ttl)


# 全局Redis实例
redis_service = RedisService()

