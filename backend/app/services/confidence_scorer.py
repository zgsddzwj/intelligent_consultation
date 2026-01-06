"""置信度评分系统 - 基于RAG相关性计算回答置信度"""
from typing import Dict, List, Any, Optional
import numpy as np
from app.utils.logger import app_logger
from app.config import get_settings

settings = get_settings()


class ConfidenceScorer:
    """置信度评分系统"""
    
    def __init__(self):
        # 置信度阈值
        self.high_confidence_threshold = 0.8
        self.medium_confidence_threshold = 0.6
        self.low_confidence_threshold = 0.4
    
    def score(self, answer: str, rag_results: List[Dict[str, Any]] = None,
              kg_results: List[Dict[str, Any]] = None,
              context: str = "") -> Dict[str, Any]:
        """
        计算回答的置信度
        
        Args:
            answer: LLM生成的回答
            rag_results: RAG检索结果
            kg_results: 知识图谱查询结果
            context: 使用的上下文
        
        Returns:
            置信度评分结果
        """
        scores = {
            "overall_confidence": 0.0,
            "rag_confidence": 0.0,
            "kg_confidence": 0.0,
            "context_coverage": 0.0,
            "source_quality": 0.0,
            "confidence_level": "low",  # low, medium, high
            "factors": []
        }
        
        try:
            # 1. RAG相关性评分
            if rag_results:
                scores["rag_confidence"] = self._score_rag_relevance(rag_results)
                scores["factors"].append({
                    "factor": "rag_relevance",
                    "score": scores["rag_confidence"],
                    "weight": 0.4
                })
            
            # 2. 知识图谱相关性评分
            if kg_results:
                scores["kg_confidence"] = self._score_kg_relevance(kg_results)
                scores["factors"].append({
                    "factor": "kg_relevance",
                    "score": scores["kg_confidence"],
                    "weight": 0.3
                })
            
            # 3. 上下文覆盖率评分
            if context:
                scores["context_coverage"] = self._score_context_coverage(answer, context)
                scores["factors"].append({
                    "factor": "context_coverage",
                    "score": scores["context_coverage"],
                    "weight": 0.2
                })
            
            # 4. 来源质量评分
            scores["source_quality"] = self._score_source_quality(rag_results, kg_results)
            scores["factors"].append({
                "factor": "source_quality",
                "score": scores["source_quality"],
                "weight": 0.1
            })
            
            # 5. 计算综合置信度（加权平均）
            total_weight = sum(f["weight"] for f in scores["factors"])
            if total_weight > 0:
                scores["overall_confidence"] = sum(
                    f["score"] * f["weight"] for f in scores["factors"]
                ) / total_weight
            else:
                scores["overall_confidence"] = 0.5  # 默认中等置信度
            
            # 6. 确定置信度等级
            if scores["overall_confidence"] >= self.high_confidence_threshold:
                scores["confidence_level"] = "high"
            elif scores["overall_confidence"] >= self.medium_confidence_threshold:
                scores["confidence_level"] = "medium"
            else:
                scores["confidence_level"] = "low"
            
        except Exception as e:
            app_logger.error(f"置信度评分失败: {e}")
            scores["error"] = str(e)
            scores["overall_confidence"] = 0.5  # 出错时使用默认值
        
        return scores
    
    def _score_rag_relevance(self, rag_results: List[Dict[str, Any]]) -> float:
        """基于RAG检索结果计算相关性评分"""
        if not rag_results:
            return 0.0
        
        # 提取相关性分数
        scores = []
        for result in rag_results[:5]:  # 只考虑top 5
            score = result.get("score", 0.0)
            similarity = result.get("similarity", 0.0)
            relevance = result.get("relevance", 0.0)
            
            # 综合多个分数
            combined_score = max(score, similarity, relevance)
            scores.append(combined_score)
        
        # 计算平均分和最高分
        if scores:
            avg_score = np.mean(scores)
            max_score = max(scores)
            # 综合平均分和最高分（更重视最高分）
            return (avg_score * 0.4 + max_score * 0.6)
        
        return 0.0
    
    def _score_kg_relevance(self, kg_results: List[Dict[str, Any]]) -> float:
        """基于知识图谱查询结果计算相关性评分"""
        if not kg_results:
            return 0.0
        
        # 检查是否有匹配的实体和关系
        has_entities = any(result.get("entities") for result in kg_results)
        has_relationships = any(result.get("relationships") for result in kg_results)
        
        score = 0.0
        if has_entities:
            score += 0.5
        if has_relationships:
            score += 0.5
        
        return score
    
    def _score_context_coverage(self, answer: str, context: str) -> float:
        """计算回答对上下文的覆盖率"""
        if not context or not answer:
            return 0.0
        
        # 提取关键实体和概念（简化版）
        answer_keywords = set(self._extract_keywords(answer))
        context_keywords = set(self._extract_keywords(context))
        
        if not context_keywords:
            return 0.0
        
        # 计算交集比例
        overlap = len(answer_keywords & context_keywords)
        coverage = overlap / len(context_keywords) if context_keywords else 0.0
        
        # 限制在合理范围内
        return min(coverage, 1.0)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词（简化版）"""
        # 医疗相关关键词
        medical_keywords = [
            "疾病", "症状", "诊断", "治疗", "药物", "检查", "手术",
            "高血压", "糖尿病", "心脏病", "癌症", "感染", "炎症"
        ]
        
        keywords = []
        text_lower = text.lower()
        
        for keyword in medical_keywords:
            if keyword in text_lower:
                keywords.append(keyword)
        
        # 也可以使用jieba分词提取更多关键词
        try:
            import jieba
            words = jieba.cut(text)
            # 过滤掉停用词和单字
            keywords.extend([w for w in words if len(w) > 1 and w not in ["的", "是", "在", "有"]])
        except:
            pass
        
        return keywords[:20]  # 最多返回20个关键词
    
    def _score_source_quality(self, rag_results: List[Dict[str, Any]] = None,
                              kg_results: List[Dict[str, Any]] = None) -> float:
        """评估来源质量"""
        score = 0.0
        source_count = 0
        
        # RAG来源质量
        if rag_results:
            source_count += len(rag_results)
            # 检查来源的元数据质量
            for result in rag_results:
                source = result.get("source", {})
                if isinstance(source, dict):
                    # 检查是否有作者、日期等元数据
                    if source.get("author") or source.get("date"):
                        score += 0.1
                    # 检查来源类型（论文、指南等）
                    source_type = source.get("type", "")
                    if source_type in ["guideline", "paper", "textbook"]:
                        score += 0.1
        
        # KG来源质量
        if kg_results:
            source_count += len(kg_results)
            score += 0.2  # 知识图谱通常质量较高
        
        # 归一化
        if source_count > 0:
            score = min(score / max(source_count, 1), 1.0)
        
        return score
    
    def get_recommendation(self, confidence_score: Dict[str, Any]) -> str:
        """根据置信度获取建议"""
        level = confidence_score.get("confidence_level", "low")
        overall = confidence_score.get("overall_confidence", 0.0)
        
        if level == "high":
            return "基于提供的医疗信息，回答具有较高的可信度。"
        elif level == "medium":
            return "回答基于部分可用的医疗信息，建议结合其他资料或咨询专业医生。"
        else:
            return "⚠️ 回答的置信度较低，相关信息可能不完整或不准确。强烈建议咨询专业医生获取准确诊断和治疗建议。"


# 全局实例
confidence_scorer = ConfidenceScorer()

