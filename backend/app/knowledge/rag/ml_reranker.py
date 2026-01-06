"""ML重排序器 - 使用SVM和决策树进行重排序"""
from typing import List, Dict, Any, Optional
import numpy as np
from app.utils.logger import app_logger
import pickle
import os
from pathlib import Path


class MLReranker:
    """ML重排序器 - 使用SVM和决策树"""
    
    def __init__(self, model_dir: str = "./models/reranker"):
        """
        初始化ML重排序器
        
        Args:
            model_dir: 模型保存目录
        """
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.svm_model = None
        self.dtree_model = None
        self.scaler = None
        self._load_models()
    
    def _load_models(self):
        """加载训练好的模型"""
        try:
            # 加载SVM模型
            svm_path = self.model_dir / "svm_reranker.pkl"
            if svm_path.exists():
                with open(svm_path, 'rb') as f:
                    self.svm_model = pickle.load(f)
                app_logger.info("SVM重排序模型加载成功")
            
            # 加载决策树模型
            dtree_path = self.model_dir / "dtree_reranker.pkl"
            if dtree_path.exists():
                with open(dtree_path, 'rb') as f:
                    self.dtree_model = pickle.load(f)
                app_logger.info("决策树重排序模型加载成功")
            
            # 加载特征缩放器
            scaler_path = self.model_dir / "scaler.pkl"
            if scaler_path.exists():
                with open(scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                app_logger.info("特征缩放器加载成功")
                
        except Exception as e:
            app_logger.warning(f"ML模型加载失败: {e}")
    
    def extract_features(self, query: str, document: Dict[str, Any]) -> np.ndarray:
        """
        提取特征
        
        Args:
            query: 查询文本
            document: 文档字典，包含text等字段
        
        Returns:
            特征向量
        """
        doc_text = document.get("text", "")
        
        features = []
        
        # 1. 文本长度特征
        features.append(len(query))
        features.append(len(doc_text))
        features.append(abs(len(query) - len(doc_text)))
        
        # 2. 词汇重叠特征
        query_words = set(query.lower().split())
        doc_words = set(doc_text.lower().split())
        if query_words:
            overlap_ratio = len(query_words & doc_words) / len(query_words)
            features.append(overlap_ratio)
        else:
            features.append(0.0)
        
        # 3. 原始分数特征
        features.append(document.get("score", 0.0))
        features.append(document.get("combined_score", 0.0))
        features.append(document.get("rrf_score", 0.0))
        
        # 4. 检索方法特征（one-hot编码）
        retrieval_method = document.get("retrieval_method", "unknown")
        methods = ["vector", "bm25", "semantic", "kg", "unknown"]
        for method in methods:
            features.append(1.0 if method == retrieval_method else 0.0)
        
        # 5. 关键词匹配特征
        query_lower = query.lower()
        doc_lower = doc_text.lower()
        keyword_matches = sum(1 for word in query_lower.split() if word in doc_lower)
        features.append(keyword_matches)
        features.append(keyword_matches / len(query.split()) if query.split() else 0.0)
        
        # 6. 位置特征（如果文档有位置信息）
        metadata = document.get("metadata", {})
        features.append(metadata.get("chunk_index", 0))
        
        return np.array(features, dtype=np.float32)
    
    def rerank_with_svm(self, query: str, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """使用SVM进行重排序"""
        if not self.svm_model:
            return documents
        
        try:
            # 提取特征
            features_list = []
            for doc in documents:
                features = self.extract_features(query, doc)
                features_list.append(features)
            
            if not features_list:
                return documents
            
            X = np.array(features_list)
            
            # 特征缩放
            if self.scaler:
                X = self.scaler.transform(X)
            
            # SVM预测相关性分数
            scores = self.svm_model.predict_proba(X)[:, 1]  # 获取正类概率
            
            # 更新文档分数
            for i, doc in enumerate(documents):
                doc["svm_score"] = float(scores[i])
                doc["ml_score"] = float(scores[i])
            
            # 按SVM分数排序
            documents.sort(key=lambda x: x.get("svm_score", 0.0), reverse=True)
            
            app_logger.info(f"SVM重排序完成，查询: {query}, 文档数: {len(documents)}")
            return documents
            
        except Exception as e:
            app_logger.error(f"SVM重排序失败: {e}")
            return documents
    
    def rerank_with_dtree(self, query: str, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """使用决策树进行重排序"""
        if not self.dtree_model:
            return documents
        
        try:
            # 提取特征
            features_list = []
            for doc in documents:
                features = self.extract_features(query, doc)
                features_list.append(features)
            
            if not features_list:
                return documents
            
            X = np.array(features_list)
            
            # 特征缩放
            if self.scaler:
                X = self.scaler.transform(X)
            
            # 决策树预测排序分数
            scores = self.dtree_model.predict(X)
            
            # 更新文档分数
            for i, doc in enumerate(documents):
                doc["dtree_score"] = float(scores[i])
                if "ml_score" not in doc:
                    doc["ml_score"] = float(scores[i])
                else:
                    # 融合SVM和决策树分数
                    doc["ml_score"] = (doc.get("svm_score", 0.0) + float(scores[i])) / 2.0
            
            # 按决策树分数排序
            documents.sort(key=lambda x: x.get("dtree_score", 0.0), reverse=True)
            
            app_logger.info(f"决策树重排序完成，查询: {query}, 文档数: {len(documents)}")
            return documents
            
        except Exception as e:
            app_logger.error(f"决策树重排序失败: {e}")
            return documents
    
    def rerank(self, query: str, documents: List[Dict[str, Any]], 
               use_svm: bool = True, use_dtree: bool = True,
               top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        使用ML模型进行重排序
        
        Args:
            query: 查询文本
            documents: 文档列表
            use_svm: 是否使用SVM
            use_dtree: 是否使用决策树
            top_k: 返回top_k个结果
        
        Returns:
            重排序后的文档列表
        """
        if not documents:
            return []
        
        # 使用SVM
        if use_svm and self.svm_model:
            documents = self.rerank_with_svm(query, documents)
        
        # 使用决策树
        if use_dtree and self.dtree_model:
            documents = self.rerank_with_dtree(query, documents)
        
        # 如果两个模型都使用了，按融合分数排序
        if use_svm and use_dtree and self.svm_model and self.dtree_model:
            documents.sort(key=lambda x: x.get("ml_score", 0.0), reverse=True)
        
        # 返回top_k
        if top_k:
            return documents[:top_k]
        
        return documents

