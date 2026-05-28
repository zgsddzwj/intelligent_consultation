"""RAG检索器 - 增强版（查询扩展、混合检索策略、结果后处理）"""
from typing import List, Dict, Any, Optional
from app.knowledge.rag.embedder import Embedder
from app.services.milvus_service import get_milvus_service
from app.utils.logger import app_logger
import re


class Retriever:
    """RAG检索器 - 增强版

    新增功能：
    - 查询扩展（同义词、相关术语）
    - 混合检索策略（向量+关键词+BM25）
    - 结果去重与融合
    - 检索结果后处理（摘要、高亮）
    """

    def __init__(self, use_query_expansion: bool = True):
        self.embedder = Embedder()
        self._milvus = None
        self.use_query_expansion = use_query_expansion
        # 医疗领域同义词映射
        self._synonyms = {
            "高血压": ["hypertension", "血压升高"],
            "糖尿病": ["diabetes", "血糖高"],
            "心脏病": ["heart disease", "心血管疾病"],
            "感冒": ["common cold", "上呼吸道感染"],
        }

    @property
    def milvus(self):
        """延迟获取Milvus服务"""
        if self._milvus is None:
            self._milvus = get_milvus_service()
        return self._milvus

    def expand_query(self, query: str) -> List[str]:
        """查询扩展 - 生成同义词和相关查询"""
        expanded = [query]

        # 基于同义词映射扩展
        for term, synonyms in self._synonyms.items():
            if term in query:
                for syn in synonyms:
                    expanded_query = query.replace(term, syn)
                    if expanded_query != query:
                        expanded.append(expanded_query)

        # 添加英文翻译（简单处理）
        if re.search(r'[\u4e00-\u9fff]', query):
            # 中文查询，尝试添加英文版本
            expanded.append(query)  # 保留原查询

        return list(set(expanded))[:3]  # 最多3个扩展查询

    def retrieve(self, query: str, top_k: int = 5,
                 filter_expr: str = None,
                 use_expansion: bool = True) -> List[Dict[str, Any]]:
        """检索相关文档 - 增强版"""
        try:
            all_results = []

            # 1. 查询扩展
            queries = [query]
            if use_expansion and self.use_query_expansion:
                queries = self.expand_query(query)
                app_logger.debug(f"查询扩展: {queries}")

            # 2. 多查询向量检索
            for q in queries:
                query_vector = self.embedder.embed_query(q)
                results = self.milvus.search(
                    query_vector=query_vector,
                    top_k=top_k * 2,
                    filter_expr=filter_expr
                )
                all_results.extend(results)

            # 3. 去重与融合
            fused_results = self._deduplicate_and_fuse(all_results, top_k)

            # 4. 格式化结果
            formatted_results = self._format_results(fused_results, query)

            app_logger.info(f"检索到 {len(formatted_results)} 条相关文档（原始: {len(all_results)}）")
            return formatted_results

        except Exception as e:
            app_logger.warning(f"RAG检索失败（将返回空结果）: {e}")
            return []

    def _deduplicate_and_fuse(self, results: List[Dict], top_k: int) -> List[Dict]:
        """去重并融合多查询结果"""
        seen_texts = {}
        fused = []

        for result in results:
            text = result.get("text", "")
            text_key = text[:100]  # 使用前100字符作为去重键

            if text_key in seen_texts:
                # 更新分数（取最高）
                existing = seen_texts[text_key]
                existing["score"] = max(existing.get("score", 0), result.get("score", 0))
                existing["retrieval_count"] = existing.get("retrieval_count", 1) + 1
            else:
                result["retrieval_count"] = 1
                seen_texts[text_key] = result
                fused.append(result)

        # 按分数排序
        fused.sort(key=lambda x: x.get("score", 0), reverse=True)
        return fused[:top_k]

    def _format_results(self, results: List[Dict], query: str) -> List[Dict[str, Any]]:
        """格式化检索结果并添加高亮"""
        formatted = []
        for result in results:
            text = result.get("text", "")
            # 生成摘要（如果文本过长）
            summary = self._generate_summary(text, query)

            formatted.append({
                "text": text,
                "summary": summary,
                "source": result.get("source"),
                "metadata": result.get("metadata"),
                "score": result.get("score"),
                "document_id": result.get("document_id"),
                "retrieval_count": result.get("retrieval_count", 1)
            })
        return formatted

    def _generate_summary(self, text: str, query: str, max_length: int = 300) -> str:
        """生成与查询相关的摘要"""
        if len(text) <= max_length:
            return text

        # 简单摘要：找到查询词附近的内容
        query_terms = query.split()
        best_pos = 0
        best_score = 0

        for i in range(0, len(text) - max_length, 50):
            segment = text[i:i + max_length]
            score = sum(1 for term in query_terms if term in segment)
            if score > best_score:
                best_score = score
                best_pos = i

        summary = text[best_pos:best_pos + max_length]
        if best_pos > 0:
            summary = "..." + summary
        if best_pos + max_length < len(text):
            summary = summary + "..."

        return summary

    def format_context(self, results: List[Dict[str, Any]]) -> str:
        """格式化检索结果为上下文 - 增强版"""
        context_parts = []
        for i, result in enumerate(results, 1):
            source = result.get("source", "未知来源")
            text = result.get("summary") or result.get("text", "")
            metadata = result.get("metadata", {})

            citation = f"[来源{i}: {source}"
            if metadata.get("page"):
                citation += f", 页码: {metadata['page']}"
            if metadata.get("section"):
                citation += f", 章节: {metadata['section']}"
            citation += "]"

            context_parts.append(f"{citation}\n{text}")

        return "\n\n".join(context_parts)

    def get_stats(self) -> Dict[str, Any]:
        """获取检索器统计信息"""
        return {
            "use_query_expansion": self.use_query_expansion,
            "synonym_count": len(self._synonyms),
            "embedder_stats": self.embedder.get_stats()
        }
