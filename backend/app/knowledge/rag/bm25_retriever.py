"""BM25检索器"""
from typing import List, Dict, Any, Optional
import threading
import time
from rank_bm25 import BM25Okapi
import jieba
import jieba.analyse
from app.utils.logger import app_logger
from app.services.milvus_service import get_milvus_service


class BM25Retriever:
    """BM25检索器 - 基于关键词匹配的检索

    索引懒构建：首次检索时从Milvus拉取全量文本构建（旧实现 build_index
    无任何调用方，索引永远为空，30%召回权重静默失效）。
    """

    # 构建失败后的退避时间（秒），期间不再尝试，避免每次检索都打一次Milvus
    _REBUILD_BACKOFF = 300

    def __init__(self):
        self.bm25: Optional[BM25Okapi] = None
        self.documents: List[str] = []
        self.doc_metadata: List[Dict[str, Any]] = []
        self._indexed = False
        self._last_build_failed_at = 0.0
        self._build_lock = threading.Lock()

    def _ensure_index(self) -> bool:
        """确保索引可用：未构建时从Milvus全量文本懒构建（并发安全+失败退避）"""
        if self._indexed:
            return True
        if time.time() - self._last_build_failed_at < self._REBUILD_BACKOFF:
            return False

        with self._build_lock:
            # 双重检查：另一线程可能已完成构建
            if self._indexed:
                return True

            try:
                milvus = get_milvus_service()
                texts, metas = milvus.fetch_all_documents()
                if not texts:
                    self._last_build_failed_at = time.time()
                    app_logger.warning("Milvus无可索引文本，BM25通道降级（5分钟内不再重试）")
                    return False
                self.build_index(texts, metas)
                if not self._indexed:
                    self._last_build_failed_at = time.time()
                    return False
                return True
            except Exception as e:
                self._last_build_failed_at = time.time()
                app_logger.warning(f"BM25索引懒构建失败（5分钟内不再重试）: {e}")
                return False

    def _load_index(self):
        """兼容保留：索引在首次检索时按需构建"""
        app_logger.debug("BM25索引延迟构建（首次检索时从Milvus拉取文本）")
        self._indexed = False
    
    def _tokenize(self, text: str) -> List[str]:
        """中文分词"""
        # 使用jieba进行分词
        words = jieba.cut(text)
        # 过滤停用词和标点
        stopwords = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
        tokens = [w.strip() for w in words if w.strip() and w.strip() not in stopwords and len(w.strip()) > 1]
        return tokens
    
    def build_index(self, documents: List[str], metadata: List[Dict[str, Any]] = None):
        """构建BM25索引"""
        try:
            self.documents = documents
            self.doc_metadata = metadata or [{}] * len(documents)
            
            # 分词
            tokenized_docs = [self._tokenize(doc) for doc in documents]
            
            # 构建BM25索引
            self.bm25 = BM25Okapi(tokenized_docs)
            self._indexed = True
            
            app_logger.info(f"BM25索引构建完成，文档数: {len(documents)}")
        except Exception as e:
            app_logger.error(f"BM25索引构建失败: {e}")
            self._indexed = False
    
    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """BM25检索（索引未构建时自动从Milvus懒构建）"""
        if not self._ensure_index():
            return []
        
        try:
            # 查询分词
            query_tokens = self._tokenize(query)
            
            if not query_tokens:
                return []
            
            # BM25评分
            scores = self.bm25.get_scores(query_tokens)
            
            # 获取top_k结果
            top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
            
            results = []
            for idx in top_indices:
                if scores[idx] > 0:  # 只返回有分数的结果
                    results.append({
                        "text": self.documents[idx],
                        "source": self.doc_metadata[idx].get("source", "unknown"),
                        "metadata": self.doc_metadata[idx],
                        "score": float(scores[idx]),
                        "retrieval_method": "bm25",
                        "document_id": self.doc_metadata[idx].get("document_id")
                    })
            
            app_logger.info(f"BM25检索完成，查询: {query}, 返回 {len(results)} 条结果")
            return results
            
        except Exception as e:
            app_logger.error(f"BM25检索失败: {e}")
            return []
    
    def extract_keywords(self, text: str, top_k: int = 10) -> List[str]:
        """提取关键词（使用TF-IDF）"""
        try:
            keywords = jieba.analyse.extract_tags(text, topK=top_k, withWeight=False)
            return keywords
        except Exception as e:
            app_logger.warning(f"关键词提取失败: {e}")
            return []

