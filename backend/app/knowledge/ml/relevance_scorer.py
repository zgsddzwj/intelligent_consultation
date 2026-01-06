"""相关性评分器 - 使用SVM判断查询-文档相关性"""
from typing import Dict, Any, List, Optional
import numpy as np
from app.utils.logger import app_logger
import pickle
from pathlib import Path


class RelevanceScorer:
    """相关性评分器 - 判断文档与查询的相关性"""
    
    def __init__(self, model_dir: str = "./models/relevance"):
        """
        初始化相关性评分器
        
        Args:
            model_dir: 模型保存目录
        """
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.svm_model = None
        self.scaler = None
        self._load_model()
    
    def _load_model(self):
        """加载训练好的模型"""
        try:
            model_path = self.model_dir / "relevance_scorer.pkl"
            if model_path.exists():
                with open(model_path, 'rb') as f:
                    model_data = pickle.load(f)
                    self.svm_model = model_data.get("model")
                    self.scaler = model_data.get("scaler")
                app_logger.info("相关性评分模型加载成功")
        except Exception as e:
            app_logger.warning(f"相关性评分模型加载失败: {e}")
    
    def extract_features(self, query: str, document: Dict[str, Any]) -> np.ndarray:
        """
        提取相关性特征
        
        Args:
            query: 查询文本
            document: 文档字典
        
        Returns:
            特征向量
        """
        doc_text = document.get("text", "")
        
        features = []
        
        # 1. 文本相似度特征
        query_lower = query.lower()
        doc_lower = doc_text.lower()
        
        # 词汇重叠
        query_words = set(query_lower.split())
        doc_words = set(doc_lower.split())
        if query_words:
            overlap_ratio = len(query_words & doc_words) / len(query_words)
            features.append(overlap_ratio)
        else:
            features.append(0.0)
        
        # 2. 关键词匹配
        query_keywords = [w for w in query_words if len(w) > 1]
        keyword_matches = sum(1 for kw in query_keywords if kw in doc_lower)
        features.append(keyword_matches)
        features.append(keyword_matches / len(query_keywords) if query_keywords else 0.0)
        
        # 3. 长度特征
        features.append(len(query))
        features.append(len(doc_text))
        features.append(abs(len(query) - len(doc_text)))
        
        # 4. 原始分数特征
        features.append(document.get("score", 0.0))
        features.append(document.get("combined_score", 0.0))
        features.append(document.get("rrf_score", 0.0))
        
        # 5. 位置特征
        metadata = document.get("metadata", {})
        features.append(metadata.get("chunk_index", 0))
        
        # 6. 检索方法特征
        retrieval_method = document.get("retrieval_method", "unknown")
        methods = ["vector", "bm25", "semantic", "kg"]
        for method in methods:
            features.append(1.0 if method == retrieval_method else 0.0)
        
        # 7. 医疗实体匹配（简化）
        medical_terms = ["疾病", "症状", "药物", "检查", "治疗"]
        query_terms = sum(1 for term in medical_terms if term in query)
        doc_terms = sum(1 for term in medical_terms if term in doc_text)
        features.append(query_terms)
        features.append(doc_terms)
        features.append(1.0 if query_terms > 0 and doc_terms > 0 else 0.0)
        
        return np.array(features, dtype=np.float32)
    
    def score(self, query: str, document: Dict[str, Any]) -> float:
        """
        计算相关性分数
        
        Args:
            query: 查询文本
            document: 文档字典
        
        Returns:
            相关性分数 (0-1)
        """
        if not self.svm_model:
            # 降级：使用简单规则
            return self._rule_based_score(query, document)
        
        try:
            # 提取特征
            features = self.extract_features(query, document)
            features = features.reshape(1, -1)
            
            # 特征缩放
            if self.scaler:
                features = self.scaler.transform(features)
            
            # SVM预测相关性概率
            proba = self.svm_model.predict_proba(features)[0]
            relevance_score = float(proba[1])  # 正类概率
            
            return relevance_score
            
        except Exception as e:
            app_logger.warning(f"SVM相关性评分失败，使用规则评分: {e}")
            return self._rule_based_score(query, document)
    
    def _rule_based_score(self, query: str, document: Dict[str, Any]) -> float:
        """基于规则的相关性评分（备用方法）"""
        doc_text = document.get("text", "")
        query_lower = query.lower()
        doc_lower = doc_text.lower()
        
        # 词汇重叠
        query_words = set(query_lower.split())
        doc_words = set(doc_lower.split())
        if query_words:
            overlap_ratio = len(query_words & doc_words) / len(query_words)
        else:
            overlap_ratio = 0.0
        
        # 原始分数
        original_score = document.get("score", document.get("combined_score", 0.0))
        normalized_score = min(original_score, 1.0) if original_score > 0 else 0.0
        
        # 综合分数
        combined = 0.6 * overlap_ratio + 0.4 * normalized_score
        
        return float(combined)
    
    def score_batch(self, query: str, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量计算相关性分数
        
        Args:
            query: 查询文本
            documents: 文档列表
        
        Returns:
            添加了relevance_score的文档列表
        """
        for doc in documents:
            relevance_score = self.score(query, doc)
            doc["relevance_score"] = relevance_score
        
        # 按相关性分数排序
        documents.sort(key=lambda x: x.get("relevance_score", 0.0), reverse=True)
        
        return documents

