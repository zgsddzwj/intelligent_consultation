"""混合检索（向量检索 + 关键词匹配）- 增强版（检索结果缓存、多路召回优化、智能融合）"""
import time
import hashlib
import threading
from typing import List, Dict, Any, Optional
from collections import OrderedDict
from app.knowledge.rag.retriever import Retriever
from app.knowledge.rag.multi_retrieval import MultiRetrieval
from app.knowledge.rag.reranker import Reranker
from app.utils.logger import app_logger
import re


class RetrievalCache:
    """检索结果缓存（线程安全LRU）"""
    
    def __init__(self, max_size: int = 200, ttl: int = 180):
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._timestamps: Dict[str, float] = {}
        self._max_size = max_size
        self._ttl = ttl
        self._lock = threading.Lock()
        self._stats = {"hits": 0, "misses": 0}
    
    def _make_key(self, query: str, top_k: int, method: str) -> str:
        key_data = f"{query}:{top_k}:{method}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]
    
    def get(self, query: str, top_k: int, method: str = "hybrid") -> Optional[List[Dict]]:
        key = self._make_key(query, top_k, method)
        with self._lock:
            if key in self._cache:
                if time.time() - self._timestamps.get(key, 0) > self._ttl:
                    del self._cache[key]
                    del self._timestamps[key]
                    self._stats["misses"] += 1
                    return None
                self._cache.move_to_end(key)
                self._stats["hits"] += 1
                return self._cache[key]
            self._stats["misses"] += 1
            return None
    
    def set(self, query: str, top_k: int, results: List[Dict], method: str = "hybrid"):
        key = self._make_key(query, top_k, method)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = results
            self._timestamps[key] = time.time()
            while len(self._cache) > self._max_size:
                old_key, _ = self._cache.popitem(last=False)
                self._timestamps.pop(old_key, None)
    
    def get_stats(self) -> Dict[str, int]:
        with self._lock:
            total = self._stats["hits"] + self._stats["misses"]
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "hit_rate": round(self._stats["hits"] / max(total, 1) * 100, 2)
            }


class HybridSearch:
    """混合检索器 - 增强版
    
    新增功能：
    - 检索结果LRU缓存
    - 多路召回智能融合
    - BGE重排序集成
    - 检索性能统计
    """
    
    def __init__(self, use_advanced: bool = True, use_reranker: bool = True,
                 cache_size: int = 200, cache_ttl: int = 180):
        self.use_advanced = use_advanced
        self.use_reranker = use_reranker
        self.retriever = Retriever()
        self.multi_retrieval = MultiRetrieval() if use_advanced else None
        self.reranker = Reranker() if use_reranker else None
        self._cache = RetrievalCache(max_size=cache_size, ttl=cache_ttl)
        self._stats = {
            "total_searches": 0,
            "cached_searches": 0,
            "reranked_searches": 0,
            "total_time": 0.0
        }
        self._stats_lock = threading.Lock()
    
    def extract_keywords(self, query: str) -> List[str]:
        """提取关键词（支持中英文）"""
        # 中文分词（简单实现）
        chinese_words = re.findall(r'[\u4e00-\u9fff]{2,}', query)
        # 英文单词
        english_words = re.findall(r'[a-zA-Z]{3,}', query.lower())
        # 数字
        numbers = re.findall(r'\d+', query)
        
        keywords = chinese_words + english_words + numbers
        return keywords
    
    def keyword_match_score(self, text: str, keywords: List[str]) -> float:
        """计算关键词匹配分数"""
        if not keywords:
            return 0.0
        
        text_lower = text.lower()
        matches = 0
        for keyword in keywords:
            if keyword.lower() in text_lower:
                matches += 1
        
        return matches / len(keywords)
    
    def hybrid_search(self, query: str, top_k: int = 5,
                      use_cache: bool = True) -> List[Dict[str, Any]]:
        """混合检索（带缓存和重排序）"""
        start_time = time.time()
        
        with self._stats_lock:
            self._stats["total_searches"] += 1
        
        # 尝试从缓存获取
        if use_cache:
            cached = self._cache.get(query, top_k, "hybrid")
            if cached is not None:
                with self._stats_lock:
                    self._stats["cached_searches"] += 1
                app_logger.debug(f"检索缓存命中: {query[:30]}...")
                return cached
        
        # 执行检索
        results = self._do_search(query, top_k)
        
        # 重排序
        if self.use_reranker and self.reranker and len(results) > 1:
            try:
                results = self.reranker.rerank(query, results, top_k=top_k)
                with self._stats_lock:
                    self._stats["reranked_searches"] += 1
            except Exception as e:
                app_logger.warning(f"重排序失败: {e}")
        
        # 写入缓存
        if use_cache:
            self._cache.set(query, top_k, results, "hybrid")
        
        # 更新统计
        duration = time.time() - start_time
        with self._stats_lock:
            self._stats["total_time"] += duration
        
        return results
    
    def _do_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """执行实际检索"""
        # 优先使用多路召回
        if self.use_advanced and self.multi_retrieval:
            try:
                results = self.multi_retrieval.retrieve(query, top_k=top_k * 2)
                if results:
                    app_logger.info(f"多路召回完成，返回 {len(results)} 条结果")
                    return self._normalize_scores(results)[:top_k]
            except Exception as e:
                app_logger.warning(f"多路召回失败，降级到传统混合检索: {e}")
        
        # 传统混合检索
        return self._traditional_hybrid_search(query, top_k)
    
    def _traditional_hybrid_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """传统混合检索（向量+关键词）"""
        # 向量检索
        vector_results = self.retriever.retrieve(query, top_k=top_k * 3)
        
        # 提取关键词
        keywords = self.extract_keywords(query)
        
        # 计算综合分数
        scored_results = []
        seen_texts = set()
        
        for result in vector_results:
            text = result.get("text", "")
            text_hash = hashlib.md5(text[:100].encode()).hexdigest()[:16]
            
            # 去重
            if text_hash in seen_texts:
                continue
            seen_texts.add(text_hash)
            
            # 向量分数（转换为相似度）
            raw_score = result.get("score", 1.0)
            vector_score = 1.0 / (1.0 + raw_score) if raw_score > 0 else 0.5
            
            # 关键词分数
            keyword_score = self.keyword_match_score(text, keywords)
            
            # 综合分数（向量60%，关键词40%）
            combined_score = 0.6 * vector_score + 0.4 * keyword_score
            
            scored_results.append({
                **result,
                "combined_score": round(combined_score, 4),
                "vector_score": round(vector_score, 4),
                "keyword_score": round(keyword_score, 4),
                "retrieval_method": "hybrid"
            })
        
        # 排序并返回
        scored_results.sort(key=lambda x: x["combined_score"], reverse=True)
        return scored_results[:top_k]
    
    def _normalize_scores(self, results: List[Dict]) -> List[Dict]:
        """归一化分数到0-1范围"""
        if not results:
            return results
        
        scores = [r.get("score", 0) for r in results]
        max_score = max(scores) if scores else 1
        min_score = min(scores) if scores else 0
        score_range = max_score - min_score if max_score != min_score else 1
        
        for result in results:
            raw_score = result.get("score", 0)
            normalized = (raw_score - min_score) / score_range
            result["normalized_score"] = round(normalized, 4)
            result["combined_score"] = round(normalized, 4)
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """获取检索统计"""
        with self._stats_lock:
            stats = dict(self._stats)
        
        total = stats["total_searches"]
        return {
            **stats,
            "cache_stats": self._cache.get_stats(),
            "avg_search_time_ms": round(
                stats["total_time"] / max(total - stats["cached_searches"], 1) * 1000, 2
            ),
            "cache_hit_rate": round(
                stats["cached_searches"] / max(total, 1) * 100, 2
            )
        }
    
    def clear_cache(self):
        """清空检索缓存"""
        self._cache = RetrievalCache()
        app_logger.info("检索缓存已清空")
