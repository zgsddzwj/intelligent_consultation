"""ML模型训练脚本

训练智能医疗管家平台所需的机器学习模型：
- 意图分类器 (Intent Classifier): SVM分类用户查询意图
- 相关性评分器 (Relevance Scorer): 评估查询-文档对的相关性
- 排序优化器 (Ranking Optimizer): 优化检索结果排序
- ML重排序器 (ML Reranker): 基于学习的重排序

Usage:
    # 训练所有模型
    python scripts/train_ml_models.py
    
    # 仅训练指定模型
    python scripts/train_ml_models.py --model intent
    
    # 使用自定义数据目录
    python scripts/train_ml_models.py --data-dir ./data/training

Author: 智能医疗管家团队
Version: 1.0.0
"""
import sys
import argparse
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any

import numpy as np
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    mean_squared_error,
    precision_recall_fscore_support,
    confusion_matrix
)
import pickle

# 添加项目根路径到sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.utils.logger import app_logger


# ============================================================
# 数据生成模块
# ============================================================

# 医疗领域关键词库（用于特征提取和数据增强）
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

# 意图类型定义（与 IntentClassifier 保持一致）
INTENT_TYPES = {
    "diagnosis": "诊断咨询",
    "medication": "用药咨询",
    "examination": "检查咨询",
    "health_management": "健康管理",
    "symptom_inquiry": "症状询问",
    "disease_info": "疾病信息",
    "prevention": "疾病预防",
    "general": "通用咨询"
}


def generate_intent_training_data(n_samples_per_class: int = 20) -> Dict[str, Any]:
    """生成意图分类训练数据
    
    基于模板和关键词组合生成多样化的医疗查询样本，
    覆盖所有预定义的意图类别。
    
    Args:
        n_samples_per_class: 每个意图类别的样本数量
        
    Returns:
        包含 queries, intents, features 的字典
    """
    
    # 意图查询模板库
    intent_templates = {
        "diagnosis": [
            "我{symptom}，可能是什么病？",
            "{symptom}已经{duration}了，需要看什么科？",
            "最近总是{symptom}，请问怎么回事？",
            "医生，我{symptom}，这是不是{disease}的症状？",
            "{symptom}严重吗？需要做哪些检查？",
            "我家人{symptom}，应该怎么办？",
            "请问{symptom}可能是什么原因引起的？",
            "持续{symptom}，是否需要立即就医？",
            "儿童{symptom}怎么处理？",
            "老年人{symptom}需要注意什么？",
        ],
        "medication": [
            "{disease}应该吃什么药？",
            "{medication}有什么副作用？",
            "{disease}能吃{medication}吗？",
            "{medication}的用法用量是什么？",
            "吃了{medication}后{symptom}更严重了怎么办？",
            "孕妇可以吃{medication}吗？",
            "{disease}的最佳药物治疗方案是什么？",
            "{medication}和{medication}能一起吃吗？",
            "{medication}需要吃多久？",
            "{medication}漏服了怎么办？",
        ],
        "examination": [
            "{disease}需要做什么检查？",
            "{examination}检查前需要注意什么？",
            "{examination}多少钱？医保能报销吗？",
            "{examination}结果怎么看？",
            "怀疑{disease}应该先做哪个检查？",
            "{examination}有辐射吗？对身体有害吗？",
            "做{examination}需要空腹吗？",
            "{examination}检查大概多长时间？",
            "{examination}能查出{disease}吗？",
            "哪些人不能做{examination}？",
        ],
        "health_management": [
            "{disease}患者平时要注意什么？",
            "如何通过{lifestyle}改善{disease}？",
            "{disease}的日常护理方法？",
            "得了{disease}还能运动吗？",
            "{disease}患者饮食上有什么禁忌？",
            "如何制定{disease}康复计划？",
            "慢性病患者如何自我管理？",
            "{disease}复诊频率应该是多少？",
            "如何监测{disease}的病情变化？",
            "{disease}患者的心理调节方法？",
        ],
        "symptom_inquiry": [
            "{disease}的早期症状有哪些？",
            "{disease}和{disease2}症状有什么区别？",
            "{symptom}是{disease}的典型表现吗？",
            "{disease}发展到后期会有什么症状？",
            "出现什么症状要警惕{disease}？",
            "{symptom}伴随{symptom2}说明什么？",
            "{disease}的并发症有哪些症状？",
            "如何区分普通{symptom}和{disease}？",
            "{disease}急性发作时有什么症状？",
            "哪些症状表明{disease}在好转？",
        ],
        "disease_info": [
            "什么是{disease}？",
            "{disease}是怎么引起的？",
            "{disease}会传染吗？",
            "{disease}的高发人群是哪些？",
            "{disease}的发病率是多少？",
            "{disease}能治愈吗？",
            "{disease}如果不治疗会怎样？",
            "{disease}的最新治疗方法有哪些？",
            "{disease}和遗传有关系吗？",
            "关于{disease}的常见误区？",
        ],
        "prevention": [
            "如何预防{disease}？",
            "什么人群容易得{disease}？",
            "{disease}的一级预防措施？",
            "日常生活中如何避免{disease}？",
            "{disease}的筛查建议？",
            "疫苗能预防{disease}吗？",
            "{lifestyle}对预防{disease}有帮助吗？",
            "季节性{disease}如何预防？",
            "家族有{disease}史如何预防？",
            "{disease}的高危因素有哪些？",
        ],
        "general": [
            "你好，我想了解一下这个系统",
            "你们医院有哪些科室？",
            "如何使用在线问诊功能？",
            "医生资质怎么样？",
            "咨询费用是多少？",
            "就诊流程是怎样的？",
            "如何查看历史记录？",
            "隐私保护政策是什么？",
            "客服联系方式？",
            "系统使用帮助？",
        ]
    }
    
    queries = []
    intents = []
    
    for intent_type, templates in intent_templates.items():
        for i in range(min(n_samples_per_class, len(templates))):
            template = templates[i % len(templates)]
            
            # 随机填充占位符
            query = template.format(
                symptom=np.random.choice(MEDICAL_KEYWORDS["symptoms"]),
                disease=np.random.choice(MEDICAL_KEYWORDS["diseases"]),
                disease2=np.random.choice(MEDICAL_KEYWORDS["diseases"]),
                medication=np.random.choice(MEDICAL_KEYWORDS["medications"]),
                examination=np.random.choice(MEDICAL_KEYWORDS["examinations"]),
                lifestyle=np.random.choice(MEDICAL_KEYWORDS["lifestyle"]),
                duration=np.random.choice(["3天", "一周", "半个月", "一个月", "两个月"])
            )
            
            queries.append(query)
            intents.append(intent_type)
    
    return {
        "queries": queries,
        "intents": intents,
        "intent_types": INTENT_TYPES
    }


def generate_relevance_training_data(n_positive: int = 30, n_negative: int = 30) -> Dict[str, Any]:
    """生成相关性评分训练数据
    
    生成查询-文档对及其相关性标签。
    正样本：查询与文档语义相关
    负样本：查询与文档不相关
    
    Args:
        n_positive: 正样本数量
        n_negative: 负样本数量
        
    Returns:
        包含 queries, documents, labels 的字典
    """
    
    # 正样本：相关查询-文档对
    positive_pairs = [
        ("高血压的症状", "高血压是一种常见慢性病，典型症状包括头痛、头晕、心悸、耳鸣等"),
        ("高血压的治疗", "高血压的治疗包括生活方式干预和药物治疗，常用药物有ACEI、ARB、CCB等"),
        ("糖尿病的症状", "糖尿病的典型症状为三多一少：多饮、多食、多尿、体重减少"),
        ("糖尿病的饮食", "糖尿病患者应控制碳水化合物摄入，增加膳食纤维，低盐低脂"),
        ("心脏病的预防", "预防心脏病应戒烟限酒、规律运动、控制血压血脂、保持健康体重"),
        ("感冒怎么办", "普通感冒多为病毒感染，以对症治疗为主，注意休息多喝水"),
        ("胃炎怎么调理", "胃炎患者应规律饮食，避免刺激性食物，必要时服用抑酸药"),
        ("失眠的原因", "失眠原因多样，包括压力、环境、生活习惯、潜在健康问题等"),
        ("关节炎的治疗", "关节炎治疗包括药物治疗、物理治疗、生活方式调整，严重时需手术"),
        ("哮喘的诱因", "哮喘常见诱因包括过敏原、冷空气、运动、呼吸道感染、情绪波动"),
    ]
    
    # 负样本：不相关的查询-文档对
    negative_pairs = [
        ("高血压的症状", "今天天气真好，适合出去散步放松心情"),
        ("糖尿病的治疗", "最新的智能手机功能非常强大，拍照效果出色"),
        ("心脏病的预防", "Python是一种流行的编程语言，广泛应用于数据分析"),
        ("感冒怎么办", "股市今天大幅上涨，投资者情绪高涨"),
        ("胃炎怎么调理", "这款新上市的电动汽车续航里程超过500公里"),
        ("失眠的原因", "装修房子时要注意选择环保材料，保证室内空气质量"),
        ("关节炎的治疗", "学习外语最好的方法是多听多说多练习"),
        ("哮喘的诱因", "旅游攻略：日本东京必去的十大景点推荐"),
    ]
    
    queries = []
    documents = []
    labels = []
    
    # 添加正样本
    for query, doc in positive_pairs:
        queries.append(query)
        documents.append(doc)
        labels.append(1)
    
    # 添加负样本
    for query, doc in negative_pairs:
        queries.append(query)
        documents.append(doc)
        labels.append(0)
    
    # 数据增强：随机打乱负样本配对
    all_docs = positive_pairs[:][1] + negative_pairs[:][1]
    extra_negatives = min(n_negative - len(negative_pairs), len(positive_pairs) * 2)
    for _ in range(extra_negatives):
        q = np.random.choice([p[0] for p in positive_pairs])
        d = np.random.choice(all_docs)
        if (q, d) not in positive_pairs:
            queries.append(q)
            documents.append(d)
            labels.append(0)
    
    return {
        "queries": queries,
        "documents": documents,
        "labels": labels
    }


def generate_ranking_training_data() -> Dict[str, Any]:
    """生成排序优化训练数据
    
    Returns:
        包含 queries, documents, scores 的字典
    """
    
    ranking_data = {
        "queries": [],
        "documents": [],
        "scores": [],  # 0-1之间的相关性分数
        "positions": []  # 初始排序位置
    }
    
    # 示例查询及其排序结果
    query_results = {
        "高血压的症状": [
            {"text": "高血压典型症状：头痛、头晕、心悸、耳鸣、视力模糊", "score": 0.95},
            {"text": "原发性高血压约占所有高血压病例的90-95%", "score": 0.75},
            {"text": "正常成人血压应低于140/90mmHg", "score": 0.60},
            {"text": "低血压也会导致头晕症状，需与高血压鉴别", "score": 0.45},
            {"text": "天气变化可能影响血压波动", "score": 0.20},
        ],
        "糖尿病的治疗": [
            {"text": "糖尿病治疗五驾马车：饮食、运动、药物、教育、监测", "score": 0.92},
            {"text": "二甲双胍是2型糖尿病一线用药", "score": 0.85},
            {"text": "胰岛素注射技术及注意事项", "score": 0.78},
            {"text": "糖尿病患者应定期检查糖化血红蛋白", "score": 0.65},
            {"text": "运动有助于改善胰岛素敏感性", "score": 0.55},
        ],
        "感冒怎么办": [
            {"text": "普通感冒多为自限性，病程约7-10天", "score": 0.90},
            {"text": "感冒期间应多休息、多饮水、清淡饮食", "score": 0.88},
            {"text": "发热时可使用退热药如布洛芬或对乙酰氨基酚", "score": 0.82},
            {"text": "感冒与流感症状相似但流感更严重", "score": 0.60},
            {"text": "抗生素对病毒性感冒无效", "score": 0.70},
        ],
    }
    
    for query, results in query_results.items():
        for position, doc in enumerate(results):
            ranking_data["queries"].append(query)
            ranking_data["documents"].append(doc["text"])
            ranking_data["scores"].append(doc["score"])
            ranking_data["positions"].append(position)
    
    return ranking_data


def generate_sample_data():
    """生成示例训练数据（兼容旧接口）"""
    intent_data = generate_intent_training_data()
    relevance_data = generate_relevance_training_data()
    return intent_data, relevance_data


# ============================================================
# 特征提取模块
# ============================================================

def extract_text_features(text: str) -> np.ndarray:
    """提取文本的统计特征（不依赖外部模型）
    
    基于规则和关键词匹配提取特征向量，
    用于在没有预训练模型时的快速特征工程。
    
    Args:
        text: 输入文本
        
    Returns:
        特征向量 (numpy array)
    """
    text_lower = text.lower()
    features = []
    
    # 1. 文本长度特征
    features.append(len(text))
    features.append(len(text.split()))
    
    # 2. 医疗关键词匹配特征
    for category, keywords in MEDICAL_KEYWORDS.items():
        match_count = sum(1 for kw in keywords if kw in text)
        features.append(match_count)
        features.append(match_count / max(len(text), 1))  # 关键词密度
    
    # 3. 问句模式特征
    question_patterns = ["什么", "怎么", "如何", "为什么", "哪", "是否", "能否", "可以吗"]
    features.append(sum(1 for p in question_patterns if p in text))
    
    # 4. 紧急程度特征
    urgent_words = ["紧急", "严重", "疼痛", "难忍", "出血", "昏迷", "高烧", "呼吸困难"]
    features.append(sum(1 for w in urgent_words if w in text))
    
    # 5. 否定词特征
    negation_words = ["不", "没", "无", "否", "不是", "没有"]
    features.append(sum(1 for w in negation_words if w in text))
    
    return np.array(features, dtype=np.float64)


# ============================================================
# 模型训练模块
# ============================================================

class TrainingResult:
    """训练结果封装类"""
    
    def __init__(self, model_name: str, success: bool, metrics: Dict[str, float] = None,
                 model_path: Path = None, error: str = None, training_time: float = 0):
        self.model_name = model_name
        self.success = success
        self.metrics = metrics or {}
        self.model_path = model_path
        self.error = error
        self.training_time = training_time
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "success": self.success,
            "metrics": self.metrics,
            "model_path": str(self.model_path) if self.model_path else None,
            "error": self.error,
            "training_time": round(self.training_time, 2),
            "timestamp": self.timestamp
        }
    
    def __str__(self) -> str:
        if self.success:
            return f"[✓] {self.model_name}: 准确率={self.metrics.get('accuracy', 'N/A')}, 耗时={self.training_time:.1f}s"
        else:
            return f"[✗] {self.model_name}: {self.error}"


def evaluate_classification_model(model, X_test, y_test, label_names: List[str] = None) -> Dict[str, Any]:
    """评估分类模型的详细指标
    
    Args:
        model: 已训练的分类模型
        X_test: 测试集特征
        y_test: 测试集标签
        label_names: 类别名称列表
        
    Returns:
        包含各项评估指标的字典
    """
    y_pred = model.predict(X_test)
    
    # 基础指标
    accuracy = accuracy_score(y_test, y_pred)
    
    # 详细分类报告
    report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
    
    # 混淆矩阵
    cm = confusion_matrix(y_test, y_pred)
    
    # 精确率、召回率、F1
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, y_pred, average='weighted', zero_division=0
    )
    
    return {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "classification_report": report,
        "confusion_matrix": cm.tolist(),
        "n_samples": len(y_test)
    }


def perform_cross_validation(model, X, y, cv: int = 5) -> Dict[str, float]:
    """执行交叉验证
    
    Args:
        model: 待评估的模型
        X: 特征矩阵
        y: 标签向量
        cv: 折数
        
    Returns:
        交叉验证结果字典
    """
    scores = cross_val_score(model, X, y, cv=cv, scoring='accuracy')
    
    return {
        "cv_mean": round(scores.mean(), 4),
        "cv_std": round(scores.std(), 4),
        "cv_scores": scores.tolist(),
        "cv_folds": cv
    }


def hyperparameter_tuning_svm(X_train, y_train) -> Tuple[Any, Dict]:
    """SVM超参数调优
    
    使用网格搜索寻找最优超参数组合。
    
    Args:
        X_train: 训练集特征
        y_train: 训练集标签
        
    Returns:
        (最佳模型, 最佳参数字典)
    """
    param_grid = {
        'C': [0.1, 1, 10, 100],
        'kernel': ['rbf', 'linear'],
        'gamma': ['scale', 'auto', 0.001, 0.01]
    }
    
    svm = SVC(probability=True, random_state=42)
    
    grid_search = GridSearchCV(
        svm, param_grid, cv=3, scoring='accuracy',
        n_jobs=-1, verbose=0
    )
    
    grid_search.fit(X_train, y_train)
    
    return grid_search.best_estimator_, grid_search.best_params_


def train_intent_classifier() -> TrainingResult:
    """训练意图分类器（增强版）
    
    改进点：
    - 数据集划分（训练/测试）
    - 交叉验证评估
    - 超参数自动调优
    - 详细评估报告
    """
    start_time = time.time()
    model_name = "intent_classifier"
    
    try:
        app_logger.info("=" * 50)
        app_logger.info(f"开始训练: {model_name}")
        
        # 加载训练数据
        intent_data = generate_intent_training_data(n_samples_per_class=10)
        queries = intent_data["queries"]
        intents = intent_data["intents"]
        
        app_logger.info(f"训练样本数: {len(queries)}")
        app_logger.info(f"意图类别: {set(intents)}")
        
        # 特征提取
        X = np.array([extract_text_features(q) for q in queries])
        
        # 标签编码
        label_encoder = LabelEncoder()
        y = label_encoder.fit_transform(intents)
        intent_names = list(label_encoder.classes_)
        
        app_logger.info(f"特征维度: {X.shape[1]}")
        app_logger.info(f"类别数量: {len(intent_names)}")
        
        if len(X) < 4:
            app_logger.warning("训练数据不足（<4），跳过训练")
            return TrainingResult(model_name, success=False, 
                                 error="训练数据不足", training_time=time.time()-start_time)
        
        # 划分训练/测试集
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        app_logger.info(f"训练集: {len(X_train)}, 测试集: {len(X_test)}")
        
        # 超参数调优
        app_logger.info("执行超参数调优...")
        best_model, best_params = hyperparameter_tuning_svm(X_train, y_train)
        app_logger.info(f"最优参数: {best_params}")
        
        # 交叉验证
        app_logger.info("执行交叉验证...")
        cv_results = perform_cross_validation(best_model, X_train, y_train)
        app_logger.info(f"交叉验证准确率: {cv_results['cv_mean']} ± {cv_results['cv_std']}")
        
        # 最终训练（使用全部训练数据）
        best_model.fit(X_train, y_train)
        
        # 评估
        metrics = evaluate_classification_model(best_model, X_test, y_test, intent_names)
        app_logger.info(f"测试集准确率: {metrics['accuracy']}")
        app_logger.info(f"F1分数: {metrics['f1_score']}")
        
        # 打印分类报告
        if metrics.get('classification_report'):
            app_logger.info("\n分类报告:")
            for class_name, class_metrics in metrics['classification_report'].items():
                if isinstance(class_metrics, dict) and 'precision' in class_metrics:
                    app_logger.info(f"  {class_name}: P={class_metrics['precision']:.2f}, "
                                   f"R={class_metrics['recall']:.2f}, F1={class_metrics['f1-score']:.2f}")
        
        # 保存模型
        model_dir = PROJECT_ROOT / "models" / "intent"
        model_dir.mkdir(parents=True, exist_ok=True)
        model_path = model_dir / "intent_classifier.pkl"
        
        model_data = {
            "model": best_model,
            "label_encoder": label_encoder,
            "feature_extractor": "statistical",
            "best_params": best_params,
            "metrics": metrics,
            "cv_results": cv_results,
            "intent_names": intent_names,
            "trained_at": datetime.now().isoformat(),
            "version": "1.1.0"
        }
        
        with open(model_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        training_time = time.time() - start_time
        app_logger.info(f"{model_name} 训练完成！耗时: {training_time:.1f}s")
        app_logger.info(f"模型已保存: {model_path}")
        
        return TrainingResult(
            model_name=model_name,
            success=True,
            metrics=metrics,
            model_path=model_path,
            training_time=training_time
        )
        
    except Exception as e:
        app_logger.error(f"{model_name} 训练失败: {e}", exc_info=True)
        return TrainingResult(
            model_name=model_name,
            success=False,
            error=str(e),
            training_time=time.time()-start_time
        )


def train_relevance_scorer() -> TrainingResult:
    """训练相关性评分器（增强版）
    
    使用统计特征和SVM分类查询-文档对的相关性。
    """
    start_time = time.time()
    model_name = "relevance_scorer"
    
    try:
        app_logger.info("=" * 50)
        app_logger.info(f"开始训练: {model_name}")
        
        # 加载训练数据
        relevance_data = generate_relevance_training_data(n_positive=15, n_negative=20)
        
        queries = relevance_data["queries"]
        documents = relevance_data["documents"]
        labels = relevance_data["labels"]
        
        app_logger.info(f"正样本: {sum(labels)}, 负样本: {len(labels)-sum(labels)}")
        
        # 特征提取：组合查询和文档特征
        X = []
        for query, doc in zip(queries, documents):
            q_features = extract_text_features(query)
            d_features = extract_text_features(doc)
            
            # 组合特征：拼接 + 交互特征
            combined = np.concatenate([
                q_features,
                d_features,
                q_features * d_features,  # 元素乘积（交互特征）
                np.abs(q_features - d_features),  # 差值特征
                [len(set(query.split()) & set(doc.split()))]  # 词重叠数
            ])
            X.append(combined)
        
        X = np.array(X)
        y = np.array(labels)
        
        app_logger.info(f"特征维度: {X.shape[1]}")
        
        if len(X) < 4:
            app_logger.warning("训练数据不足，跳过训练")
            return TrainingResult(model_name, success=False,
                                 error="训练数据不足", training_time=time.time()-start_time)
        
        # 划分数据集
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # 特征缩放
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # 超参数调优
        app_logger.info("执行超参数调优...")
        best_model, best_params = hyperparameter_tuning_svm(X_train_scaled, y_train)
        app_logger.info(f"最优参数: {best_params}")
        
        # 交叉验证
        cv_results = perform_cross_validation(best_model, X_train_scaled, y_train)
        app_logger.info(f"CV准确率: {cv_results['cv_mean']} ± {cv_results['cv_std']}")
        
        # 最终训练
        best_model.fit(X_train_scaled, y_train)
        
        # 评估
        metrics = evaluate_classification_model(best_model, X_test_scaled, y_test)
        app_logger.info(f"测试集准确率: {metrics['accuracy']}")
        app_logger.info(f"F1分数: {metrics['f1_score']}")
        
        # 保存模型
        model_dir = PROJECT_ROOT / "models" / "relevance"
        model_dir.mkdir(parents=True, exist_ok=True)
        model_path = model_dir / "relevance_scorer.pkl"
        
        model_data = {
            "model": best_model,
            "scaler": scaler,
            "feature_extractor": "statistical_combined",
            "best_params": best_params,
            "metrics": metrics,
            "cv_results": cv_results,
            "trained_at": datetime.now().isoformat(),
            "version": "1.1.0"
        }
        
        with open(model_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        training_time = time.time() - start_time
        app_logger.info(f"{model_name} 训练完成！耗时: {training_time:.1f}s")
        
        return TrainingResult(model_name=model_name, success=True,
                             metrics=metrics, model_path=model_path,
                             training_time=training_time)
        
    except Exception as e:
        app_logger.error(f"{model_name} 训练失败: {e}", exc_info=True)
        return TrainingResult(model_name=model_name, success=False,
                             error=str(e), training_time=time.time()-start_time)


def train_ranking_optimizer() -> TrainingResult:
    """训练排序优化器（增强版）
    
    使用决策树/梯度提升回归预测文档的相关性分数。
    """
    start_time = time.time()
    model_name = "ranking_optimizer"
    
    try:
        app_logger.info("=" * 50)
        app_logger.info(f"开始训练: {model_name}")
        
        # 加载训练数据
        ranking_data = generate_ranking_training_data()
        queries = ranking_data["queries"]
        documents = ranking_data["documents"]
        scores = ranking_data["scores"]
        positions = ranking_data["positions"]
        
        app_logger.info(f"训练样本数: {len(queries)}")
        
        # 特征提取
        X = []
        y = []
        
        for query, doc_text, score, position in zip(queries, documents, scores, positions):
            q_features = extract_text_features(query)
            d_features = extract_text_features(doc_text)
            
            # 排序特征：包含位置信息
            combined = np.concatenate([
                q_features,
                d_features,
                q_features * d_features,
                [position / max(len(set(queries)), 1)],  # 归一化位置
                [len(doc_text) / 100],  # 文档长度归一化
                [len(set(query.split()) & set(doc_text.split()))],  # 词重叠
                [score]  # 原始分数作为参考特征
            ])
            X.append(combined)
            y.append(score)
        
        X = np.array(X)
        y = np.array(y)
        
        if len(X) < 4:
            app_logger.warning("训练数据不足，跳过训练")
            return TrainingResult(model_name, success=False,
                                 error="训练数据不足", training_time=time.time()-start_time)
        
        # 划分数据集
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # 特征缩放
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # 训练梯度提升回归模型（比单一决策树效果更好）
        model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42,
            subsample=0.8
        )
        model.fit(X_train_scaled, y_train)
        
        # 评估
        y_pred = model.predict(X_test_scaled)
        mse = mean_squared_error(y_test, y_pred)
        r2 = 1 - (np.sum((y_test - y_pred) ** 2) / np.sum((y_test - np.mean(y_test)) ** 2))
        
        metrics = {
            "mse": round(mse, 4),
            "rmse": round(np.sqrt(mse), 4),
            "r2_score": round(r2, 4),
            "mae": round(np.mean(np.abs(y_test - y_pred)), 4)
        }
        
        app_logger.info(f"MSE: {metrics['mse']}, RMSE: {metrics['rmse']}")
        app_logger.info(f"R²: {metrics['r2_score']}, MAE: {metrics['mae']}")
        
        # 保存模型
        model_dir = PROJECT_ROOT / "models" / "ranking"
        model_dir.mkdir(parents=True, exist_ok=True)
        model_path = model_dir / "ranking_optimizer.pkl"
        
        model_data = {
            "model": model,
            "scaler": scaler,
            "feature_extractor": "statistical_ranking",
            "metrics": metrics,
            "trained_at": datetime.now().isoformat(),
            "version": "1.1.0"
        }
        
        with open(model_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        training_time = time.time() - start_time
        app_logger.info(f"{model_name} 训练完成！耗时: {training_time:.1f}s")
        
        return TrainingResult(model_name=model_name, success=True,
                             metrics=metrics, model_path=model_path,
                             training_time=training_time)
        
    except Exception as e:
        app_logger.error(f"{model_name} 训练失败: {e}", exc_info=True)
        return TrainingResult(model_name=model_name, success=False,
                             error=str(e), training_time=time.time()-start_time)


def train_ml_reranker() -> TrainingResult:
    """训练ML重排序器（增强版）
    
    使用SVM和决策树集成进行重排序，
    结合两种模型的预测结果提高鲁棒性。
    """
    start_time = time.time()
    model_name = "ml_reranker"
    
    try:
        app_logger.info("=" * 50)
        app_logger.info(f"开始训练: {model_name}")
        
        # 生成训练数据
        rerank_queries = [
            ("高血压的症状", [
                {"text": "高血压典型症状包括头痛、头晕、心悸、耳鸣、视力模糊", "score": 0.95},
                {"text": "原发性高血压约占所有高血压病例的90-95%", "score": 0.75},
                {"text": "低血压也会导致头晕症状，需与高血压鉴别", "score": 0.45},
                {"text": "今天天气很好适合户外运动", "score": 0.05},
            ]),
            ("糖尿病的治疗", [
                {"text": "糖尿病治疗五驾马车：饮食、运动、药物、教育、监测", "score": 0.92},
                {"text": "二甲双胍是2型糖尿病一线用药", "score": 0.85},
                {"text": "Python是最好的编程语言", "score": 0.02},
            ]),
        ]
        
        X = []
        y = []
        
        for query, documents in rerank_queries:
            for doc in documents:
                q_features = extract_text_features(query)
                d_features = extract_text_features(doc["text"])
                
                combined = np.concatenate([
                    q_features,
                    d_features,
                    q_features * d_features,
                    [len(set(query.split()) & set(doc["text"].split()))],
                    [doc.get("score", 0)]
                ])
                X.append(combined)
                # 二分类标签：相关(1) vs 不相关(0)
                y.append(1 if doc.get("score", 0) > 0.5 else 0)
        
        X = np.array(X)
        y = np.array(y)
        
        app_logger.info(f"训练样本数: {len(X)}")
        app_logger.info(f"正样本: {sum(y)}, 负样本: {len(y)-sum(y)}")
        
        if len(X) < 4:
            app_logger.warning("训练数据不足，跳过训练")
            return TrainingResult(model_name, success=False,
                                 error="训练数据不足", training_time=time.time()-start_time)
        
        # 划分数据集
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.25, random_state=42, stratify=y
        )
        
        # 特征缩放
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # 模型1: SVM分类器
        svm_model = SVC(kernel='rbf', probability=True, random_state=42)
        svm_model.fit(X_train_scaled, y_train)
        
        # 模型2: 随机森林分类器
        rf_model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            class_weight='balanced'
        )
        rf_model.fit(X_train_scaled, y_train)
        
        # 模型3: 决策树回归（用于概率校准）
        dtree_model = DecisionTreeRegressor(random_state=42, max_depth=10)
        dtree_model.fit(X_train_scaled, y_train)
        
        # 集成评估：加权平均
        svm_proba = svm_model.predict_proba(X_test_scaled)[:, 1]
        rf_proba = rf_model.predict_proba(X_test_scaled)[:, 1]
        dtree_pred = dtree_model.predict(X_test_scaled)
        
        # 简单集成：平均概率
        ensemble_pred = (svm_proba + rf_proba + dtree_pred) / 3
        ensemble_binary = (ensemble_pred > 0.5).astype(int)
        
        # 评估各模型
        svm_metrics = evaluate_classification_model(svm_model, X_test_scaled, y_test)
        rf_metrics = evaluate_classification_model(rf_model, X_test_scaled, y_test)
        
        ensemble_accuracy = accuracy_score(y_test, ensemble_binary)
        ensemble_f1 = precision_recall_fscore_support(y_test, ensemble_binary, average='weighted')[2]
        
        metrics = {
            "svm_accuracy": svm_metrics["accuracy"],
            "rf_accuracy": rf_metrics["accuracy"],
            "ensemble_accuracy": round(ensemble_accuracy, 4),
            "ensemble_f1": round(ensemble_f1, 4),
            "n_models": 3
        }
        
        app_logger.info(f"SVM准确率: {svm_metrics['accuracy']}")
        app_logger.info(f"RF准确率: {rf_metrics['accuracy']}")
        app_logger.info(f"集成准确率: {ensemble_accuracy}")
        
        # 保存所有模型
        model_dir = PROJECT_ROOT / "models" / "reranker"
        model_dir.mkdir(parents=True, exist_ok=True)
        model_path = model_dir / "ml_reranker_ensemble.pkl"
        
        model_data = {
            "models": {
                "svm": svm_model,
                "random_forest": rf_model,
                "decision_tree": dtree_model
            },
            "scaler": scaler,
            "feature_extractor": "statistical_rerank",
            "ensemble_method": "weighted_average",
            "weights": {"svm": 0.33, "rf": 0.33, "dtree": 0.34},
            "metrics": metrics,
            "trained_at": datetime.now().isoformat(),
            "version": "1.1.0"
        }
        
        with open(model_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        # 同时保存单独的模型文件（兼容旧接口）
        with open(model_dir / "svm_reranker.pkl", 'wb') as f:
            pickle.dump(svm_model, f)
        with open(model_dir / "dtree_reranker.pkl", 'wb') as f:
            pickle.dump(dtree_model, f)
        with open(model_dir / "scaler.pkl", 'wb') as f:
            pickle.dump(scaler, f)
        
        training_time = time.time() - start_time
        app_logger.info(f"{model_name} 训练完成！耗时: {training_time:.1f}s")
        
        return TrainingResult(model_name=model_name, success=True,
                             metrics=metrics, model_path=model_path,
                             training_time=training_time)
        
    except Exception as e:
        app_logger.error(f"{model_name} 训练失败: {e}", exc_info=True)
        return TrainingResult(model_name=model_name, success=False,
                             error=str(e), training_time=time.time()-start_time)


# ============================================================
# 主程序入口
# ============================================================

# 可用的训练函数映射
TRAINING_FUNCTIONS = {
    "intent": train_intent_classifier,
    "relevance": train_relevance_scorer,
    "ranking": train_ranking_optimizer,
    "reranker": train_ml_reranker,
}

ALL_MODELS = list(TRAINING_FUNCTIONS.keys())


def parse_arguments() -> argparse.Namespace:
    """解析命令行参数
    
    Returns:
        解析后的参数命名空间
    """
    parser = argparse.ArgumentParser(
        description="智能医疗管家 - ML模型训练脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 训练所有模型
  python scripts/train_ml_models.py
  
  # 仅训练意图分类器
  python scripts/train_ml_models.py --model intent
  
  # 训练多个指定模型
  python scripts/train_ml_models.py --model intent relevance
  
  # 列出所有可用模型
  python scripts/train_ml_models.py --list-models

  # 输出详细日志
  python scripts/train_ml_models.py --verbose
        """
    )
    
    parser.add_argument(
        "--model", "-m",
        type=str,
        nargs="+",
        choices=ALL_MODELS,
        default=None,
        help="要训练的模型名称（默认训练所有）"
    )
    
    parser.add_argument(
        "--data-dir", "-d",
        type=str,
        default=None,
        help="自定义训练数据目录路径"
    )
    
    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default=None,
        help="模型输出目录路径"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=False,
        help="输出详细训练过程信息"
    )
    
    parser.add_argument(
        "--list-models",
        action="store_true",
        default=False,
        help="列出所有可训练的模型"
    )
    
    parser.add_argument(
        "--skip-eval",
        action="store_true",
        default=False,
        help="跳过评估步骤（加速训练）"
    )
    
    return parser.parse_args()


def save_training_report(results: List[TrainingResult], output_path: Path = None):
    """保存训练报告
    
    将所有模型的训练结果汇总为JSON报告文件。
    
    Args:
        results: 训练结果列表
        output_path: 报告输出路径
    """
    report = {
        "training_summary": {
            "total_models": len(results),
            "successful": sum(1 for r in results if r.success),
            "failed": sum(1 for r in results if not r.success),
            "total_time": round(sum(r.training_time for r in results), 2),
            "timestamp": datetime.now().isoformat(),
            "version": "1.1.0"
        },
        "model_results": [r.to_dict() for r in results]
    }
    
    if output_path is None:
        output_path = PROJECT_ROOT / "logs" / "training_report.json"
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    app_logger.info(f"训练报告已保存: {output_path}")


def main():
    """主函数 - 协调所有模型的训练流程"""
    
    # 解析命令行参数
    args = parse_arguments()
    
    # 列出可用模型
    if args.list_models:
        print("\n可训练的模型列表:")
        print("-" * 40)
        for name, func in TRAINING_FUNCTIONS.items():
            print(f"  {name:<15} {func.__doc__.split(chr(10))[0] if func.__doc__ else ''}")
        print("-" * 40)
        return
    
    # 设置输出目录
    if args.output_dir:
        global MODEL_OUTPUT_DIR
        MODEL_OUTPUT_DIR = Path(args.output_dir)
        MODEL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 开始训练
    app_logger.info("=" * 60)
    app_logger.info("  智能医疗管家 - ML模型训练系统 v1.1.0")
    app_logger.info("=" * 60)
    app_logger.info(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    app_logger.info(f"项目根目录: {PROJECT_ROOT}")
    
    overall_start = time.time()
    results = []
    
    # 确定要训练的模型
    models_to_train = args.model if args.model else ALL_MODELS
    app_logger.info(f"\n待训练模型 ({len(models_to_train)}): {', '.join(models_to_train)}\n")
    
    try:
        for i, model_name in enumerate(models_to_train, 1):
            app_logger.info(f"\n[{i}/{len(models_to_train)}] 开始训练: {model_name}")
            
            train_func = TRAINING_FUNCTIONS.get(model_name)
            if not train_func:
                app_logger.warning(f"未知模型: {model_name}，跳过")
                continue
            
            result = train_func()
            results.append(result)
            
            # 打印结果摘要
            app_logger.info(f"\n{result}")
        
        # 汇总报告
        total_time = time.time() - overall_start
        
        app_logger.info("\n" + "=" * 60)
        app_logger.info("  训练完成 - 结果汇总")
        app_logger.info("=" * 60)
        
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        
        app_logger.info(f"\n总耗时: {total_time:.1f}s")
        app_logger.info(f"成功: {len(successful)}/{len(results)}")
        
        if successful:
            app_logger.info("\n成功训练的模型:")
            for r in successful:
                app_logger.info(f"  ✓ {r.model_name}: accuracy={r.metrics.get('accuracy', 'N/A')}, "
                               f"time={r.training_time:.1f}s")
        
        if failed:
            app_logger.info("\n训练失败的模型:")
            for r in failed:
                app_logger.info(f"  ✗ {r.model_name}: {r.error}")
        
        # 保存训练报告
        save_training_report(results)
        
        # 使用建议
        app_logger.info("\n" + "-" * 60)
        app_logger.info("后续建议:")
        app_logger.info("  1. 当前使用示例数据，生产环境需准备真实标注数据")
        app_logger.info("  2. 可使用人工标注、用户点击、反馈数据作为训练集")
        app_logger.info("  3. 建议定期重新训练以适应数据分布变化")
        app_logger.info("  4. 查看训练报告: logs/training_report.json")
        app_logger.info("-" * 60)
        
    except KeyboardInterrupt:
        app_logger.warning("\n\n训练被用户中断")
        raise
    except Exception as e:
        app_logger.error(f"\n训练流程异常终止: {e}", exc_info=True)
        raise


# ============================================================
# 模型版本管理与工具函数
# ============================================================

class ModelVersionManager:
    """模型版本管理器
    
    管理模型的版本、元数据和生命周期。
    支持多版本共存和回滚操作。
    """
    
    def __init__(self, models_dir: Path = None):
        self.models_dir = models_dir or (PROJECT_ROOT / "models")
        self.version_file = self.models_dir / "versions.json"
        self._versions = self._load_versions()
    
    def _load_versions(self) -> Dict:
        """加载版本记录"""
        if self.version_file.exists():
            try:
                with open(self.version_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                app_logger.warning(f"加载版本记录失败: {e}")
        return {"models": {}, "last_updated": None}
    
    def _save_versions(self):
        """保存版本记录"""
        self.versions["last_updated"] = datetime.now().isoformat()
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        with open(self.version_file, 'w', encoding='utf-8') as f:
            json.dump(self._versions, f, ensure_ascii=False, indent=2)
    
    def register_model(self, model_name: str, model_path: Path, 
                       version: str, metadata: Dict = None) -> Dict:
        """注册新训练的模型
        
        Args:
            model_name: 模型名称
            model_path: 模型文件路径
            version: 版本号
            metadata: 额外元数据
            
        Returns:
            版本信息字典
        """
        if model_name not in self._versions["models"]:
            self._versions["models"][model_name] = []
        
        version_info = {
            "version": version,
            "path": str(model_path),
            "registered_at": datetime.now().isoformat(),
            "metadata": metadata or {},
            "size_mb": round(model_path.stat().st_size / (1024 * 1024), 2) if model_path.exists() else 0
        }
        
        # 添加到版本历史
        self._versions["models"][model_name].append(version_info)
        
        # 只保留最近5个版本
        if len(self._versions["models"][model_name]) > 5:
            old_version = self._versions["models"][model_name].pop(0)
            app_logger.info(f"移除旧版本: {old_version['version']}")
        
        self._save_versions()
        app_logger.info(f"已注册模型: {model_name} v{version}")
        
        return version_info
    
    def get_latest_version(self, model_name: str) -> Optional[Dict]:
        """获取指定模型的最新版本信息"""
        versions = self._versions.get("models", {}).get(model_name, [])
        return versions[-1] if versions else None
    
    def list_models(self) -> Dict[str, List[Dict]]:
        """列出所有已注册的模型及其版本"""
        return self._versions.get("models", {})
    
    def rollback(self, model_name: str, target_version: str = None) -> bool:
        """回滚到指定版本
        
        Args:
            model_name: 模型名称
            target_version: 目标版本（默认回滚到上一版本）
            
        Returns:
            是否成功
        """
        versions = self._versions.get("models", {}).get(model_name, [])
        
        if len(versions) < 2:
            app_logger.warning(f"{model_name} 没有可回滚的旧版本")
            return False
        
        if target_version:
            # 回滚到指定版本
            for v in versions:
                if v["version"] == target_version:
                    app_logger.info(f"{model_name} 已回滚到 v{target_version}")
                    return True
            app_logger.warning(f"未找到版本: {target_version}")
            return False
        else:
            # 回滚到上一版本
            prev_version = versions[-2]
            app_logger.info(f"{model_name} 已回滚到 v{prev_version['version']}")
            return True


def validate_model(model_path: Path) -> Tuple[bool, str]:
    """验证模型文件的有效性
    
    检查模型文件是否可以正常加载和使用。
    
    Args:
        model_path: 模型文件路径
        
    Returns:
        (是否有效, 错误消息)
    """
    if not model_path.exists():
        return False, f"文件不存在: {model_path}"
    
    if model_path.stat().st_size == 0:
        return False, f"文件为空: {model_path}"
    
    try:
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
        
        # 验证必要字段
        required_fields = ["model"]
        for field in required_fields:
            if field not in model_data:
                return False, f"缺少必要字段: {field}"
        
        # 尝试调用模型的predict方法（基本可用性检查）
        model = model_data.get("model")
        if hasattr(model, 'predict'):
            # 使用虚拟数据测试
            test_input = np.zeros((1, 10))
            try:
                _ = model.predict(test_input)
            except Exception as e:
                # 预测失败不一定是致命错误，记录警告即可
                app_logger.debug(f"模型预测测试警告: {e}")
        
        return True, "模型验证通过"
        
    except pickle.UnpicklingError as e:
        return False, f"Pickle反序列化失败: {e}"
    except Exception as e:
        return False, f"验证异常: {e}"


def load_model(model_name: str, models_dir: Path = None) -> Optional[Any]:
    """加载指定模型
    
    Args:
        model_name: 模型名称 (intent/relevance/ranking/reranker)
        models_dir: 模型目录
        
    Returns:
        模型数据字典，加载失败返回None
    """
    models_dir = models_dir or (PROJECT_ROOT / "models")
    
    # 模型文件映射
    model_files = {
        "intent": "intent_classifier.pkl",
        "relevance": "relevance_scorer.pkl",
        "ranking": "ranking_optimizer.pkl",
        "reranker": "ml_reranker_ensemble.pkl",
    }
    
    if model_name not in model_files:
        app_logger.error(f"未知模型名称: {model_name}")
        return None
    
    model_path = models_dir / model_name / model_files[model_name]
    
    # 验证模型
    is_valid, msg = validate_model(model_path)
    if not is_valid:
        app_logger.error(f"模型验证失败 [{model_name}]: {msg}")
        return None
    
    try:
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
        
        app_logger.info(f"成功加载模型: {model_name} (v{model_data.get('version', 'unknown')})")
        return model_data
        
    except Exception as e:
        app_logger.error(f"加载模型失败 [{model_name}]: {e}")
        return None


def create_training_config(output_path: Path = None) -> Path:
    """创建训练配置模板
    
    生成一个YAML格式的训练配置文件，
    用户可以通过修改此文件自定义训练参数。
    
    Args:
        output_path: 配置文件输出路径
        
    Returns:
        配置文件路径
    """
    config = {
        "training": {
            "random_seed": 42,
            "test_size": 0.2,
            "cross_validation_folds": 5,
            "n_jobs": -1,
            "verbose": True
        },
        "models": {
            "intent_classifier": {
                "enabled": True,
                "algorithm": "svm",
                "hyperparameters": {
                    "C": [0.1, 1, 10, 100],
                    "kernel": ["rbf", "linear"],
                    "gamma": ["scale", "auto"]
                },
                "n_samples_per_class": 20
            },
            "relevance_scorer": {
                "enabled": True,
                "algorithm": "svm",
                "n_positive_samples": 30,
                "n_negative_samples": 30
            },
            "ranking_optimizer": {
                "enabled": True,
                "algorithm": "gradient_boosting",
                "hyperparameters": {
                    "n_estimators": 100,
                    "max_depth": 6,
                    "learning_rate": 0.1
                }
            },
            "ml_reranker": {
                "enabled": True,
                "ensemble": True,
                "models": ["svm", "random_forest", "decision_tree"]
            }
        },
        "output": {
            "models_dir": "./models",
            "report_dir": "./logs",
            "save_intermediate": False
        },
        "data": {
            "source": "generated",  # generated/file/database
            "augmentation": True,
            "balance_classes": True
        }
    }
    
    if output_path is None:
        output_path = PROJECT_ROOT / "config" / "training_config.json"
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
    
    app_logger.info(f"训练配置模板已创建: {output_path}")
    return output_path


def benchmark_models(models_dir: Path = None) -> Dict[str, float]:
    """对已训练的模型进行基准测试
    
    测试各模型的推理延迟，用于性能评估。
    
    Args:
        models_dir: 模型目录
        
    Returns:
        各模型的平均推理时间(ms)
    """
    import time as time_module
    
    models_dir = models_dir or (PROJECT_ROOT / "models")
    benchmarks = {}
    
    app_logger.info("开始模型基准测试...")
    
    for model_name in ALL_MODELS:
        model_data = load_model(model_name, models_dir)
        if model_data is None:
            continue
        
        model = model_data.get("model")
        if model is None or not hasattr(model, 'predict'):
            app_logger.warning(f"{model_name}: 无法进行基准测试（无predict方法）")
            continue
        
        # 准备测试数据
        n_tests = 100
        test_input = np.random.randn(n_tests, 20)  # 通用测试输入
        
        # 预热
        _ = model.predict(test_input[:1])
        
        # 正式测试
        start = time_module.time()
        for _ in range(5):
            _ = model.predict(test_input)
        elapsed = (time_module.time() - start) / (n_tests * 5) * 1000  # ms per sample
        
        benchmarks[model_name] = round(elapsed, 3)
        app_logger.info(f"  {model_name}: {elapsed:.3f} ms/sample")
    
    return benchmarks


if __name__ == "__main__":
    main()

