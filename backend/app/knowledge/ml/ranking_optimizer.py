"""排序优化器 - 使用决策树学习排序"""
from typing import Dict, Any, List, Optional
import numpy as np
from app.utils.logger import app_logger
import pickle
from pathlib import Path


class RankingOptimizer:
    """排序优化器 - 使用决策树优化排序"""
    
    def __init__(self, model_dir: str = "./models/ranking"):
        """
        初始化排序优化器
        
        Args:
            model_dir: 模型保存目录
        """
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.dtree_model = None
        self.scaler = None
        self._load_model()
    
    def _load_model(self):
        """加载训练好的模型"""
        try:
            model_path = self.model_dir / "ranking_optimizer.pkl"
            if model_path.exists():
                with open(model_path, 'rb') as f:
                    model_data = pickle.load(f)
                    self.dtree_model = model_data.get("model")
                    self.scaler = model_data.get("scaler")
                app_logger.info("排序优化模型加载成功")
        except Exception as e:
            app_logger.warning(f"排序优化模型加载失败: {e}")
    
    def extract_ranking_features(self, query: str, document: Dict[str, Any], 
                                position: int = 0) -> np.ndarray:
        """
        提取排序特征
        
        Args:
            query: 查询文本
            document: 文档字典
            position: 文档在原始列表中的位置
        
        Returns:
            特征向量
        """
        doc_text = document.get("text", "")
        
        features = []
        
        # 1. 相关性特征
        features.append(document.get("relevance_score", 0.0))
        features.append(document.get("score", 0.0))
        features.append(document.get("combined_score", 0.0))
        features.append(document.get("rrf_score", 0.0))
        features.append(document.get("bge_score", 0.0))
        features.append(document.get("ml_score", 0.0))
        
        # 2. 位置特征
        features.append(position)
        features.append(1.0 / (position + 1))  # 位置倒数
        
        # 3. 文本特征
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
        
        # 4. 长度特征
        features.append(len(query))
        features.append(len(doc_text))
        features.append(len(doc_text) / len(query) if query else 0.0)
        
        # 5. 检索方法特征
        retrieval_method = document.get("retrieval_method", "unknown")
        methods = ["vector", "bm25", "semantic", "kg"]
        for method in methods:
            features.append(1.0 if method == retrieval_method else 0.0)
        
        # 6. 元数据特征
        metadata = document.get("metadata", {})
        features.append(metadata.get("chunk_index", 0))
        
        # 7. 来源特征
        source = document.get("source", "")
        features.append(1.0 if "knowledge_graph" in source else 0.0)
        features.append(1.0 if "medical" in source.lower() else 0.0)
        
        return np.array(features, dtype=np.float32)
    
    def optimize_ranking(self, query: str, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        优化排序
        
        Args:
            query: 查询文本
            documents: 文档列表
        
        Returns:
            优化后的文档列表
        """
        if not documents:
            return []
        
        if not self.dtree_model:
            # 降级：使用综合分数排序
            return self._fallback_ranking(documents)
        
        try:
            # 提取特征
            features_list = []
            for i, doc in enumerate(documents):
                features = self.extract_ranking_features(query, doc, position=i)
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
                doc["ranking_score"] = float(scores[i])
                doc["optimized_score"] = float(scores[i])
            
            # 按排序分数排序
            documents.sort(key=lambda x: x.get("ranking_score", 0.0), reverse=True)
            
            app_logger.info(f"排序优化完成，查询: {query}, 文档数: {len(documents)}")
            return documents
            
        except Exception as e:
            app_logger.error(f"排序优化失败: {e}")
            return self._fallback_ranking(documents)
    
    def _fallback_ranking(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """降级排序方法"""
        # 使用综合分数排序
        for doc in documents:
            # 计算综合分数
            scores = [
                doc.get("relevance_score", 0.0),
                doc.get("bge_score", 0.0),
                doc.get("ml_score", 0.0),
                doc.get("rrf_score", 0.0),
                doc.get("combined_score", 0.0)
            ]
            # 取最高分
            doc["optimized_score"] = max(scores) if scores else 0.0
        
        documents.sort(key=lambda x: x.get("optimized_score", 0.0), reverse=True)
        return documents
    
    def personalize_ranking(self, query: str, documents: List[Dict[str, Any]], 
                           user_profile: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        个性化排序
        
        Args:
            query: 查询文本
            documents: 文档列表
            user_profile: 用户画像（可选）
        
        Returns:
            个性化排序后的文档列表
        """
        # 先进行基础排序优化
        documents = self.optimize_ranking(query, documents)
        
        # 如果有用户画像，进行个性化调整
        if user_profile:
            # 可以根据用户历史、偏好等进行调整
            # 这里简化处理
            pass
        
        return documents

