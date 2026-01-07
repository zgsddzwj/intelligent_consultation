"""相关性评分器 - 对知识图谱结果进行排序"""
from typing import List, Dict, Any, Optional
from app.utils.logger import app_logger
import math


class RelevanceScorer:
    """相关性评分器"""
    
    def __init__(self):
        # 权重配置
        self.weights = {
            "entity_match": 0.4,      # 实体匹配度
            "query_similarity": 0.3,   # 查询相似度
            "relationship_strength": 0.2,  # 关系强度
            "result_completeness": 0.1  # 结果完整性
        }
    
    def score_and_sort(self, 
                      results: List[Dict[str, Any]], 
                      query: str,
                      entities: Dict[str, List[str]],
                      question_type: str = "general") -> List[Dict[str, Any]]:
        """
        对结果进行评分和排序
        
        Args:
            results: 检索结果列表
            query: 原始查询
            entities: 提取的实体
            question_type: 问题类型
        
        Returns:
            排序后的结果列表
        """
        if not results:
            return []
        
        # 计算每个结果的得分
        scored_results = []
        for result in results:
            score = self._calculate_relevance_score(result, query, entities, question_type)
            result["relevance_score"] = score
            scored_results.append(result)
        
        # 按得分排序
        scored_results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        app_logger.debug(f"相关性评分完成，共 {len(scored_results)} 条结果")
        return scored_results
    
    def _calculate_relevance_score(self, 
                                   result: Dict[str, Any],
                                   query: str,
                                   entities: Dict[str, List[str]],
                                   question_type: str) -> float:
        """计算单个结果的相关性得分"""
        score = 0.0
        
        # 1. 实体匹配度
        entity_score = self._calculate_entity_match(result, entities)
        score += entity_score * self.weights["entity_match"]
        
        # 2. 查询相似度
        similarity_score = self._calculate_query_similarity(result, query)
        score += similarity_score * self.weights["query_similarity"]
        
        # 3. 关系强度
        relationship_score = self._calculate_relationship_strength(result, question_type)
        score += relationship_score * self.weights["relationship_strength"]
        
        # 4. 结果完整性
        completeness_score = self._calculate_completeness(result)
        score += completeness_score * self.weights["result_completeness"]
        
        return min(score, 1.0)  # 限制在[0, 1]范围内
    
    def _calculate_entity_match(self, result: Dict[str, Any], entities: Dict[str, List[str]]) -> float:
        """计算实体匹配度"""
        score = 0.0
        total_entities = sum(len(v) for v in entities.values())
        
        if total_entities == 0:
            return 0.5  # 没有实体时给中等分数
        
        # 检查结果中的实体
        result_text = result.get("text", "").lower()
        metadata = result.get("metadata", {})
        
        matched_count = 0
        
        # 检查疾病匹配
        for disease in entities.get("diseases", []):
            if disease.lower() in result_text or metadata.get("entity_name") == disease:
                matched_count += 1
        
        # 检查症状匹配
        for symptom in entities.get("symptoms", []):
            if symptom.lower() in result_text or metadata.get("entity_name") == symptom:
                matched_count += 1
        
        # 检查药物匹配
        for drug in entities.get("drugs", []):
            if drug.lower() in result_text or metadata.get("entity_name") == drug:
                matched_count += 1
        
        # 检查检查项目匹配
        for exam in entities.get("examinations", []):
            if exam.lower() in result_text or metadata.get("entity_name") == exam:
                matched_count += 1
        
        if total_entities > 0:
            score = matched_count / total_entities
        
        return score
    
    def _calculate_query_similarity(self, result: Dict[str, Any], query: str) -> float:
        """计算查询相似度（简化版，使用关键词重叠）"""
        query_words = set(query.lower().split())
        result_text = result.get("text", "").lower()
        result_words = set(result_text.split())
        
        if not query_words or not result_words:
            return 0.0
        
        # 计算Jaccard相似度
        intersection = query_words & result_words
        union = query_words | result_words
        
        if not union:
            return 0.0
        
        jaccard = len(intersection) / len(union)
        
        # 考虑文本长度（避免过短文本得分过高）
        length_penalty = min(len(result_text) / 100, 1.0)
        
        return jaccard * length_penalty
    
    def _calculate_relationship_strength(self, result: Dict[str, Any], question_type: str) -> float:
        """计算关系强度"""
        metadata = result.get("metadata", {})
        
        # 根据问题类型调整权重
        type_weights = {
            "disease_info": {"symptoms_count": 0.3, "drugs_count": 0.3, "exams_count": 0.2},
            "symptom_diagnosis": {"diseases_count": 0.5, "exams_count": 0.3},
            "drug_info": {"diseases_count": 0.5},
            "treatment_plan": {"symptoms_count": 0.2, "drugs_count": 0.4, "exams_count": 0.2}
        }
        
        weights = type_weights.get(question_type, {
            "symptoms_count": 0.25,
            "drugs_count": 0.25,
            "exams_count": 0.25,
            "diseases_count": 0.25
        })
        
        score = 0.0
        
        # 根据关联实体数量计算得分
        for key, weight in weights.items():
            count = metadata.get(key, 0)
            # 使用对数函数避免数量过多时得分过高
            normalized_count = min(math.log(count + 1) / math.log(10), 1.0)
            score += normalized_count * weight
        
        return min(score, 1.0)
    
    def _calculate_completeness(self, result: Dict[str, Any]) -> float:
        """计算结果完整性"""
        metadata = result.get("metadata", {})
        text = result.get("text", "")
        
        score = 0.0
        
        # 检查是否有基本信息
        if text and len(text) > 20:
            score += 0.3
        
        # 检查是否有元数据
        if metadata:
            score += 0.2
        
        # 检查是否有多个关联实体
        entity_counts = [
            metadata.get("symptoms_count", 0),
            metadata.get("drugs_count", 0),
            metadata.get("exams_count", 0),
            metadata.get("diseases_count", 0)
        ]
        
        non_zero_counts = sum(1 for count in entity_counts if count > 0)
        if non_zero_counts >= 2:
            score += 0.3
        elif non_zero_counts == 1:
            score += 0.2
        
        # 检查是否有来源信息
        if result.get("source"):
            score += 0.2
        
        return min(score, 1.0)
    
    def rerank_with_llm(self, 
                       results: List[Dict[str, Any]], 
                       query: str,
                       top_k: int = 5) -> List[Dict[str, Any]]:
        """
        使用LLM对结果进行重排序（可选的高级功能）
        
        Args:
            results: 检索结果列表
            query: 原始查询
            top_k: 返回前k个结果
        
        Returns:
            重排序后的结果列表
        """
        if len(results) <= top_k:
            return results
        
        # 简化实现：使用相关性得分排序
        # 完整实现可以使用LLM对结果进行语义重排序
        scored_results = self.score_and_sort(results, query, {}, "general")
        return scored_results[:top_k]
