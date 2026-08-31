"""Reranker - BGE-Reranker模型集成"""
from typing import List, Dict, Any, Optional
from app.utils.logger import app_logger
import os
import threading


class BGEReranker:
    """BGE-Reranker - 使用FlagEmbedding的BGE-Reranker模型（单例模式）"""

    _instance = None
    _lock = threading.Lock()

    # 单个文档送入模型的最大字符数，防止超长文本导致OOM
    MAX_DOC_CHARS = 2048
    # 批量评分时每批的最大文档数，避免显存溢出
    BATCH_SIZE = 32

    def __new__(cls, model_name: str = "BAAI/bge-reranker-base"):
        """单例：相同模型名只加载一次"""
        with cls._lock:
            if cls._instance is not None:
                # 已有实例则直接复用（加载失败也复用，避免每请求抢锁重试下载）
                if cls._instance.model_name == model_name:
                    return cls._instance
            instance = super().__new__(cls)
            instance.model_name = model_name
            instance.model = None
            instance.tokenizer = None
            instance._loaded = False
            cls._instance = instance
        # 模型加载耗时较长，移到锁外执行，避免长时间持锁阻塞并发构造
        instance._load_model()
        return instance
    
    def _load_model(self):
        """加载BGE-Reranker模型"""
        try:
            from FlagEmbedding import FlagReranker
            self.model = FlagReranker(self.model_name, use_fp16=True)
            self._loaded = True
            app_logger.info(f"BGE-Reranker模型加载成功: {self.model_name}")
        except ImportError:
            app_logger.warning("FlagEmbedding未安装，BGE-Reranker将不可用")
            self._loaded = False
        except Exception as e:
            app_logger.warning(f"BGE-Reranker模型加载失败: {e}")
            self._loaded = False
    
    def rerank(self, query: str, documents: List[Dict[str, Any]], top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        重排序文档
        
        Args:
            query: 查询文本
            documents: 文档列表，每个文档包含text字段
            top_k: 返回top_k个结果，None表示返回所有
        
        Returns:
            重排序后的文档列表
        """
        if not self._loaded or not self.model:
            app_logger.warning("BGE-Reranker未加载，返回原始顺序")
            return documents
        
        if not documents:
            return []
        
        try:
            # 构建查询-文档对，对超长文档做截断保护
            pairs = []
            for doc in documents:
                doc_text = doc.get("text", "")
                if doc_text:
                    # 截断超长文档，防止OOM
                    if len(doc_text) > self.MAX_DOC_CHARS:
                        doc_text = doc_text[:self.MAX_DOC_CHARS]
                    pairs.append([query, doc_text])
            
            if not pairs:
                return documents
            
            # 分批评分，避免大批文档导致显存溢出
            all_scores = []
            for i in range(0, len(pairs), self.BATCH_SIZE):
                batch = pairs[i:i + self.BATCH_SIZE]
                batch_scores = self.model.compute_score(batch, normalize=True)
                # 单个结果时返回标量，需转为列表
                if not isinstance(batch_scores, list):
                    batch_scores = [batch_scores]
                all_scores.extend(batch_scores)
            
            scores = all_scores

            # 更新文档分数
            for i, doc in enumerate(documents):
                if i < len(scores):
                    doc["rerank_score"] = float(scores[i])
                    doc["bge_score"] = float(scores[i])
                else:
                    doc["rerank_score"] = 0.0
                    doc["bge_score"] = 0.0
            
            # 按分数排序
            documents.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)
            
            # 返回top_k
            if top_k:
                return documents[:top_k]
            
            app_logger.info(f"BGE-Reranker重排序完成，查询: {query}, 文档数: {len(documents)}")
            return documents
            
        except Exception as e:
            app_logger.error(f"BGE-Reranker重排序失败: {e}")
            return documents


class Reranker:
    """Reranker主类 - 整合多种重排序方法"""
    
    def __init__(self, use_bge: bool = True, bge_model: str = "BAAI/bge-reranker-base"):
        """
        初始化Reranker
        
        Args:
            use_bge: 是否使用BGE-Reranker
            bge_model: BGE模型名称
        """
        self.use_bge = use_bge
        self.bge_reranker = None
        
        if use_bge:
            try:
                self.bge_reranker = BGEReranker(bge_model)
            except Exception as e:
                app_logger.warning(f"BGE-Reranker初始化失败: {e}")
                self.use_bge = False
    
    def rerank(self, query: str, documents: List[Dict[str, Any]], top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        重排序文档
        
        Args:
            query: 查询文本
            documents: 文档列表
            top_k: 返回top_k个结果
        
        Returns:
            重排序后的文档列表
        """
        if not documents:
            return []
        
        # 使用BGE-Reranker
        if self.use_bge and self.bge_reranker:
            try:
                return self.bge_reranker.rerank(query, documents, top_k)
            except Exception as e:
                app_logger.warning(f"BGE-Reranker重排序失败，使用原始顺序: {e}")
        
        # 降级：按原始分数排序
        documents.sort(key=lambda x: x.get("score", x.get("combined_score", 0.0)), reverse=True)
        
        if top_k:
            return documents[:top_k]
        
        return documents

