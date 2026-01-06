"""BM25检索器"""
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi
import jieba
import jieba.analyse
from app.utils.logger import app_logger
from app.services.milvus_service import get_milvus_service


class BM25Retriever:
    """BM25检索器 - 基于关键词匹配的检索"""
    
    def __init__(self):
        self.bm25: Optional[BM25Okapi] = None
        self.documents: List[str] = []
        self.doc_metadata: List[Dict[str, Any]] = []
        self._indexed = False
        self._load_index()
    
    def _load_index(self):
        """从Milvus加载文档索引"""
        try:
            milvus = get_milvus_service()
            # 从Milvus获取所有文档（用于构建BM25索引）
            # 这里需要从Milvus获取文档文本，实际实现可能需要调整
            app_logger.info("BM25索引加载中...")
            # 暂时标记为未索引，等待文档加载
            self._indexed = False
        except Exception as e:
            app_logger.warning(f"BM25索引加载失败: {e}")
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
        """BM25检索"""
        if not self._indexed or not self.bm25:
            app_logger.warning("BM25索引未构建，返回空结果")
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

