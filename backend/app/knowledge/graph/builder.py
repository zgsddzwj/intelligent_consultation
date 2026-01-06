"""知识图谱构建器"""
from typing import Dict, List, Any
from app.knowledge.graph.neo4j_client import neo4j_client
from app.knowledge.graph.queries import CypherQueries
from app.utils.logger import app_logger


class KnowledgeGraphBuilder:
    """知识图谱构建器"""
    
    def __init__(self):
        self.client = neo4j_client
        self.queries = CypherQueries()
    
    def create_entity(self, entity_type: str, name: str, properties: Dict[str, Any] = None):
        """创建实体节点"""
        properties = properties or {}
        properties["name"] = name
        
        props_str = ", ".join([f"{k}: ${k}" for k in properties.keys()])
        query = f"CREATE (e:{entity_type} {{{props_str}}}) RETURN e"
        
        try:
            result = self.client.execute_write(query, properties)
            app_logger.info(f"创建实体: {entity_type} - {name}")
            return result
        except Exception as e:
            app_logger.error(f"创建实体失败: {e}")
            raise
    
    def create_relationship(self, from_type: str, from_name: str,
                           rel_type: str, to_type: str, to_name: str,
                           properties: Dict[str, Any] = None):
        """创建关系"""
        query = self.queries.create_relationship(
            from_type, from_name, rel_type, to_type, to_name, properties
        )
        
        params = {
            "from_name": from_name,
            "to_name": to_name
        }
        if properties:
            params.update(properties)
        
        try:
            result = self.client.execute_write(query, params)
            app_logger.info(f"创建关系: {from_type}({from_name}) -[{rel_type}]-> {to_type}({to_name})")
            return result
        except Exception as e:
            app_logger.error(f"创建关系失败: {e}")
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

