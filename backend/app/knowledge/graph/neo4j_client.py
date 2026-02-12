"""Neo4j客户端"""
from neo4j import GraphDatabase
from typing import List, Dict, Any, Optional
from app.config import get_settings
from app.utils.logger import app_logger

settings = get_settings()


class Neo4jClient:
    """Neo4j客户端类"""
    
    def __init__(self):
        self.uri = settings.NEO4J_URI
        self.user = settings.NEO4J_USER
        self.password = settings.NEO4J_PASSWORD
        self.driver = None
        self._connected = False
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            # 测试连接
            self.driver.verify_connectivity()
            self._connected = True
            app_logger.info(f"已连接到Neo4j: {self.uri}")
        except Exception as e:
            app_logger.warning(f"Neo4j连接失败（将在首次使用时重试）: {e}")
            self._connected = False
    
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
    
    def execute_query(self, query: str, parameters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """执行Cypher查询"""
        # 如果未连接，尝试重新连接
        if not self._connected or not self.driver:
            try:
                if self.driver:
                    try:
                        self.driver.close()
                    except Exception:
                        pass
                self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
                self.driver.verify_connectivity()
                self._connected = True
                app_logger.info(f"Neo4j重新连接成功: {self.uri}")
            except Exception as e:
                app_logger.warning(f"Neo4j连接失败，返回空结果: {e}")
                raise  # 重新抛出异常，让调用方处理
        
        try:
            with self.driver.session() as session:
                result = session.run(query, parameters or {})
                return [record.data() for record in result]
        except Exception as e:
            # 连接可能已断开，标记为未连接
            self._connected = False
            app_logger.warning(f"Neo4j查询失败: {e}")
            raise
    
    def execute_write(self, query: str, parameters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """执行写操作"""
        # 如果未连接，尝试重新连接
        if not self._connected or not self.driver:
            try:
                if self.driver:
                    try:
                        self.driver.close()
                    except Exception:
                        pass
                self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
                self.driver.verify_connectivity()
                self._connected = True
                app_logger.info(f"Neo4j重新连接成功: {self.uri}")
            except Exception as e:
                app_logger.warning(f"Neo4j连接失败，无法执行写操作: {e}")
                raise  # 重新抛出异常，让调用方处理
        
        try:
            with self.driver.session() as session:
                # Neo4j 5.0+ 使用 execute_write
                # 在事务内部处理结果，避免事务关闭后访问结果
                def work(tx):
                    result = tx.run(query, parameters or {})
                    # 在事务内立即消费结果
                    return [record.data() for record in result]
                return session.execute_write(work)
        except Exception as e:
            # 连接可能已断开，标记为未连接
            self._connected = False
            app_logger.warning(f"Neo4j写操作失败: {e}")
            raise
    
    def create_indexes(self):
        """创建索引"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS FOR (d:Disease) ON (d.name)",
            "CREATE INDEX IF NOT EXISTS FOR (d:Disease) ON (d.icd10)",
            "CREATE INDEX IF NOT EXISTS FOR (s:Symptom) ON (s.name)",
            "CREATE INDEX IF NOT EXISTS FOR (dr:Drug) ON (dr.name)",
            "CREATE INDEX IF NOT EXISTS FOR (e:Examination) ON (e.name)",
        ]
        
        for index_query in indexes:
            try:
                self.execute_write(index_query)
                app_logger.info(f"索引创建成功: {index_query}")
            except Exception as e:
                app_logger.warning(f"索引创建失败: {e}")
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            result = self.execute_query("RETURN 1 as health")
            return len(result) > 0
        except Exception as e:
            app_logger.error(f"Neo4j健康检查失败: {e}")
            return False


import threading

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

