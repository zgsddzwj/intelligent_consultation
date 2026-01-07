"""知识图谱构建器"""
from typing import Dict, List, Any
from app.knowledge.graph.neo4j_client import get_neo4j_client
from app.knowledge.graph.queries import CypherQueries
from app.utils.logger import app_logger


class KnowledgeGraphBuilder:
    """知识图谱构建器"""
    
    def __init__(self):
        self._client = None
        self.queries = CypherQueries()
    
    @property
    def client(self):
        """延迟获取Neo4j客户端"""
        if self._client is None:
            self._client = get_neo4j_client()
        return self._client
    
    def create_entity(self, entity_type: str, name: str, properties: Dict[str, Any] = None, merge: bool = False):
        """创建实体节点"""
        properties = properties or {}
        properties["name"] = name
        
        props_str = ", ".join([f"{k}: ${k}" for k in properties.keys()])
        set_str = ", ".join([f"e.{k} = ${k}" for k in properties.keys() if k != "name"])
        
        if merge:
            # 使用MERGE避免重复创建
            if set_str:
                query = f"MERGE (e:{entity_type} {{name: $name}}) SET {set_str} RETURN e"
            else:
                query = f"MERGE (e:{entity_type} {{name: $name}}) RETURN e"
        else:
            query = f"CREATE (e:{entity_type} {{{props_str}}}) RETURN e"
        
        try:
            result = self.client.execute_write(query, properties)
            # 减少日志输出，只在debug模式下记录
            # if not merge:
            #     app_logger.debug(f"创建实体: {entity_type} - {name}")
            return result
        except Exception as e:
            app_logger.warning(f"创建实体失败 {entity_type}:{name}: {str(e)[:100]}")
            raise
    
    def create_relationship(self, from_type: str, from_name: str,
                           rel_type: str, to_type: str, to_name: str,
                           properties: Dict[str, Any] = None, merge: bool = True):
        """创建关系（默认使用MERGE避免重复）"""
        query = self.queries.create_relationship(
            from_type, from_name, rel_type, to_type, to_name, properties, merge=merge
        )
        
        params = {
            "from_name": from_name,
            "to_name": to_name
        }
        if properties:
            params.update(properties)
        
        try:
            result = self.client.execute_write(query, params)
            # 减少日志输出，只在debug模式下记录
            # app_logger.debug(f"创建关系: {from_type}({from_name}) -[{rel_type}]-> {to_type}({to_name})")
            return result
        except Exception as e:
            app_logger.warning(f"创建关系失败: {from_type}({from_name})-[{rel_type}]->{to_type}({to_name}): {str(e)[:100]}")
            raise
    
    def query_disease_info(self, disease_name: str) -> Dict:
        """查询疾病完整信息"""
        result = {
            "disease": None,
            "symptoms": [],
            "drugs": [],
            "examinations": []
        }
        
        # 查询疾病基本信息
        disease_query = self.queries.find_disease_by_name(disease_name)
        disease_result = self.client.execute_query(disease_query, {"name": disease_name})
        if disease_result:
            result["disease"] = disease_result[0].get("d")
        
        # 查询症状
        symptoms_query = self.queries.find_disease_symptoms(disease_name)
        result["symptoms"] = self.client.execute_query(symptoms_query, {"disease_name": disease_name})
        
        # 查询药物
        drugs_query = self.queries.find_disease_drugs(disease_name)
        result["drugs"] = self.client.execute_query(drugs_query, {"disease_name": disease_name})
        
        # 查询检查
        exams_query = self.queries.find_disease_examinations(disease_name)
        result["examinations"] = self.client.execute_query(exams_query, {"disease_name": disease_name})
        
        return result
    
    def initialize_schema(self):
        """初始化图谱模式（创建索引）"""
        self.client.create_indexes()
        app_logger.info("知识图谱模式初始化完成")

