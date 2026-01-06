"""Reranker - BGE-Reranker模型集成"""
from typing import List, Dict, Any, Optional
from app.utils.logger import app_logger
import os


class BGEReranker:
    """BGE-Reranker - 使用FlagEmbedding的BGE-Reranker模型"""
    
    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        """
        初始化BGE-Reranker
        
        Args:
            model_name: 模型名称，默认使用BGE-Reranker-Base
        """
        self.model_name = model_name
        self.model = None
        self.tokenizer = None
        self._load_model()
    
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
            # 构建查询-文档对
            pairs = []
            for doc in documents:
                doc_text = doc.get("text", "")
                if doc_text:
                    pairs.append([query, doc_text])
            
            if not pairs:
                return documents
            
            # 批量评分
            scores = self.model.compute_score(pairs, normalize=True)
            
            # 如果是单个分数，转换为列表
            if not isinstance(scores, list):
                scores = [scores]
            
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

