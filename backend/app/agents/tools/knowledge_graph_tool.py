"""知识图谱工具"""
from typing import Dict, Any, List
from app.knowledge.graph.neo4j_client import neo4j_client
from app.knowledge.graph.queries import CypherQueries
from app.utils.logger import app_logger


class KnowledgeGraphTool:
    """知识图谱查询工具"""
    
    def __init__(self):
        self.name = "knowledge_graph_query"
        self.description = "查询医疗知识图谱，获取疾病、症状、药物等实体关系"
        self.client = neo4j_client
        self.queries = CypherQueries()
    
    def execute(self, operation: str, **kwargs) -> Dict[str, Any]:
        """执行知识图谱查询"""
        try:
            if operation == "get_disease_info":
                return self.get_disease_info(kwargs.get("disease_name"))
            elif operation == "get_drug_info":
                return self.get_drug_info(kwargs.get("drug_name"))
            elif operation == "get_drug_interactions":
                return self.get_drug_interactions(kwargs.get("drug_name"))
            elif operation == "find_diseases_by_symptoms":
                return self.find_diseases_by_symptoms(kwargs.get("symptoms", []))
            else:
                raise ValueError(f"不支持的操作: {operation}")
        except Exception as e:
            app_logger.error(f"知识图谱查询失败: {e}")
            return {"error": str(e), "operation": operation}
    
    def get_disease_info(self, disease_name: str) -> Dict[str, Any]:
        """获取疾病信息"""
        query = self.queries.find_disease_by_name(disease_name)
        result = self.client.execute_query(query, {"name": disease_name})
        
        if not result:
            return {"disease": None, "found": False}
        
        disease = result[0].get("d")
        
        # 获取相关症状、药物、检查
        symptoms = self.client.execute_query(
            self.queries.find_disease_symptoms(disease_name),
            {"disease_name": disease_name}
        )
        drugs = self.client.execute_query(
            self.queries.find_disease_drugs(disease_name),
            {"disease_name": disease_name}
        )
        examinations = self.client.execute_query(
            self.queries.find_disease_examinations(disease_name),
            {"disease_name": disease_name}
        )
        
        return {
            "disease": dict(disease) if disease else None,
            "symptoms": symptoms,
            "drugs": drugs,
            "examinations": examinations,
            "found": True
        }
    
    def get_drug_info(self, drug_name: str) -> Dict[str, Any]:
        """获取药物信息"""
        query = "MATCH (d:Drug {name: $drug_name}) RETURN d"
        result = self.client.execute_query(query, {"drug_name": drug_name})
        
        if not result:
            return {"drug": None, "found": False}
        
        drug = result[0].get("d")
        
        # 获取禁忌和相互作用
        contraindications = self.client.execute_query(
            self.queries.find_drug_contraindications(drug_name),
            {"drug_name": drug_name}
        )
        interactions = self.client.execute_query(
            self.queries.find_drug_interactions(drug_name),
            {"drug_name": drug_name}
        )
        
        return {
            "drug": dict(drug) if drug else None,
            "contraindications": contraindications,
            "interactions": interactions,
            "found": True
        }
    
    def get_drug_interactions(self, drug_name: str) -> Dict[str, Any]:
        """获取药物相互作用"""
        result = self.client.execute_query(
            self.queries.find_drug_interactions(drug_name),
            {"drug_name": drug_name}
        )
        return {
            "drug": drug_name,
            "interactions": result
        }
    
    def find_diseases_by_symptoms(self, symptoms: List[str]) -> Dict[str, Any]:
        """根据症状查找疾病"""
        if not symptoms:
            return {"diseases": [], "count": 0}
        
        result = self.client.execute_query(
            self.queries.find_diseases_by_symptoms(symptoms),
            {}
        )
        return {
            "symptoms": symptoms,
            "diseases": result,
            "count": len(result)
        }
    
    def format_disease_info(self, info: Dict[str, Any]) -> str:
        """格式化疾病信息为文本"""
        if not info.get("found"):
            return f"未找到疾病信息。"
        
        disease = info.get("disease", {})
        text = f"疾病: {disease.get('name', '未知')}\n"
        if disease.get("icd10"):
            text += f"ICD-10编码: {disease['icd10']}\n"
        if disease.get("description"):
            text += f"描述: {disease['description']}\n"
        
        if info.get("symptoms"):
            text += "\n相关症状:\n"
            for symptom in info["symptoms"]:
                text += f"- {symptom.get('symptom', '')}\n"
        
        if info.get("drugs"):
            text += "\n治疗药物:\n"
            for drug in info["drugs"]:
                text += f"- {drug.get('drug', '')} ({drug.get('generic_name', '')})\n"
        
        if info.get("examinations"):
            text += "\n相关检查:\n"
            for exam in info["examinations"]:
                text += f"- {exam.get('examination', '')}\n"
        
        return text

