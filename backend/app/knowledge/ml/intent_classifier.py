"""意图分类器 - 使用SVM进行医疗查询意图分类"""
from typing import Dict, Any, List, Optional
import numpy as np
from app.utils.logger import app_logger
import pickle
from pathlib import Path


class IntentClassifier:
    """意图分类器 - 分类医疗查询意图

    SVM路径必须与 scripts/ml/train_ml_models.py 的训练管线保持一致：
    特征提取复刻训练侧 extract_text_features（15维统计特征），
    标签映射使用训练时保存的 label_encoder / intent_names。
    """

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

    # 规则分类关键词（预编译为frozenset，避免每次调用重新创建列表）
    RULE_KEYWORDS = {
        "diagnosis": frozenset({"是什么病", "可能", "会不会", "是不是", "诊断"}),
        "medication": frozenset({"用药", "药物", "药", "服用", "剂量", "怎么吃"}),
        "examination": frozenset({"检查", "化验", "检测", "需要做什么"}),
        "health_management": frozenset({"管理", "注意", "预防", "保健", "生活方式"}),
        "symptom_inquiry": frozenset({"症状", "表现", "会怎样", "有什么症状"}),
        "disease_info": frozenset({"什么是", "介绍", "了解", "信息"}),
    }

    # 规则匹配优先级顺序（先匹配的优先级高）
    RULE_PRIORITY = (
        "diagnosis",
        "medication",
        "examination",
        "health_management",
        "symptom_inquiry",
        "disease_info",
    )

    # 医疗关键词（必须与 scripts/ml/train_ml_models.py 的 MEDICAL_KEYWORDS 保持一致）
    MEDICAL_KEYWORDS = {
        "symptoms": ["头痛", "头晕", "发热", "咳嗽", "腹痛", "恶心", "呕吐", "胸闷", "气短",
                     "乏力", "失眠", "食欲不振", "体重下降", "水肿", "皮疹"],
        "diseases": ["高血压", "糖尿病", "心脏病", "感冒", "肺炎", "胃炎", "肝炎", "肾炎",
                     "关节炎", "哮喘", "癌症", "中风", "抑郁症", "焦虑症"],
        "medications": ["阿司匹林", "胰岛素", "降压药", "抗生素", "止痛药", "维生素", "中药",
                        "降压片", "降糖药", "消炎药"],
        "examinations": ["血常规", "尿常规", "CT", "MRI", "B超", "心电图", "X光", "胃镜",
                         "肝功能", "肾功能", "血脂", "血糖"],
        "lifestyle": ["饮食", "运动", "睡眠", "戒烟", "限酒", "减压", "作息", "锻炼"],
    }

    def __init__(self, model_dir: str = "./models/intent"):
        """
        初始化意图分类器

        Args:
            model_dir: 模型保存目录
        """
        self.model_dir = Path(model_dir)
        self.svm_model = None
        self.label_encoder = None
        self.intent_names: List[str] = []
        self._load_model()

    def _load_model(self):
        """加载训练好的模型（训练产物含 label_encoder 与 intent_names，无 vectorizer）"""
        try:
            model_path = self.model_dir / "intent_classifier.pkl"
            if model_path.exists():
                with open(model_path, 'rb') as f:
                    model_data = pickle.load(f)
                    self.svm_model = model_data.get("model")
                    self.label_encoder = model_data.get("label_encoder")
                    self.intent_names = model_data.get("intent_names") or []
                if self.svm_model is not None:
                    app_logger.info("意图分类模型加载成功")
                    return
            app_logger.warning("意图分类模型文件不存在，将使用规则分类")
        except Exception as e:
            app_logger.warning(f"意图分类模型加载失败: {e}")
        self.svm_model = None

    def extract_features(self, query: str) -> np.ndarray:
        """提取统计特征（严格复刻训练侧 extract_text_features，维度与语义必须一致）"""
        text = query
        text_lower = text.lower()
        features = []

        # 1. 文本长度特征
        features.append(len(text))
        features.append(len(text.split()))

        # 2. 医疗关键词匹配特征（每类：命中数 + 密度）
        for category, keywords in self.MEDICAL_KEYWORDS.items():
            match_count = sum(1 for kw in keywords if kw in text)
            features.append(match_count)
            features.append(match_count / max(len(text), 1))

        # 3. 问句模式特征
        question_patterns = ["什么", "怎么", "如何", "为什么", "哪", "是否", "能否", "可以吗"]
        features.append(sum(1 for p in question_patterns if p in text))

        # 4. 紧急程度特征
        urgent_words = ["紧急", "严重", "疼痛", "难忍", "出血", "昏迷", "高烧", "呼吸困难"]
        features.append(sum(1 for w in urgent_words if w in text))

        # 5. 否定词特征
        negation_words = ["不", "没", "无", "否", "不是", "没有"]
        features.append(sum(1 for w in negation_words if w in text_lower))

        return np.array(features, dtype=np.float64)

    def classify_with_rules(self, query: str) -> Dict[str, Any]:
        """基于规则的意图分类（使用预编译关键词集合优化）"""
        query_lower = query.lower()

        for intent in self.RULE_PRIORITY:
            keywords = self.RULE_KEYWORDS[intent]
            # 遍历关键词检查是否存在于查询中
            for word in keywords:
                if word in query_lower:
                    return {
                        "intent": intent,
                        "intent_name": self.INTENT_TYPES[intent],
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

        # 模型已加载时使用模型分类（特征空间与训练一致）
        if self.svm_model is not None:
            try:
                features = self.extract_features(query).reshape(1, -1)

                intent_idx = int(self.svm_model.predict(features)[0])
                proba = self.svm_model.predict_proba(features)[0]

                # 通过训练保存的 intent_names 映射标签（classes_顺序与proba列对齐）
                classes = list(self.svm_model.classes_)
                intent = (
                    self.intent_names[intent_idx]
                    if intent_idx < len(self.intent_names)
                    else str(classes[intent_idx])
                )
                confidence = float(proba[list(classes).index(intent_idx)])

                return {
                    "intent": intent,
                    "intent_name": self.INTENT_TYPES.get(intent, "未知"),
                    "confidence": confidence,
                    "all_probas": {
                        self.intent_names[c] if c < len(self.intent_names) else str(c): float(p)
                        for c, p in zip(classes, proba)
                    },
                }
            except Exception as e:
                app_logger.warning(f"SVM意图分类失败，使用规则分类: {e}")

        # 降级到规则分类
        return self.classify_with_rules(query)
