"""多路召回融合器 - 整合向量、BM25、语义、图谱检索"""
from typing import List, Dict, Any, Optional
from app.knowledge.rag.retriever import Retriever
from app.knowledge.rag.bm25_retriever import BM25Retriever
from app.knowledge.rag.semantic_retriever import SemanticRetriever
from app.knowledge.rag.kg_retriever import KnowledgeGraphRetriever
from app.services.milvus_service import get_milvus_service
from app.utils.logger import app_logger
from collections import defaultdict


class MultiRetrieval:
    """多路召回融合器 - 使用Reciprocal Rank Fusion (RRF)融合多路结果"""
    
    def __init__(self, 
                 vector_weight: float = 0.4,
                 bm25_weight: float = 0.3,
                 semantic_weight: float = 0.2,
                 kg_weight: float = 0.1):
        """
        初始化多路召回器
        
        Args:
            vector_weight: 向量检索权重
            bm25_weight: BM25检索权重
            semantic_weight: 语义检索权重
            kg_weight: 知识图谱检索权重
        """
        self.vector_retriever = Retriever()
        self.bm25_retriever = BM25Retriever()
        self.semantic_retriever = SemanticRetriever()
        self.kg_retriever = KnowledgeGraphRetriever()
        
        # 权重配置
        self.weights = {
            "vector": vector_weight,
            "bm25": bm25_weight,
            "semantic": semantic_weight,
            "kg": kg_weight
        }
        
        # 归一化权重
        total_weight = sum(self.weights.values())
        if total_weight > 0:
            self.weights = {k: v / total_weight for k, v in self.weights.items()}
    
    def _reciprocal_rank_fusion(self, 
                                results_list: List[List[Dict[str, Any]]],
                                weights: List[float],
                                k: int = 60) -> List[Dict[str, Any]]:
        """
        Reciprocal Rank Fusion (RRF)算法
        
        Args:
            results_list: 多路检索结果列表
            weights: 每路结果的权重
            k: RRF参数，通常为60
        """
        # 使用文本作为唯一标识
        doc_scores = defaultdict(float)
        doc_data = {}
        
        for results, weight in zip(results_list, weights):
            for rank, result in enumerate(results, start=1):
                # 使用文本作为唯一标识
                text = result.get("text", "")
                if not text:
                    continue
                
                # RRF分数
                rrf_score = weight / (k + rank)
                doc_scores[text] += rrf_score
                
                # 保存文档数据（保留第一个出现的完整数据）
                if text not in doc_data:
                    doc_data[text] = result
        
        # 按分数排序
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        
        # 构建最终结果
        final_results = []
        for text, score in sorted_docs:
            result = doc_data[text].copy()
            result["rrf_score"] = score
            result["combined_score"] = score
            final_results.append(result)
        
        return final_results
    
    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去重结果"""
        seen_texts = set()
        unique_results = []
        
        for result in results:
            text = result.get("text", "")
            # 使用文本的前100个字符作为去重key
            text_key = text[:100] if len(text) > 100 else text
            
            if text_key not in seen_texts:
                seen_texts.add(text_key)
                unique_results.append(result)
        
        return unique_results
    
    def retrieve(self, query: str, top_k: int = 10, 
                 enable_vector: bool = True,
                 enable_bm25: bool = True,
                 enable_semantic: bool = True,
                 enable_kg: bool = True) -> List[Dict[str, Any]]:
        """
        多路召回检索（并行执行，大幅减少等待时间）
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import time as _time

        all_results = []
        all_weights = []
        vector_results = []

        # 定义各检索任务
        def _do_vector():
            if not enable_vector:
                return []
            try:
                results = self.vector_retriever.retrieve(query, top_k=top_k * 2)
                if results:
                    app_logger.info(f"向量检索返回 {len(results)} 条结果")
                return results
            except Exception as e:
                app_logger.warning(f"向量检索失败: {e}")
                return []

        def _do_bm25():
            if not enable_bm25:
                return []
            try:
                results = self.bm25_retriever.retrieve(query, top_k=top_k * 2)
                if results:
                    app_logger.info(f"BM25检索返回 {len(results)} 条结果")
                return results
            except Exception as e:
                app_logger.warning(f"BM25检索失败: {e}")
                return []

        def _do_kg():
            if not enable_kg:
                return []
            try:
                results = self.kg_retriever.retrieve(query, top_k=top_k)
                if results:
                    app_logger.info(f"知识图谱检索返回 {len(results)} 条结果")
                return results
            except Exception as e:
                app_logger.warning(f"知识图谱检索失败: {e}")
                return []

        # 并行执行向量、BM25、KG检索
        start = _time.time()
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(_do_vector): "vector",
                executor.submit(_do_bm25): "bm25",
                executor.submit(_do_kg): "kg",
            }

            kg_results = []
            for future in as_completed(futures):
                method = futures[future]
                try:
                    results = future.result()
                    if results:
                        if method == "vector":
                            vector_results = results
                            all_results.append(results)
                            all_weights.append(self.weights["vector"])
                        elif method == "bm25":
                            all_results.append(results)
                            all_weights.append(self.weights["bm25"])
                        elif method == "kg":
                            kg_results = results
                            all_results.append(results)
                            all_weights.append(self.weights["kg"])
                except Exception as e:
                    app_logger.warning(f"{method} 检索异常: {e}")

        app_logger.info(f"并行多路检索耗时: {_time.time() - start:.2f}s")

        # 语义检索依赖向量结果，在并行后单独执行
        if enable_semantic and vector_results:
            try:
                semantic_results = self.semantic_retriever.semantic_search(
                    query, vector_results, top_k=top_k
                )
                if semantic_results:
                    all_results.append(semantic_results)
                    all_weights.append(self.weights["semantic"])
                    app_logger.info(f"语义检索返回 {len(semantic_results)} 条结果")
            except Exception as e:
                app_logger.warning(f"语义检索失败: {e}")

        # 如果没有结果，返回空列表
        if not all_results:
            app_logger.warning("所有检索方法都失败，返回空结果")
            return []
        
        # 归一化权重
        total_weight = sum(all_weights)
        if total_weight > 0:
            all_weights = [w / total_weight for w in all_weights]
        
        # RRF融合
        fused_results = self._reciprocal_rank_fusion(all_results, all_weights)
        
        # 去重
        unique_results = self._deduplicate_results(fused_results)
        
        # 返回top_k
        final_results = unique_results[:top_k]
        
        app_logger.info(f"多路召回完成，查询: {query}, 融合后返回 {len(final_results)} 条结果")
        
        return final_results
    
    def get_retrieval_stats(self, query: str) -> Dict[str, Any]:
        """获取检索统计信息"""
        stats = {
            "query": query,
            "methods": {},
            "total_results": 0
        }
        
        # 测试各方法
        try:
            vector_results = self.vector_retriever.retrieve(query, top_k=5)
            stats["methods"]["vector"] = len(vector_results)
        except Exception:
            stats["methods"]["vector"] = 0
        
        try:
            bm25_results = self.bm25_retriever.retrieve(query, top_k=5)
            stats["methods"]["bm25"] = len(bm25_results)
        except Exception:
            stats["methods"]["bm25"] = 0
        
        try:
            kg_results = self.kg_retriever.retrieve(query, top_k=5)
            stats["methods"]["kg"] = len(kg_results)
        except Exception:
            stats["methods"]["kg"] = 0
        
        stats["total_results"] = sum(stats["methods"].values())
        
        return stats

