"""语义检索器 - 基于语义理解的检索"""
from typing import List, Dict, Any
from app.knowledge.rag.embedder import Embedder
from app.utils.logger import app_logger
import re


class SemanticRetriever:
    """语义检索器 - 基于向量相似度的语义级召回

    说明：查询扩展采用轻量规则实现（分词/别名映射），
    不再发起LLM调用——旧实现每次扩展白白消耗一次完整LLM请求且结果从未被使用。
    """

    def __init__(self):
        self.embedder = Embedder()

    # 常见医疗口语/缩写到规范术语的轻量映射（规则化查询扩展，无网络开销）
    _SYNONYM_MAP = {
        "高血压": ["血压高", "hypertension"],
        "糖尿病": ["血糖高", "diabetes"],
        "发烧": ["发热", "体温升高"],
        "感冒": ["上呼吸道感染"],
        "拉肚子": ["腹泻"],
        "头疼": ["头痛"],
        "心梗": ["心肌梗死"],
        "中风": ["脑卒中", "脑梗"],
    }

    def expand_query(self, query: str) -> Dict[str, Any]:
        """查询扩展 - 规则化生成同义词与关键词（零延迟、零成本）"""
        keywords = self._extract_keywords(query)
        synonyms: List[str] = []
        for term, alts in self._SYNONYM_MAP.items():
            if term in query:
                synonyms.extend(alts)

        expanded_query = query
        if synonyms:
            # 同义词附加到原查询后，提升向量召回覆盖面
            expanded_query = f"{query} {' '.join(synonyms)}"

        return {
            "original_query": query,
            "expanded_query": expanded_query,
            "keywords": keywords,
            "synonyms": synonyms,
            "medical_terms": [],
        }

    def _extract_keywords(self, text: str) -> List[str]:
        """简单关键词提取"""
        # 移除标点
        words = re.findall(r'\b\w+\b', text)
        # 过滤短词
        keywords = [w for w in words if len(w) > 1]
        return keywords

    def semantic_search(self, query: str, documents: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        """语义检索 - 基于语义相似度（文档向量一次批量编码，避免逐条请求embedding API）"""
        try:
            if not documents:
                return []

            # 扩展查询
            expanded = self.expand_query(query)
            query_text = expanded.get("expanded_query", query)

            # 单次批量编码所有文档文本（旧实现逐文档调用embed_query，N次HTTP往返）
            valid_indices: List[int] = []
            doc_texts: List[str] = []
            for i, doc in enumerate(documents):
                doc_text = doc.get("text", "")
                if doc_text:
                    valid_indices.append(i)
                    doc_texts.append(doc_text)

            if not doc_texts:
                return []

            doc_vectors = self.embedder.embed(doc_texts)
            query_vector = self.embedder.embed_query(query_text)

            # 计算余弦相似度
            results = []
            for idx, doc_vector in zip(valid_indices, doc_vectors):
                if doc_vector is None:
                    continue
                similarity = self._cosine_similarity(query_vector, doc_vector)
                results.append({
                    **documents[idx],
                    "score": similarity,
                    "retrieval_method": "semantic",
                    "expanded_query": query_text
                })

            # 按相似度排序
            results.sort(key=lambda x: x["score"], reverse=True)

            # 返回top_k
            final_results = results[:top_k]

            app_logger.info(f"语义检索完成，查询: {query}, 返回 {len(final_results)} 条结果")
            return final_results

        except Exception as e:
            app_logger.error(f"语义检索失败: {e}")
            return []

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        try:
            import numpy as np
            vec1 = np.array(vec1)
            vec2 = np.array(vec2)
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            if norm1 == 0 or norm2 == 0:
                return 0.0
            return float(dot_product / (norm1 * norm2))
        except Exception as e:
            app_logger.warning(f"余弦相似度计算失败: {e}")
            return 0.0

    def retrieve(self, query: str, documents: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        """检索接口 - 兼容其他检索器"""
        return self.semantic_search(query, documents, top_k)
