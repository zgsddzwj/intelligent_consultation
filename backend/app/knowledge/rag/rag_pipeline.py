"""RAG管道 - 企业级检索增强生成管道

整合检索、重排序、上下文构建、答案生成全流程，
支持可配置策略、性能监控和错误降级。
"""
import time
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from app.knowledge.rag.retriever import Retriever
from app.knowledge.rag.hybrid_search import HybridSearch
from app.knowledge.rag.reranker import Reranker
from app.utils.logger import app_logger


@dataclass
class RAGConfig:
    """RAG管道配置"""
    # 检索配置
    retrieval_top_k: int = 10
    use_hybrid_search: bool = True
    use_query_expansion: bool = True

    # 重排序配置
    use_reranker: bool = True
    reranker_top_k: int = 5

    # 上下文配置
    max_context_length: int = 4000
    context_format: str = "citation"  # citation / plain / structured

    # 生成配置
    max_answer_length: int = 2000
    temperature: float = 0.7

    # 性能配置
    timeout: float = 30.0
    enable_cache: bool = True


@dataclass
class RAGResult:
    """RAG管道结果"""
    answer: str
    sources: List[Dict[str, Any]] = field(default_factory=list)
    context: str = ""
    retrieval_time_ms: float = 0.0
    rerank_time_ms: float = 0.0
    total_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class RAGPipeline:
    """RAG管道 - 企业级实现"""

    def __init__(self, config: RAGConfig = None):
        self.config = config or RAGConfig()
        self.retriever = Retriever(use_query_expansion=self.config.use_query_expansion)
        self.hybrid_search = HybridSearch() if self.config.use_hybrid_search else None
        self.reranker = Reranker() if self.config.use_reranker else None
        self._stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "avg_retrieval_time_ms": 0.0,
            "avg_rerank_time_ms": 0.0,
            "avg_total_time_ms": 0.0,
        }

    def run(self, query: str, system_prompt: str = None,
            conversation_history: List[Dict] = None,
            filter_expr: str = None) -> RAGResult:
        """执行完整的RAG流程"""
        start_time = time.time()
        self._stats["total_queries"] += 1

        try:
            # 1. 检索
            retrieval_start = time.time()
            raw_results = self._retrieve(query, filter_expr)
            retrieval_time = (time.time() - retrieval_start) * 1000

            # 2. 重排序
            rerank_start = time.time()
            ranked_results = self._rerank(query, raw_results)
            rerank_time = (time.time() - rerank_start) * 1000

            # 3. 构建上下文
            context = self._build_context(ranked_results)

            # 4. 生成答案
            answer = self._generate_answer(query, context, system_prompt, conversation_history)

            total_time = (time.time() - start_time) * 1000

            self._stats["successful_queries"] += 1
            self._update_time_stats(retrieval_time, rerank_time, total_time)

            return RAGResult(
                answer=answer,
                sources=ranked_results,
                context=context,
                retrieval_time_ms=round(retrieval_time, 2),
                rerank_time_ms=round(rerank_time, 2),
                total_time_ms=round(total_time, 2),
                metadata={
                    "raw_result_count": len(raw_results),
                    "ranked_result_count": len(ranked_results),
                    "context_length": len(context),
                    "query": query
                }
            )

        except Exception as e:
            self._stats["failed_queries"] += 1
            app_logger.error(f"RAG管道执行失败: {e}")
            return RAGResult(
                answer="抱歉，检索相关信息时遇到问题，请稍后重试。",
                sources=[],
                context="",
                total_time_ms=round((time.time() - start_time) * 1000, 2),
                metadata={"error": str(e), "query": query}
            )

    def _retrieve(self, query: str, filter_expr: str = None) -> List[Dict[str, Any]]:
        """执行检索"""
        if self.hybrid_search:
            results = self.hybrid_search.hybrid_search(
                query, top_k=self.config.retrieval_top_k
            )
        else:
            results = self.retriever.retrieve(
                query,
                top_k=self.config.retrieval_top_k,
                filter_expr=filter_expr,
                use_expansion=self.config.use_query_expansion
            )
        return results

    def _rerank(self, query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """执行重排序"""
        if not self.reranker or len(results) <= 1:
            return results[:self.config.reranker_top_k]

        try:
            reranked = self.reranker.rerank(
                query, results, top_k=self.config.reranker_top_k
            )
            return reranked
        except Exception as e:
            app_logger.warning(f"重排序失败，使用原始排序: {e}")
            return results[:self.config.reranker_top_k]

    def _build_context(self, results: List[Dict[str, Any]]) -> str:
        """构建上下文"""
        if self.config.context_format == "citation":
            context = self.retriever.format_context(results)
        elif self.config.context_format == "plain":
            context = "\n\n".join(r.get("text", "") for r in results)
        else:
            context = self.retriever.format_context(results)

        # 截断到最大长度
        if len(context) > self.config.max_context_length:
            context = context[:self.config.max_context_length] + "\n...[内容已截断]"

        return context

    def _generate_answer(self, query: str, context: str,
                         system_prompt: str = None,
                         conversation_history: List[Dict] = None) -> str:
        """生成答案（简化版，实际应调用LLM服务）"""
        # 这里返回上下文，由调用方使用LLM服务生成最终答案
        # 实际实现中，可以集成llm_service进行生成
        return f"基于检索到的信息：\n\n{context}\n\n用户问题：{query}"

    def _update_time_stats(self, retrieval_time: float, rerank_time: float, total_time: float):
        """更新时间统计（滑动平均）"""
        n = self._stats["successful_queries"]
        self._stats["avg_retrieval_time_ms"] = (
            (self._stats["avg_retrieval_time_ms"] * (n - 1) + retrieval_time) / n
        )
        self._stats["avg_rerank_time_ms"] = (
            (self._stats["avg_rerank_time_ms"] * (n - 1) + rerank_time) / n
        )
        self._stats["avg_total_time_ms"] = (
            (self._stats["avg_total_time_ms"] * (n - 1) + total_time) / n
        )

    def get_stats(self) -> Dict[str, Any]:
        """获取管道统计信息"""
        total = self._stats["total_queries"]
        return {
            **self._stats,
            "success_rate": round(self._stats["successful_queries"] / max(total, 1) * 100, 2),
            "config": {
                "retrieval_top_k": self.config.retrieval_top_k,
                "use_hybrid_search": self.config.use_hybrid_search,
                "use_reranker": self.config.use_reranker,
            }
        }

    def clear_cache(self):
        """清除缓存"""
        if self.hybrid_search:
            self.hybrid_search.clear_cache()
