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
        self._init_client()
        
    def _init_client(self):
        """初始化Redis客户端"""
        redis_url = settings.REDIS_URL or "redis://localhost:6379/0"
        
        try:
            self.client = redis.from_url(
                redis_url,
                decode_responses=True,
                encoding="utf-8",
                socket_connect_timeout=2,
                socket_timeout=2,
                retry_on_timeout=False  # 我们自己处理重试
            )
            # 测试连接
            self.client.ping()
            app_logger.info(f"Redis连接成功: {redis_url}")
        except Exception as e:
            app_logger.warning(f"Redis连接失败: {e}，将在使用时尝试重连")
            # 即使连接失败，我们也保留client对象（如果是连接错误），
            # 但如果from_url失败（如配置错误），client可能是None
            # 这里我们不置为None，依赖redis-py的重试机制（如果是连接问题）
            # 或者在方法中重新检查
    
    def _ensure_connection(self) -> bool:
        """确保连接可用"""
        if self.client:
            try:
                self.client.ping()
                return True
            except Exception:
                pass
        
        # 尝试重新初始化
        self._init_client()
        return self.client is not None
    
    def get(self, key: str) -> Optional[str]:
        """获取值"""
        if not self.client:
            self._init_client()
            
        if not self.client:
            return None
            
        try:
            return self.client.get(key)
        except Exception as e:
            app_logger.warning(f"Redis get操作失败: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置值"""
        if not self.client:
            self._init_client()
            
        if not self.client:
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
        if not self.client:
            self._init_client()
            
        if not self.client:
            return False
            
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            app_logger.warning(f"Redis delete操作失败: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if not self.client:
            self._init_client()
            
        if not self.client:
            return False
            
        try:
            return bool(self.client.exists(key))
        except Exception as e:
            app_logger.warning(f"Redis exists操作失败: {e}")
            return False
    
    def get_json(self, key: str) -> Optional[dict]:
        """获取JSON值"""
        value = self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None
    
    def set_json(self, key: str, value: dict, ttl: Optional[int] = None) -> bool:
        """设置JSON值"""
        return self.set(key, value, ttl)
    
    def health_check(self) -> bool:
        """健康检查"""
        if not self.client:
            self._init_client()
        
        if not self.client:
            return False
            
        try:
            return self.client.ping()
        except Exception:
            return False


# 全局Redis实例
redis_service = RedisService()

