"""高级RAG系统 - 整合多路召回、Rerank、ML算法"""
from typing import List, Dict, Any, Optional
from app.knowledge.rag.multi_retrieval import MultiRetrieval
from app.knowledge.rag.reranker import Reranker
from app.knowledge.rag.ml_reranker import MLReranker
from app.knowledge.ml.intent_classifier import IntentClassifier
from app.knowledge.ml.relevance_scorer import RelevanceScorer
from app.knowledge.ml.query_understanding import QueryUnderstanding
from app.knowledge.ml.ranking_optimizer import RankingOptimizer
from app.utils.logger import app_logger


class AdvancedRAG:
    """高级RAG系统 - 整合所有组件"""
    
    def __init__(self,
                 enable_multi_retrieval: bool = True,
                 enable_rerank: bool = True,
                 enable_ml_rerank: bool = True,
                 enable_intent_classification: bool = True,
                 enable_relevance_scoring: bool = True,
                 enable_query_understanding: bool = True,
                 enable_ranking_optimization: bool = True):
        """
        初始化高级RAG系统
        
        Args:
            enable_multi_retrieval: 是否启用多路召回
            enable_rerank: 是否启用BGE-Reranker
            enable_ml_rerank: 是否启用ML重排序
            enable_intent_classification: 是否启用意图分类
            enable_relevance_scoring: 是否启用相关性评分
            enable_query_understanding: 是否启用查询理解
            enable_ranking_optimization: 是否启用排序优化
        """
        # 多路召回
        self.multi_retrieval = MultiRetrieval() if enable_multi_retrieval else None
        
        # Rerank
        self.reranker = Reranker() if enable_rerank else None
        self.ml_reranker = MLReranker() if enable_ml_rerank else None
        
        # ML算法
        self.intent_classifier = IntentClassifier() if enable_intent_classification else None
        self.relevance_scorer = RelevanceScorer() if enable_relevance_scoring else None
        self.query_understanding = QueryUnderstanding() if enable_query_understanding else None
        self.ranking_optimizer = RankingOptimizer() if enable_ranking_optimization else None
        
        app_logger.info("高级RAG系统初始化完成")
    
    def retrieve(self, query: str, top_k: int = 10,
                 use_multi_retrieval: bool = True,
                 use_rerank: bool = True,
                 use_ml_rerank: bool = True,
                 use_ranking_optimization: bool = True) -> Dict[str, Any]:
        """
        高级检索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            use_multi_retrieval: 是否使用多路召回
            use_rerank: 是否使用Rerank
            use_ml_rerank: 是否使用ML重排序
            use_ranking_optimization: 是否使用排序优化
        
        Returns:
            检索结果字典
        """
        result = {
            "query": query,
            "intent": None,
            "query_analysis": None,
            "documents": [],
            "stats": {}
        }
        
        # 1. 查询理解
        if self.query_understanding:
            try:
                query_analysis = self.query_understanding.understand(query)
                result["query_analysis"] = query_analysis
                app_logger.info(f"查询理解完成: {query_analysis.get('main_keywords', [])}")
            except Exception as e:
                app_logger.warning(f"查询理解失败: {e}")
        
        # 2. 意图分类
        if self.intent_classifier:
            try:
                intent_result = self.intent_classifier.classify(query)
                result["intent"] = intent_result
                app_logger.info(f"意图分类: {intent_result.get('intent_name')}")
            except Exception as e:
                app_logger.warning(f"意图分类失败: {e}")
        
        # 3. 多路召回
        documents = []
        if use_multi_retrieval and self.multi_retrieval:
            try:
                documents = self.multi_retrieval.retrieve(query, top_k=top_k * 2)
                result["stats"]["multi_retrieval"] = len(documents)
                app_logger.info(f"多路召回完成，返回 {len(documents)} 条结果")
            except Exception as e:
                app_logger.warning(f"多路召回失败: {e}")
        
        if not documents:
            app_logger.warning("未检索到文档，返回空结果")
            return result
        
        # 4. 相关性评分
        if self.relevance_scorer:
            try:
                documents = self.relevance_scorer.score_batch(query, documents)
                result["stats"]["relevance_scoring"] = "completed"
                app_logger.info("相关性评分完成")
            except Exception as e:
                app_logger.warning(f"相关性评分失败: {e}")
        
        # 5. BGE-Rerank
        if use_rerank and self.reranker:
            try:
                documents = self.reranker.rerank(query, documents, top_k=top_k * 2)
                result["stats"]["rerank"] = "completed"
                app_logger.info("BGE-Rerank完成")
            except Exception as e:
                app_logger.warning(f"BGE-Rerank失败: {e}")
        
        # 6. ML重排序
        if use_ml_rerank and self.ml_reranker:
            try:
                documents = self.ml_reranker.rerank(query, documents, top_k=top_k * 2)
                result["stats"]["ml_rerank"] = "completed"
                app_logger.info("ML重排序完成")
            except Exception as e:
                app_logger.warning(f"ML重排序失败: {e}")
        
        # 7. 排序优化
        if use_ranking_optimization and self.ranking_optimizer:
            try:
                documents = self.ranking_optimizer.optimize_ranking(query, documents)
                result["stats"]["ranking_optimization"] = "completed"
                app_logger.info("排序优化完成")
            except Exception as e:
                app_logger.warning(f"排序优化失败: {e}")
        
        # 8. 最终排序（综合所有分数）
        documents = self._final_ranking(documents)
        
        # 返回top_k
        result["documents"] = documents[:top_k]
        result["stats"]["total_documents"] = len(result["documents"])
        
        app_logger.info(f"高级RAG检索完成，查询: {query}, 最终返回 {len(result['documents'])} 条结果")
        
        return result
    
    def _final_ranking(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """最终排序 - 综合所有分数"""
        for doc in documents:
            # 收集所有分数
            scores = []
            
            # 相关性分数
            if "relevance_score" in doc:
                scores.append(doc["relevance_score"] * 0.3)
            
            # Rerank分数
            if "bge_score" in doc:
                scores.append(doc["bge_score"] * 0.3)
            
            # ML分数
            if "ml_score" in doc:
                scores.append(doc["ml_score"] * 0.2)
            
            # 排序优化分数
            if "optimized_score" in doc:
                scores.append(doc["optimized_score"] * 0.2)
            
            # 原始分数
            if "rrf_score" in doc:
                scores.append(doc["rrf_score"] * 0.1)
            elif "combined_score" in doc:
                scores.append(doc["combined_score"] * 0.1)
            
            # 计算最终分数
            if scores:
                doc["final_score"] = sum(scores)
            else:
                doc["final_score"] = 0.0
        
        # 按最终分数排序
        documents.sort(key=lambda x: x.get("final_score", 0.0), reverse=True)
        
        return documents
    
    def format_context(self, result: Dict[str, Any]) -> str:
        """格式化检索结果为上下文"""
        documents = result.get("documents", [])
        
        context_parts = []
        
        # 添加意图信息
        if result.get("intent"):
            intent = result["intent"]
            context_parts.append(f"[查询意图: {intent.get('intent_name')}]")
        
        # 添加文档内容
        for i, doc in enumerate(documents, 1):
            source = doc.get("source", "未知来源")
            text = doc.get("text", "")
            metadata = doc.get("metadata", {})
            
            # 构建来源标注
            citation = f"[来源{i}: {source}"
            if metadata.get("page"):
                citation += f", 页码: {metadata['page']}"
            if metadata.get("section"):
                citation += f", 章节: {metadata['section']}"
            citation += f", 相关性: {doc.get('final_score', 0.0):.2f}]"
            
            context_parts.append(f"{citation}\n{text}")
        
        return "\n\n".join(context_parts)
    
    def get_retrieval_stats(self, query: str) -> Dict[str, Any]:
        """获取检索统计信息"""
        stats = {
            "query": query,
            "multi_retrieval": None,
            "intent": None,
            "query_analysis": None
        }
        
        # 多路召回统计
        if self.multi_retrieval:
            try:
                stats["multi_retrieval"] = self.multi_retrieval.get_retrieval_stats(query)
            except Exception as e:
                app_logger.warning(f"获取多路召回统计失败: {e}")
        
        # 意图分类
        if self.intent_classifier:
            try:
                stats["intent"] = self.intent_classifier.classify(query)
            except Exception as e:
                app_logger.warning(f"意图分类失败: {e}")
        
        # 查询理解
        if self.query_understanding:
            try:
                stats["query_analysis"] = self.query_understanding.understand(query)
            except Exception as e:
                app_logger.warning(f"查询理解失败: {e}")
        
        return stats

