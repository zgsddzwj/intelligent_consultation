"""优化的Redis服务 - 支持连接池和智能重连"""
import redis
import json
import asyncio
from typing import Optional, Any, Dict
from redis.connection import ConnectionPool
from app.config import get_settings
from app.utils.logger import app_logger

settings = get_settings()


class RedisServiceOptimized:
    """优化的Redis服务类 - 支持连接池、智能重连、健康检查"""
    
    def __init__(self):
        self.redis_url = settings.REDIS_URL or "redis://localhost:6379/0"
        self.pool: Optional[ConnectionPool] = None
        self.client: Optional[redis.Redis] = None
        self._max_retries = 3
        self._retry_delay = 1.0
        self._init_pool()
        
    def _init_pool(self):
        """初始化连接池"""
        try:
            # 连接池配置：最大连接数、最小空闲连接数、连接超时
            self.pool = redis.ConnectionPool.from_url(
                self.redis_url,
                max_connections=20,  # 最大连接数
                socket_connect_timeout=3,  # 连接超时（秒）
                socket_timeout=3,  # 读写超时（秒）
                socket_keepalive=True,  # 启用TCP Keep-Alive
                socket_keepalive_options={
                    1: 1,  # TCP_KEEPIDLE: 1秒后开始探测
                    2: 1,  # TCP_KEEPINTVL: 探测间隔1秒
                    3: 3,  # TCP_KEEPCNT: 最多3次探测
                } if hasattr(redis.connection, 'TCP_KEEPIDLE') else None,
                retry_on_timeout=True,
                health_check_interval=30,  # 30秒健康检查间隔
                decode_responses=True,
                encoding="utf-8",
            )
            
            self.client = redis.Redis(connection_pool=self.pool)
            # 测试连接
            self.client.ping()
            app_logger.info(f"✓ Redis连接池初始化成功: {self.redis_url}")
        except Exception as e:
            app_logger.error(f"✗ Redis连接池初始化失败: {e}")
            self.pool = None
            self.client = None
    
    async def _ensure_connection_async(self) -> bool:
        """异步方式确保连接可用"""
        for attempt in range(self._max_retries):
            if self.client:
                try:
                    self.client.ping()
                    return True
                except Exception as e:
                    app_logger.warning(f"Redis ping失败 (尝试 {attempt + 1}/{self._max_retries}): {e}")
            
            if attempt < self._max_retries - 1:
                await asyncio.sleep(self._retry_delay)
                self._init_pool()
        
        return False
    
    def _ensure_connection(self) -> bool:
        """同步方式确保连接可用"""
        if not self.client:
            self._init_pool()
            return self.client is not None
        
        try:
            self.client.ping()
            return True
        except Exception as e:
            app_logger.warning(f"Redis连接失败，尝试重新初始化: {e}")
            self._init_pool()
            return self.client is not None
    
    def get(self, key: str) -> Optional[str]:
        """获取值"""
        if not self._ensure_connection():
            return None
        
        try:
            return self.client.get(key)
        except redis.RedisError as e:
            app_logger.error(f"Redis GET错误 [{key}]: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置值，支持自动TTL"""
        if not self._ensure_connection():
            return False
        
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            
            ttl = ttl or getattr(settings, 'REDIS_CACHE_TTL', 3600)
            self.client.setex(key, ttl, value)
            return True
        except redis.RedisError as e:
            app_logger.error(f"Redis SET错误 [{key}]: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """删除键"""
        if not self._ensure_connection():
            return False
        
        try:
            return bool(self.client.delete(key))
        except redis.RedisError as e:
            app_logger.error(f"Redis DELETE错误 [{key}]: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """删除匹配模式的所有键"""
        if not self._ensure_connection():
            return 0
        
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except redis.RedisError as e:
            app_logger.error(f"Redis PATTERN DELETE错误 [{pattern}]: {e}")
            return 0
    
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if not self._ensure_connection():
            return False
        
        try:
            return bool(self.client.exists(key))
        except redis.RedisError as e:
            app_logger.error(f"Redis EXISTS错误 [{key}]: {e}")
            return False
    
    def get_json(self, key: str) -> Optional[Dict]:
        """获取JSON值"""
        value = self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError as e:
                app_logger.error(f"JSON解析错误 [{key}]: {e}")
                return None
        return None
    
    def set_json(self, key: str, value: dict, ttl: Optional[int] = None) -> bool:
        """设置JSON值"""
        return self.set(key, value, ttl)
    
    def incr(self, key: str, increment: int = 1) -> Optional[int]:
        """原子递增"""
        if not self._ensure_connection():
            return None
        
        try:
            return self.client.incrby(key, increment)
        except redis.RedisError as e:
            app_logger.error(f"Redis INCR错误 [{key}]: {e}")
            return None
    
    def ttl(self, key: str) -> int:
        """获取键的剩余TTL（秒）"""
        if not self._ensure_connection():
            return -1
        
        try:
            return self.client.ttl(key)
        except redis.RedisError as e:
            app_logger.error(f"Redis TTL错误 [{key}]: {e}")
            return -1
    
    def expire(self, key: str, seconds: int) -> bool:
        """设置键过期时间"""
        if not self._ensure_connection():
            return False
        
        try:
            return bool(self.client.expire(key, seconds))
        except redis.RedisError as e:
            app_logger.error(f"Redis EXPIRE错误 [{key}]: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """获取健康检查详情"""
        if not self.client:
            return {"status": "unhealthy", "reason": "未初始化"}
        
        try:
            info = self.client.info('server')
            return {
                "status": "healthy",
                "version": info.get('redis_version'),
                "uptime_seconds": info.get('uptime_in_seconds'),
                "connected_clients": info.get('connected_clients'),
                "used_memory_mb": info.get('used_memory') / 1024 / 1024 if info.get('used_memory') else 0,
            }
        except redis.RedisError as e:
            return {"status": "unhealthy", "reason": str(e)}
    
    def flush_all(self) -> bool:
        """清空所有数据（仅用于开发/测试）"""
        if not self._ensure_connection():
            return False
        
        try:
            self.client.flushall()
            app_logger.warning("Redis: 已清空所有数据")
            return True
        except redis.RedisError as e:
            app_logger.error(f"Redis FLUSH_ALL错误: {e}")
            return False
    
    def close(self):
        """关闭连接池"""
        if self.pool:
            self.pool.disconnect()
            app_logger.info("Redis连接池已关闭")


# 全局Redis服务实例
redis_service = RedisServiceOptimized()
