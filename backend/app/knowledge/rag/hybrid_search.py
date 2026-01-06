"""混合检索（向量检索 + 关键词匹配）- 增强版，支持多路召回"""
from typing import List, Dict, Any, Optional
from app.knowledge.rag.retriever import Retriever
from app.knowledge.rag.multi_retrieval import MultiRetrieval
from app.utils.logger import app_logger
import re


class HybridSearch:
    """混合检索器 - 支持多路召回和传统混合检索"""
    
    def __init__(self, use_advanced: bool = True):
        """
        初始化混合检索器
        
        Args:
            use_advanced: 是否使用高级多路召回（默认True）
        """
        self.use_advanced = use_advanced
        self.retriever = Retriever()
        self.multi_retrieval = MultiRetrieval() if use_advanced else None
    
    def extract_keywords(self, query: str) -> List[str]:
        """提取关键词"""
        # 简单的关键词提取（可以改进为更复杂的NLP方法）
        # 移除停用词和标点
        words = re.findall(r'\b\w+\b', query.lower())
        # 过滤短词
        keywords = [w for w in words if len(w) > 2]
        return keywords
    
    def keyword_match_score(self, text: str, keywords: List[str]) -> float:
        """计算关键词匹配分数"""
        text_lower = text.lower()
        matches = sum(1 for keyword in keywords if keyword in text_lower)
        return matches / len(keywords) if keywords else 0.0
    
    def hybrid_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """混合检索 - 优先使用多路召回"""
        # 如果启用高级模式，使用多路召回
        if self.use_advanced and self.multi_retrieval:
            try:
                results = self.multi_retrieval.retrieve(query, top_k=top_k)
                app_logger.info(f"多路召回完成，返回 {len(results)} 条结果")
                return results
            except Exception as e:
                app_logger.warning(f"多路召回失败，降级到传统混合检索: {e}")
        
        # 传统混合检索（向后兼容）
        # 向量检索
        vector_results = self.retriever.retrieve(query, top_k=top_k * 2)
        
        # 提取关键词
        keywords = self.extract_keywords(query)
        
        # 计算综合分数
        scored_results = []
        for result in vector_results:
            text = result.get("text", "")
            vector_score = 1.0 / (1.0 + result.get("score", 1.0))  # 转换为相似度分数
            keyword_score = self.keyword_match_score(text, keywords)
            
            # 综合分数（向量70%，关键词30%）
            combined_score = 0.7 * vector_score + 0.3 * keyword_score
            
            scored_results.append({
                **result,
                "combined_score": combined_score,
                "vector_score": vector_score,
                "keyword_score": keyword_score
            })
        
        # 按综合分数排序
        scored_results.sort(key=lambda x: x["combined_score"], reverse=True)
        
        # 返回top_k结果
        final_results = scored_results[:top_k]
        
        app_logger.info(f"混合检索完成，返回 {len(final_results)} 条结果")
        return final_results
    
    def rerank(self, query: str, results: List[Dict[str, Any]], top_k: int = None) -> List[Dict[str, Any]]:
        """重排序结果"""
        # 使用关键词匹配进行重排序
        keywords = self.extract_keywords(query)
        
        for result in results:
            text = result.get("text", "")
            keyword_score = self.keyword_match_score(text, keywords)
            original_score = result.get("combined_score", result.get("score", 0))
            
            # 提升关键词匹配高的结果
            result["rerank_score"] = original_score * 0.8 + keyword_score * 0.2
        
        # 按重排序分数排序
        results.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
        
        if top_k:
            return results[:top_k]
        return results

