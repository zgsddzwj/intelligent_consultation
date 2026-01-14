"""知识图谱检索器 - 从Neo4j检索相关实体和关系（优化版）"""
from typing import List, Dict, Any, Optional
from app.knowledge.graph.neo4j_client import get_neo4j_client
from app.knowledge.graph.queries import CypherQueries
from app.knowledge.ml.entity_recognizer import MedicalEntityRecognizer
from app.knowledge.ml.query_strategy import QueryStrategySelector
from app.knowledge.ml.relevance_scorer import RelevanceScorer
from app.utils.logger import app_logger
import re


class KnowledgeGraphRetriever:
    """知识图谱检索器（优化版）"""
    
    def __init__(self):
        self.queries = CypherQueries()
        self._client = None
        # 初始化优化组件
        self.entity_recognizer = MedicalEntityRecognizer()
        self.strategy_selector = QueryStrategySelector()
        self.relevance_scorer = RelevanceScorer()
    
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
    
    def extract_entities(self, query: str, use_kg_validation: bool = True) -> Dict[str, List[str]]:
        """
        从查询中提取实体（使用NER模型）
        
        Args:
            query: 查询文本
            use_kg_validation: 是否使用知识图谱验证实体
        
        Returns:
            实体字典
        """
        try:
            # 使用NER模型提取实体
            if use_kg_validation and self.client:
                entities = self.entity_recognizer.extract_with_kg_validation(query, self.client)
            else:
                entities = self.entity_recognizer.extract_entities(query)
            
            # 确保返回格式一致
            if "departments" not in entities:
                entities["departments"] = []
            
            return entities
            
        except Exception as e:
            app_logger.warning(f"实体提取失败，使用回退策略: {e}")
            # 回退到简单匹配
            return self._fallback_entity_extraction(query)
    
    def _fallback_entity_extraction(self, query: str) -> Dict[str, List[str]]:
        """回退的实体提取方法（保留原有逻辑作为备用）"""
        entities = {
            "diseases": [],
            "symptoms": [],
            "drugs": [],
            "examinations": [],
            "departments": []
        }
        
        if not self.client:
            return entities
        
        try:
            # 查询所有疾病名称（限制数量以提高性能）
            diseases_query = "MATCH (d:Disease) RETURN d.name as name LIMIT 1000"
            disease_results = self.client.execute_query(diseases_query)
            disease_names = [r["name"] for r in disease_results if r.get("name")]
            
            # 查询所有症状
            symptoms_query = "MATCH (s:Symptom) RETURN s.name as name LIMIT 1000"
            symptom_results = self.client.execute_query(symptoms_query)
            symptom_names = [r["name"] for r in symptom_results if r.get("name")]
            
            # 查询所有药物
            drugs_query = "MATCH (dr:Drug) RETURN dr.name as name LIMIT 500"
            drug_results = self.client.execute_query(drugs_query)
            drug_names = [r["name"] for r in drug_results if r.get("name")]
            
            # 查询所有检查
            exams_query = "MATCH (e:Examination) RETURN e.name as name LIMIT 500"
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
            app_logger.warning(f"回退实体提取失败: {e}")
        
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
        """
        从知识图谱检索相关信息（优化版）
        
        Args:
            query: 查询文本
            top_k: 返回前k个结果
        
        Returns:
            排序后的检索结果列表
        """
        if not self.client:
            return []
        
        try:
            # 1. 提取实体（使用NER模型）
            entities = self.extract_entities(query, use_kg_validation=True)
            
            # 2. 分类问题类型并选择查询策略
            query_analysis = self.strategy_selector.classify_question(query, entities)
            strategy = self.strategy_selector.get_query_strategy(query_analysis["strategy"])
            
            app_logger.info(f"查询分析: 类型={query_analysis['question_type_name']}, "
                          f"策略={strategy['description']}, 置信度={query_analysis['confidence']:.2f}")
            
            # 3. 根据策略执行查询
            all_results = self._execute_strategy_query(
                query, entities, strategy, query_analysis["question_type"]
            )
            
            # 4. 去重（基于文本）
            unique_results = self._deduplicate_results(all_results)
            
            # 5. 相关性评分和排序
            scored_results = self.relevance_scorer.score_and_sort(
                unique_results, query, entities, query_analysis["question_type"]
            )
            
            # 6. 返回top_k
            final_results = scored_results[:top_k]
            
            app_logger.info(f"知识图谱检索完成，查询: {query}, "
                          f"返回 {len(final_results)} 条结果（共检索 {len(all_results)} 条）")
            return final_results
            
        except Exception as e:
            app_logger.error(f"知识图谱检索失败: {e}")
            return []
    
    def _execute_strategy_query(self, 
                                query: str,
                                entities: Dict[str, List[str]],
                                strategy: Dict[str, Any],
                                question_type: str) -> List[Dict[str, Any]]:
        """根据策略执行查询"""
        all_results = []
        priority = strategy.get("priority", [])
        max_results = strategy.get("max_results", 10)
        depth = strategy.get("depth", 2)
        
        # 按照优先级顺序查询
        for entity_type in priority:
            entity_list = entities.get(entity_type, [])
            if not entity_list:
                continue
            
            # 限制每个类型的实体数量
            limit = max_results // len(priority) if priority else max_results
            for entity_name in entity_list[:limit]:
                if entity_type == "diseases":
                    results = self.retrieve_by_entity("Disease", entity_name, depth=depth)
                    all_results.extend(results)
                elif entity_type == "symptoms":
                    results = self.retrieve_by_entity("Symptom", entity_name, depth=depth)
                    all_results.extend(results)
                elif entity_type == "drugs":
                    results = self._retrieve_drug_info(entity_name, question_type)
                    all_results.extend(results)
                elif entity_type == "examinations":
                    results = self._retrieve_examination_info(entity_name)
                    all_results.extend(results)
            
        return all_results
    
    def _retrieve_drug_info(self, drug_name: str, question_type: str) -> List[Dict[str, Any]]:
        """检索药物信息"""
        results = []
        
        try:
            if question_type == "drug_interaction":
                # 查询药物相互作用
                interaction_query = """
                MATCH (d1:Drug {name: $drug_name})-[r:INTERACTS_WITH]-(d2:Drug)
                RETURN d2.name as interacting_drug, r.interaction_type as type,
                       r.severity as severity, r.description as description
                LIMIT 10
                """
                interactions = self.client.execute_query(interaction_query, {"drug_name": drug_name})
                
                if interactions:
                    interaction_list = "\n".join([
                        f"- {i['interacting_drug']}: {i.get('description', '')}"
                        for i in interactions
                    ])
                    results.append({
                        "text": f"药物：{drug_name}\n相互作用：\n{interaction_list}",
                        "source": "knowledge_graph",
                        "metadata": {
                            "entity_type": "Drug",
                            "entity_name": drug_name,
                            "interactions_count": len(interactions)
                        },
                        "score": 1.0,
                        "retrieval_method": "knowledge_graph"
                    })
            else:
                # 查询药物适用疾病
                drug_query = """
                MATCH (dr:Drug {name: $drug_name})
                OPTIONAL MATCH (d:Disease)-[:TREATED_BY]->(dr)
                RETURN dr.name as drug, collect(d.name) as diseases
                """
                drug_results = self.client.execute_query(drug_query, {"drug_name": drug_name})
                
                if drug_results:
                    drug_info = drug_results[0]
                    diseases = drug_info.get("diseases", [])
                    disease_list = ", ".join(diseases[:10]) if diseases else "无"
                    
                    results.append({
                        "text": f"药物：{drug_name}\n适用疾病：{disease_list}",
                        "source": "knowledge_graph",
                        "metadata": {
                            "entity_type": "Drug",
                            "entity_name": drug_name,
                            "diseases_count": len(diseases)
                        },
                        "score": 1.0,
                        "retrieval_method": "knowledge_graph"
                    })
        except Exception as e:
            app_logger.warning(f"药物信息检索失败: {e}")
        
        return results
    
    def _retrieve_examination_info(self, exam_name: str) -> List[Dict[str, Any]]:
        """检索检查信息"""
        results = []
        
        try:
            exam_query = """
            MATCH (e:Examination {name: $exam_name})
            OPTIONAL MATCH (d:Disease)-[:REQUIRES_EXAM]->(e)
            RETURN e.name as examination, collect(d.name) as diseases
            """
            exam_results = self.client.execute_query(exam_query, {"exam_name": exam_name})
            
            if exam_results:
                exam_info = exam_results[0]
                diseases = exam_info.get("diseases", [])
                disease_list = ", ".join(diseases[:10]) if diseases else "无"
                
                results.append({
                    "text": f"检查项目：{exam_name}\n适用疾病：{disease_list}",
                    "source": "knowledge_graph",
                    "metadata": {
                        "entity_type": "Examination",
                        "entity_name": exam_name,
                        "diseases_count": len(diseases)
                    },
                    "score": 1.0,
                    "retrieval_method": "knowledge_graph"
                })
        except Exception as e:
            app_logger.warning(f"检查信息检索失败: {e}")
        
        return results
    
    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去重结果"""
        seen_texts = set()
        unique_results = []
        
        for result in results:
            text = result.get("text", "")
            if text and text not in seen_texts:
                seen_texts.add(text)
                unique_results.append(result)
        
        return unique_results

