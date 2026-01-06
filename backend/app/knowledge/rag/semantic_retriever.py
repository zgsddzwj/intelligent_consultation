"""语义检索器 - 基于语义理解的检索"""
from typing import List, Dict, Any
from app.knowledge.rag.embedder import Embedder
from app.services.llm_service import LLMService
from app.utils.logger import app_logger
import re


class SemanticRetriever:
    """语义检索器 - 使用LLM进行查询扩展和语义理解"""
    
    def __init__(self):
        self.embedder = Embedder()
        self.llm = LLMService()
        self._medical_terms_cache = {}
    
    def expand_query(self, query: str) -> Dict[str, Any]:
        """查询扩展 - 生成同义词和相关术语"""
        try:
            prompt = f"""
请分析以下医疗查询，提取关键信息并生成相关的同义词和医学术语：

查询：{query}

请以JSON格式返回：
{{
    "keywords": ["关键词1", "关键词2"],
    "synonyms": ["同义词1", "同义词2"],
    "medical_terms": ["医学术语1", "医学术语2"],
    "expanded_query": "扩展后的查询"
}}
"""
            
            response = self.llm.generate(
                prompt=prompt,
                temperature=0.3,
                max_tokens=500
            )
            
            # 解析响应（简化处理，实际应该更robust）
            expanded = {
                "original_query": query,
                "expanded_query": query,  # 默认使用原查询
                "keywords": self._extract_keywords(query),
                "synonyms": [],
                "medical_terms": []
            }
            
            # 尝试从响应中提取JSON（简化实现）
            # 实际应该使用更robust的JSON解析
            
            return expanded
            
        except Exception as e:
            app_logger.warning(f"查询扩展失败: {e}")
            return {
                "original_query": query,
                "expanded_query": query,
                "keywords": self._extract_keywords(query),
                "synonyms": [],
                "medical_terms": []
            }
    
    def _extract_keywords(self, text: str) -> List[str]:
        """简单关键词提取"""
        # 移除标点
        words = re.findall(r'\b\w+\b', text)
        # 过滤短词
        keywords = [w for w in words if len(w) > 1]
        return keywords
    
    def rewrite_query(self, query: str, context: str = None) -> str:
        """查询重写 - 将自然语言查询转换为更精确的检索查询"""
        try:
            context_part = f"\n上下文：{context}" if context else ""
            prompt = f"""
请将以下医疗查询重写为更适合检索的形式，保持核心医疗概念：

查询：{query}{context_part}

请直接返回重写后的查询，不要添加其他说明。
"""
            
            rewritten = self.llm.generate(
                prompt=prompt,
                temperature=0.2,
                max_tokens=200
            )
            
            return rewritten.strip()
            
        except Exception as e:
            app_logger.warning(f"查询重写失败: {e}")
            return query
    
    def semantic_search(self, query: str, documents: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        """语义检索 - 基于语义相似度"""
        try:
            # 扩展查询
            expanded = self.expand_query(query)
            
            # 使用扩展后的查询进行向量检索
            query_text = expanded.get("expanded_query", query)
            query_vector = self.embedder.embed_query(query_text)
            
            # 计算与所有文档的相似度
            doc_vectors = []
            for doc in documents:
                doc_text = doc.get("text", "")
                if doc_text:
                    doc_vector = self.embedder.embed_query(doc_text)
                    doc_vectors.append(doc_vector)
                else:
                    doc_vectors.append(None)
            
            # 计算余弦相似度
            results = []
            for i, doc in enumerate(documents):
                if doc_vectors[i] is None:
                    continue
                
                # 计算余弦相似度
                similarity = self._cosine_similarity(query_vector, doc_vectors[i])
                
                results.append({
                    **doc,
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

