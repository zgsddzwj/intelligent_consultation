"""查询理解器 - 使用决策树进行查询分析和实体提取"""
from typing import Dict, Any, List, Optional
import numpy as np
from app.utils.logger import app_logger
import pickle
from pathlib import Path
import re
import jieba
import jieba.analyse


class QueryUnderstanding:
    """查询理解器 - 分析查询，提取实体和关键词"""
    
    def __init__(self, model_dir: str = "./models/query"):
        """
        初始化查询理解器
        
        Args:
            model_dir: 模型保存目录
        """
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.dtree_model = None
        self._load_model()
    
    def _load_model(self):
        """加载训练好的模型"""
        try:
            model_path = self.model_dir / "query_understanding.pkl"
            if model_path.exists():
                with open(model_path, 'rb') as f:
                    self.dtree_model = pickle.load(f)
                app_logger.info("查询理解模型加载成功")
        except Exception as e:
            app_logger.warning(f"查询理解模型加载失败: {e}")
    
    def extract_entities(self, query: str) -> Dict[str, List[str]]:
        """
        提取实体
        
        Args:
            query: 查询文本
        
        Returns:
            实体字典
        """
        entities = {
            "diseases": [],
            "symptoms": [],
            "drugs": [],
            "examinations": [],
            "keywords": []
        }
        
        # 使用jieba提取关键词
        keywords = jieba.analyse.extract_tags(query, topK=10, withWeight=False)
        entities["keywords"] = keywords
        
        # 简单的实体识别（可以改进为NER模型）
        # 疾病关键词
        disease_keywords = ["高血压", "糖尿病", "心脏病", "癌症", "肿瘤", "炎症", "感染"]
        for keyword in disease_keywords:
            if keyword in query:
                entities["diseases"].append(keyword)
        
        # 症状关键词
        symptom_keywords = ["头痛", "发热", "咳嗽", "疼痛", "乏力", "头晕"]
        for keyword in symptom_keywords:
            if keyword in query:
                entities["symptoms"].append(keyword)
        
        # 药物关键词
        drug_keywords = ["药", "药物", "治疗", "用药"]
        for keyword in drug_keywords:
            if keyword in query:
                entities["drugs"].append(keyword)
        
        # 检查关键词
        exam_keywords = ["检查", "化验", "检测", "CT", "MRI", "X光"]
        for keyword in exam_keywords:
            if keyword in query:
                entities["examinations"].append(keyword)
        
        return entities
    
    def extract_keywords(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        提取关键词并评分
        
        Args:
            query: 查询文本
            top_k: 返回top_k个关键词
        
        Returns:
            关键词列表，包含关键词和重要性分数
        """
        # 使用TF-IDF提取关键词
        keywords_with_weight = jieba.analyse.extract_tags(
            query, topK=top_k, withWeight=True
        )
        
        keywords = []
        for keyword, weight in keywords_with_weight:
            keywords.append({
                "keyword": keyword,
                "importance": float(weight),
                "length": len(keyword)
            })
        
        return keywords
    
    def analyze_query_type(self, query: str) -> Dict[str, Any]:
        """
        分析查询类型
        
        Args:
            query: 查询文本
        
        Returns:
            查询类型分析结果
        """
        query_lower = query.lower()
        
        # 问句类型
        question_types = {
            "what": "什么" in query or "哪些" in query,
            "how": "怎么" in query or "如何" in query,
            "why": "为什么" in query or "原因" in query,
            "whether": "是否" in query or "会不会" in query or "是不是" in query
        }
        
        # 查询复杂度
        word_count = len(query.split())
        complexity = "simple" if word_count < 10 else "complex"
        
        # 医疗领域
        medical_domain = "general"
        if any(word in query for word in ["疾病", "症状", "诊断"]):
            medical_domain = "diagnosis"
        elif any(word in query for word in ["药物", "用药", "治疗"]):
            medical_domain = "medication"
        elif any(word in query for word in ["检查", "化验"]):
            medical_domain = "examination"
        
        return {
            "question_types": question_types,
            "complexity": complexity,
            "word_count": word_count,
            "medical_domain": medical_domain
        }
    
    def understand(self, query: str) -> Dict[str, Any]:
        """
        理解查询
        
        Args:
            query: 查询文本
        
        Returns:
            查询理解结果
        """
        # 提取实体
        entities = self.extract_entities(query)
        
        # 提取关键词
        keywords = self.extract_keywords(query)
        
        # 分析查询类型
        query_type = self.analyze_query_type(query)
        
        return {
            "query": query,
            "entities": entities,
            "keywords": keywords,
            "query_type": query_type,
            "main_keywords": [kw["keyword"] for kw in keywords[:5]]
        }
    
    def get_query_features(self, query: str) -> np.ndarray:
        """
        获取查询特征（用于决策树模型）
        
        Args:
            query: 查询文本
        
        Returns:
            特征向量
        """
        features = []
        
        # 1. 长度特征
        features.append(len(query))
        features.append(len(query.split()))
        
        # 2. 问句类型特征
        question_words = ["什么", "怎么", "为什么", "如何", "是否"]
        question_count = sum(1 for word in question_words if word in query)
        features.append(question_count)
        
        # 3. 医疗实体特征
        medical_terms = ["疾病", "症状", "药物", "检查", "治疗"]
        medical_count = sum(1 for term in medical_terms if term in query)
        features.append(medical_count)
        
        # 4. 关键词重要性
        keywords = self.extract_keywords(query, top_k=5)
        if keywords:
            avg_importance = sum(kw["importance"] for kw in keywords) / len(keywords)
            features.append(avg_importance)
        else:
            features.append(0.0)
        
        return np.array(features, dtype=np.float32)

