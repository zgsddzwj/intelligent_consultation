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
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        app_logger.info(f"已连接到Neo4j: {self.uri}")
    
    def close(self):
        """关闭连接"""
        self.driver.close()
    
    def execute_query(self, query: str, parameters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """执行Cypher查询"""
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]
    
    def execute_write(self, query: str, parameters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """执行写操作"""
        with self.driver.session() as session:
            result = session.write_transaction(lambda tx: tx.run(query, parameters or {}))
            return [record.data() for record in result]
    
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


# 全局Neo4j客户端实例
neo4j_client = Neo4jClient()

