"""知识图谱检索器 - 从Neo4j检索相关实体和关系"""
from typing import List, Dict, Any, Optional
from app.knowledge.graph.neo4j_client import get_neo4j_client
from app.knowledge.graph.queries import CypherQueries
from app.utils.logger import app_logger
import re


class KnowledgeGraphRetriever:
    """知识图谱检索器"""
    
    def __init__(self):
        self.queries = CypherQueries()
        self._client = None
    
    @property
    def client(self):
        """延迟获取Neo4j客户端"""
        if self._client is None:
            try:
                self._client = get_neo4j_client()
            except Exception as e:
                app_logger.warning(f"Neo4j客户端获取失败: {e}")
                return None
        return self._client
    
    def extract_entities(self, query: str) -> Dict[str, List[str]]:
        """从查询中提取实体（疾病、症状、药物等）"""
        entities = {
            "diseases": [],
            "symptoms": [],
            "drugs": [],
            "examinations": []
        }
        
        if not self.client:
            return entities
        
        try:
            # 简单的实体识别（可以改进为NER模型）
            # 查询所有疾病名称
            diseases_query = "MATCH (d:Disease) RETURN d.name as name"
            disease_results = self.client.execute_query(diseases_query)
            disease_names = [r["name"] for r in disease_results if r.get("name")]
            
            # 查询所有症状
            symptoms_query = "MATCH (s:Symptom) RETURN s.name as name"
            symptom_results = self.client.execute_query(symptoms_query)
            symptom_names = [r["name"] for r in symptom_results if r.get("name")]
            
            # 查询所有药物
            drugs_query = "MATCH (dr:Drug) RETURN dr.name as name"
            drug_results = self.client.execute_query(drugs_query)
            drug_names = [r["name"] for r in drug_results if r.get("name")]
            
            # 查询所有检查
            exams_query = "MATCH (e:Examination) RETURN e.name as name"
            exam_results = self.client.execute_query(exams_query)
            exam_names = [r["name"] for r in exam_results if r.get("name")]
            
            # 在查询中匹配实体
            query_lower = query.lower()
            for name in disease_names:
                if name in query or name.lower() in query_lower:
                    entities["diseases"].append(name)
            
            for name in symptom_names:
                if name in query or name.lower() in query_lower:
                    entities["symptoms"].append(name)
            
            for name in drug_names:
                if name in query or name.lower() in query_lower:
                    entities["drugs"].append(name)
            
            for name in exam_names:
                if name in query or name.lower() in query_lower:
                    entities["examinations"].append(name)
            
        except Exception as e:
            app_logger.warning(f"实体提取失败: {e}")
        
        return entities
    
    def retrieve_by_entity(self, entity_type: str, entity_name: str, depth: int = 2) -> List[Dict[str, Any]]:
        """根据实体检索相关信息"""
        if not self.client:
            return []
        
        try:
            results = []
            
            if entity_type == "Disease":
                # 查询疾病相关信息
                disease_info = self.queries.find_disease_by_name(entity_name)
                disease_result = self.client.execute_query(disease_info, {"name": entity_name})
                
                if disease_result:
                    # 查询症状
                    symptoms_query = self.queries.find_disease_symptoms(entity_name)
                    symptoms = self.client.execute_query(symptoms_query, {"disease_name": entity_name})
                    
                    # 查询药物
                    drugs_query = self.queries.find_disease_drugs(entity_name)
                    drugs = self.client.execute_query(drugs_query, {"disease_name": entity_name})
                    
                    # 查询检查
                    exams_query = self.queries.find_disease_examinations(entity_name)
                    exams = self.client.execute_query(exams_query, {"disease_name": entity_name})
                    
                    # 构建文本结果
                    text_parts = [f"疾病：{entity_name}"]
                    if symptoms:
                        symptom_list = ", ".join([s["symptom"] for s in symptoms])
                        text_parts.append(f"症状：{symptom_list}")
                    if drugs:
                        drug_list = ", ".join([d["drug"] for d in drugs])
                        text_parts.append(f"治疗药物：{drug_list}")
                    if exams:
                        exam_list = ", ".join([e["examination"] for e in exams])
                        text_parts.append(f"检查项目：{exam_list}")
                    
                    results.append({
                        "text": "\n".join(text_parts),
                        "source": "knowledge_graph",
                        "metadata": {
                            "entity_type": "Disease",
                            "entity_name": entity_name,
                            "symptoms_count": len(symptoms),
                            "drugs_count": len(drugs),
                            "exams_count": len(exams)
                        },
                        "score": 1.0,
                        "retrieval_method": "knowledge_graph"
                    })
            
            elif entity_type == "Symptom":
                # 根据症状查找疾病
                symptom_query = f"""
                MATCH (d:Disease)-[:HAS_SYMPTOM]->(s:Symptom {{name: $symptom_name}})
                RETURN d.name as disease, d.icd10 as icd10
                LIMIT 10
                """
                diseases = self.client.execute_query(symptom_query, {"symptom_name": entity_name})
                
                if diseases:
                    disease_list = ", ".join([d["disease"] for d in diseases])
                    results.append({
                        "text": f"症状：{entity_name}\n可能相关疾病：{disease_list}",
                        "source": "knowledge_graph",
                        "metadata": {
                            "entity_type": "Symptom",
                            "entity_name": entity_name,
                            "diseases_count": len(diseases)
                        },
                        "score": 1.0,
                        "retrieval_method": "knowledge_graph"
                    })
            
            return results
            
        except Exception as e:
            app_logger.error(f"实体检索失败: {e}")
            return []
    
    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """从知识图谱检索相关信息"""
        if not self.client:
            return []
        
        try:
            # 提取实体
            entities = self.extract_entities(query)
            
            all_results = []
            
            # 根据疾病检索
            for disease in entities["diseases"][:3]:  # 限制数量
                results = self.retrieve_by_entity("Disease", disease)
                all_results.extend(results)
            
            # 根据症状检索
            for symptom in entities["symptoms"][:3]:
                results = self.retrieve_by_entity("Symptom", symptom)
                all_results.extend(results)
            
            # 根据药物检索
            for drug in entities["drugs"][:2]:
                drug_query = f"""
                MATCH (dr:Drug {{name: $drug_name}})
                OPTIONAL MATCH (d:Disease)-[:TREATED_BY]->(dr)
                RETURN dr.name as drug, collect(d.name) as diseases
                """
                drug_results = self.client.execute_query(drug_query, {"drug_name": drug})
                
                if drug_results:
                    drug_info = drug_results[0]
                    diseases = drug_info.get("diseases", [])
                    disease_list = ", ".join(diseases) if diseases else "无"
                    
                    all_results.append({
                        "text": f"药物：{drug}\n适用疾病：{disease_list}",
                        "source": "knowledge_graph",
                        "metadata": {
                            "entity_type": "Drug",
                            "entity_name": drug
                        },
                        "score": 1.0,
                        "retrieval_method": "knowledge_graph"
                    })
            
            # 去重（基于文本）
            seen_texts = set()
            unique_results = []
            for result in all_results:
                text = result["text"]
                if text not in seen_texts:
                    seen_texts.add(text)
                    unique_results.append(result)
            
            # 返回top_k
            final_results = unique_results[:top_k]
            
            app_logger.info(f"知识图谱检索完成，查询: {query}, 返回 {len(final_results)} 条结果")
            return final_results
            
        except Exception as e:
            app_logger.error(f"知识图谱检索失败: {e}")
            return []

