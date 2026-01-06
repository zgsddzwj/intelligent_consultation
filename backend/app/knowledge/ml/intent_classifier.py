"""意图分类器 - 使用SVM进行医疗查询意图分类"""
from typing import Dict, Any, List, Optional
import numpy as np
from app.utils.logger import app_logger
import pickle
from pathlib import Path
import re


class IntentClassifier:
    """意图分类器 - 分类医疗查询意图"""
    
    # 意图类别
    INTENT_TYPES = {
        "diagnosis": "诊断咨询",
        "medication": "用药咨询",
        "examination": "检查咨询",
        "health_management": "健康管理",
        "symptom_inquiry": "症状询问",
        "disease_info": "疾病信息",
        "general": "一般咨询"
    }
    
    def __init__(self, model_dir: str = "./models/intent"):
        """
        初始化意图分类器
        
        Args:
            model_dir: 模型保存目录
        """
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.svm_model = None
        self.vectorizer = None
        self._load_model()
    
    def _load_model(self):
        """加载训练好的模型"""
        try:
            model_path = self.model_dir / "intent_classifier.pkl"
            if model_path.exists():
                with open(model_path, 'rb') as f:
                    model_data = pickle.load(f)
                    self.svm_model = model_data.get("model")
                    self.vectorizer = model_data.get("vectorizer")
                app_logger.info("意图分类模型加载成功")
            else:
                app_logger.warning("意图分类模型文件不存在，将使用规则分类")
        except Exception as e:
            app_logger.warning(f"意图分类模型加载失败: {e}")
    
    def extract_features(self, query: str) -> np.ndarray:
        """提取特征"""
        features = []
        
        # 1. 文本长度特征
        features.append(len(query))
        features.append(len(query.split()))
        
        # 2. 关键词特征
        keywords = {
            "diagnosis": ["诊断", "是什么病", "可能", "会不会", "是不是"],
            "medication": ["用药", "药物", "药", "治疗", "服用", "剂量"],
            "examination": ["检查", "化验", "检测", "需要做什么检查"],
            "health_management": ["管理", "注意", "预防", "保健", "生活方式"],
            "symptom_inquiry": ["症状", "表现", "有什么症状", "会怎样"],
            "disease_info": ["什么是", "介绍", "了解", "信息"]
        }
        
        query_lower = query.lower()
        for intent, words in keywords.items():
            count = sum(1 for word in words if word in query_lower)
            features.append(count)
        
        # 3. 问句类型特征
        question_words = ["什么", "怎么", "为什么", "如何", "是否", "会不会"]
        question_count = sum(1 for word in question_words if word in query)
        features.append(question_count)
        
        # 4. 医疗实体特征（简化）
        medical_terms = ["疾病", "症状", "药物", "检查", "治疗", "诊断"]
        medical_count = sum(1 for term in medical_terms if term in query)
        features.append(medical_count)
        
        return np.array(features, dtype=np.float32)
    
    def classify_with_rules(self, query: str) -> Dict[str, Any]:
        """基于规则的意图分类（备用方法）"""
        query_lower = query.lower()
        
        # 诊断相关
        if any(word in query_lower for word in ["是什么病", "可能", "会不会", "是不是", "诊断"]):
            return {
                "intent": "diagnosis",
                "intent_name": self.INTENT_TYPES["diagnosis"],
                "confidence": 0.8
            }
        
        # 用药相关
        if any(word in query_lower for word in ["用药", "药物", "药", "服用", "剂量", "怎么吃"]):
            return {
                "intent": "medication",
                "intent_name": self.INTENT_TYPES["medication"],
                "confidence": 0.8
            }
        
        # 检查相关
        if any(word in query_lower for word in ["检查", "化验", "检测", "需要做什么"]):
            return {
                "intent": "examination",
                "intent_name": self.INTENT_TYPES["examination"],
                "confidence": 0.8
            }
        
        # 健康管理
        if any(word in query_lower for word in ["管理", "注意", "预防", "保健", "生活方式"]):
            return {
                "intent": "health_management",
                "intent_name": self.INTENT_TYPES["health_management"],
                "confidence": 0.8
            }
        
        # 症状询问
        if any(word in query_lower for word in ["症状", "表现", "会怎样", "有什么症状"]):
            return {
                "intent": "symptom_inquiry",
                "intent_name": self.INTENT_TYPES["symptom_inquiry"],
                "confidence": 0.8
            }
        
        # 疾病信息
        if any(word in query_lower for word in ["什么是", "介绍", "了解", "信息"]):
            return {
                "intent": "disease_info",
                "intent_name": self.INTENT_TYPES["disease_info"],
                "confidence": 0.8
            }
        
        # 默认
        return {
            "intent": "general",
            "intent_name": self.INTENT_TYPES["general"],
            "confidence": 0.5
        }
    
    def classify(self, query: str) -> Dict[str, Any]:
        """
        分类查询意图
        
        Args:
            query: 查询文本
        
        Returns:
            意图分类结果
        """
        if not query:
            return {
                "intent": "general",
                "intent_name": self.INTENT_TYPES["general"],
                "confidence": 0.0
            }
        
        # 如果模型已加载，使用模型分类
        if self.svm_model and self.vectorizer:
            try:
                # 提取特征
                features = self.extract_features(query)
                features = features.reshape(1, -1)
                
                # 预测
                intent_idx = self.svm_model.predict(features)[0]
                intent_proba = self.svm_model.predict_proba(features)[0]
                
                intent_names = list(self.INTENT_TYPES.keys())
                if intent_idx < len(intent_names):
                    intent = intent_names[intent_idx]
                    confidence = float(intent_proba[intent_idx])
                    
                    return {
                        "intent": intent,
                        "intent_name": self.INTENT_TYPES.get(intent, "未知"),
                        "confidence": confidence,
                        "all_probas": {
                            intent_names[i]: float(intent_proba[i]) 
                            for i in range(len(intent_names))
                        }
                    }
            except Exception as e:
                app_logger.warning(f"SVM意图分类失败，使用规则分类: {e}")
        
        # 降级到规则分类
        return self.classify_with_rules(query)

