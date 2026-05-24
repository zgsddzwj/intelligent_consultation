"""Neo4j客户端 - 增强版（查询缓存、批量查询、连接池管理、健康监控）"""
import time
import threading
import hashlib
import json
from typing import List, Dict, Any, Optional
from collections import OrderedDict
from neo4j import GraphDatabase
from app.config import get_settings
from app.utils.logger import app_logger

settings = get_settings()


class LRUCache:
    """线程安全的LRU缓存"""
    
    def __init__(self, max_size: int = 100, ttl: int = 300):
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._timestamps: Dict[str, float] = {}
        self._max_size = max_size
        self._ttl = ttl
        self._lock = threading.Lock()
    
    def _make_key(self, query: str, params: Dict) -> str:
        """生成缓存键"""
        key_data = f"{query}:{json.dumps(params, sort_keys=True, default=str)}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]
    
    def get(self, query: str, params: Dict) -> Optional[Any]:
        """获取缓存结果"""
        key = self._make_key(query, params)
        with self._lock:
            if key in self._cache:
                # 检查TTL
                if time.time() - self._timestamps.get(key, 0) > self._ttl:
                    del self._cache[key]
                    del self._timestamps[key]
                    return None
                
                self._cache.move_to_end(key)
                return self._cache[key]
            return None
    
    def set(self, query: str, params: Dict, value: Any):
        """设置缓存结果"""
        key = self._make_key(query, params)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = value
            self._timestamps[key] = time.time()
            
            # 淘汰旧条目
            while len(self._cache) > self._max_size:
                old_key, _ = self._cache.popitem(last=False)
                self._timestamps.pop(old_key, None)
    
    def invalidate(self, pattern: str = None):
        """使缓存失效"""
        with self._lock:
            if pattern:
                keys_to_remove = [k for k in self._cache.keys() if pattern in k]
                for k in keys_to_remove:
                    del self._cache[k]
                    self._timestamps.pop(k, None)
            else:
                self._cache.clear()
                self._timestamps.clear()
    
    def get_stats(self) -> Dict[str, int]:
        """获取缓存统计"""
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "ttl": self._ttl
            }


class Neo4jClient:
    """Neo4j客户端类（增强版）
    
    新增功能：
    - 查询结果LRU缓存
    - 批量查询支持
    - 连接池配置
    - 查询性能统计
    - 自动重连退避
    """
    
    def __init__(self, cache_size: int = 100, cache_ttl: int = 300):
        self.uri = settings.NEO4J_URI
        self.user = settings.NEO4J_USER
        self.password = settings.NEO4J_PASSWORD
        self.driver = None
        self._connected = False
        self._query_stats = {
            "total_queries": 0,
            "cached_queries": 0,
            "failed_queries": 0,
            "total_time": 0.0
        }
        self._stats_lock = threading.Lock()
        
        # 查询缓存
        self._cache = LRUCache(max_size=cache_size, ttl=cache_ttl)
        
        # 初始化连接
        try:
            self._init_driver()
            self._connected = True
            app_logger.info(f"已连接到Neo4j: {self.uri}")
        except Exception as e:
            app_logger.warning(f"Neo4j连接失败（将在首次使用时重试）: {e}")
            self._connected = False
    
    def _init_driver(self):
        """初始化驱动（带连接池配置）"""
        self.driver = GraphDatabase.driver(
            self.uri,
            auth=(self.user, self.password),
            max_connection_pool_size=20,
            connection_acquisition_timeout=10,
            connection_timeout=10,
            max_transaction_retry_time=30.0
        )
        self.driver.verify_connectivity()
    
    def close(self):
        """关闭连接"""
        if self.driver:
            try:
                self.driver.close()
            except Exception as e:
                app_logger.warning(f"关闭Neo4j连接失败: {e}")
            finally:
                self.driver = None
                self._connected = False
    
    def _ensure_connection(self):
        """确保连接可用（带重试退避）"""
        if not self._connected or not self.driver:
            for attempt in range(3):
                try:
                    if self.driver:
                        try:
                            self.driver.close()
                        except Exception:
                            pass
                    
                    self._init_driver()
                    self._connected = True
                    app_logger.info(f"Neo4j重新连接成功（尝试 {attempt + 1}）")
                    return
                except Exception as e:
                    app_logger.warning(f"Neo4j重连失败 (尝试 {attempt + 1}/3): {e}")
                    time.sleep(0.5 * (attempt + 1))
            
            raise ConnectionError("Neo4j连接失败，已重试3次")
    
    def execute_query(self, query: str, parameters: Optional[Dict] = None,
                      use_cache: bool = True) -> List[Dict[str, Any]]:
        """执行Cypher查询（支持缓存）"""
        parameters = parameters or {}
        
        # 尝试从缓存获取
        if use_cache:
            cached = self._cache.get(query, parameters)
            if cached is not None:
                with self._stats_lock:
                    self._query_stats["cached_queries"] += 1
                return cached
        
        self._ensure_connection()
        
        start_time = time.time()
        try:
            with self.driver.session() as session:
                result = session.run(query, parameters)
                data = [record.data() for record in result]
            
            # 更新统计
            duration = time.time() - start_time
            with self._stats_lock:
                self._query_stats["total_queries"] += 1
                self._query_stats["total_time"] += duration
            
            # 写入缓存
            if use_cache:
                self._cache.set(query, parameters, data)
            
            return data
            
        except Exception as e:
            self._connected = False
            with self._stats_lock:
                self._query_stats["failed_queries"] += 1
            app_logger.warning(f"Neo4j查询失败: {e}")
            raise
    
    def execute_write(self, query: str, parameters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """执行写操作（自动使相关缓存失效）"""
        self._ensure_connection()
        
        try:
            with self.driver.session() as session:
                def work(tx):
                    result = tx.run(query, parameters or {})
                    return [record.data() for record in result]
                
                data = session.execute_write(work)
            
            # 写操作后使缓存失效
            self._cache.invalidate()
            
            return data
            
        except Exception as e:
            self._connected = False
            app_logger.warning(f"Neo4j写操作失败: {e}")
            raise
    
    def execute_batch(self, queries: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        批量执行查询
        
        Args:
            queries: 查询列表，每项为 {"query": str, "parameters": dict, "use_cache": bool}
            
        Returns:
            各查询结果列表
        """
        results = []
        for item in queries:
            try:
                result = self.execute_query(
                    item["query"],
                    item.get("parameters", {}),
                    item.get("use_cache", True)
                )
                results.append(result)
            except Exception as e:
                app_logger.warning(f"批量查询中某条失败: {e}")
                results.append([])
        
        return results
    
    def create_indexes(self):
        """创建索引"""
        indexes = [
            "CREATE INDEX disease_name_idx IF NOT EXISTS FOR (d:Disease) ON (d.name)",
            "CREATE INDEX disease_icd10_idx IF NOT EXISTS FOR (d:Disease) ON (d.icd10)",
            "CREATE INDEX symptom_name_idx IF NOT EXISTS FOR (s:Symptom) ON (s.name)",
            "CREATE INDEX drug_name_idx IF NOT EXISTS FOR (dr:Drug) ON (dr.name)",
            "CREATE INDEX exam_name_idx IF NOT EXISTS FOR (e:Examination) ON (e.name)",
        ]
        
        for index_query in indexes:
            try:
                self.execute_write(index_query)
                app_logger.info(f"索引创建成功: {index_query}")
            except Exception as e:
                app_logger.warning(f"索引创建失败: {e}")
    
    def health_check(self) -> Dict[str, Any]:
        """增强健康检查"""
        try:
            start = time.time()
            result = self.execute_query("RETURN 1 as health", use_cache=False)
            latency = time.time() - start
            
            return {
                "status": "healthy",
                "latency_ms": round(latency * 1000, 2),
                "connected": self._connected,
                "cache_stats": self._cache.get_stats(),
                "query_stats": dict(self._query_stats)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "connected": False
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取查询统计"""
        with self._stats_lock:
            stats = dict(self._query_stats)
        
        total = stats["total_queries"] + stats["cached_queries"]
        avg_time = stats["total_time"] / max(stats["total_queries"], 1)
        
        return {
            **stats,
            "total_including_cache": total,
            "cache_hit_rate": round(stats["cached_queries"] / max(total, 1) * 100, 2),
            "avg_query_time_ms": round(avg_time * 1000, 2),
            "cache_stats": self._cache.get_stats()
        }


# 全局Neo4j客户端实例（延迟初始化）
_neo4j_client: Optional[Neo4jClient] = None
_neo4j_lock = threading.Lock()


def get_neo4j_client() -> Neo4jClient:
    """获取Neo4j客户端实例（单例模式，线程安全）"""
    global _neo4j_client
    if _neo4j_client is None:
        with _neo4j_lock:
            if _neo4j_client is None:
                _neo4j_client = Neo4jClient()
    return _neo4j_client


# 为了向后兼容
class Neo4jClientProxy:
    """Neo4j客户端代理"""
    def __getattr__(self, name):
        return getattr(get_neo4j_client(), name)


neo4j_client = Neo4jClientProxy()
