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


def train_intent_classifier():
    """训练意图分类器"""
    app_logger.info("开始训练意图分类器...")
    
    # 加载或生成训练数据
    intent_data, _ = generate_sample_data()
    
    # 这里应该从实际数据源加载训练数据
    # 示例：使用规则生成特征
    from app.knowledge.ml.intent_classifier import IntentClassifier
    
    classifier = IntentClassifier()
    
    # 提取特征
    X = []
    y = []
    intent_names = list(classifier.INTENT_TYPES.keys())
    
    for query, intent in zip(intent_data["queries"], intent_data["intents"]):
        features = classifier.extract_features(query)
        X.append(features)
        y.append(intent_names.index(intent) if intent in intent_names else len(intent_names) - 1)
    
    X = np.array(X)
    y = np.array(y)
    
    if len(X) < 2:
        app_logger.warning("训练数据不足，跳过意图分类器训练")
        return
    
    # 训练SVM模型
    model = SVC(kernel='rbf', probability=True, random_state=42)
    model.fit(X, y)
    
    # 评估
    y_pred = model.predict(X)
    accuracy = accuracy_score(y, y_pred)
    app_logger.info(f"意图分类器训练完成，准确率: {accuracy:.2f}")
    
    # 保存模型
    model_dir = Path("./models/intent")
    model_dir.mkdir(parents=True, exist_ok=True)
    
    model_data = {
        "model": model,
        "vectorizer": None  # 这里可以添加文本向量化器
    }
    
    with open(model_dir / "intent_classifier.pkl", 'wb') as f:
        pickle.dump(model_data, f)
    
    app_logger.info(f"意图分类器已保存到: {model_dir / 'intent_classifier.pkl'}")


def train_relevance_scorer():
    """训练相关性评分器"""
    app_logger.info("开始训练相关性评分器...")
    
    # 加载或生成训练数据
    _, relevance_data = generate_sample_data()
    
    from app.knowledge.ml.relevance_scorer import RelevanceScorer
    
    scorer = RelevanceScorer()
    
    # 提取特征
    X = []
    y = []
    
    for query, doc_text, label in zip(
        relevance_data["queries"],
        relevance_data["documents"],
        relevance_data["labels"]
    ):
        doc = {"text": doc_text}
        features = scorer.extract_features(query, doc)
        X.append(features)
        y.append(label)
    
    # 生成更多负样本（简化处理）
    for i in range(len(X)):
        # 添加一些负样本
        doc = {"text": "这是一段不相关的文本内容。"}
        features = scorer.extract_features(relevance_data["queries"][0], doc)
        X.append(features)
        y.append(0)
    
    X = np.array(X)
    y = np.array(y)
    
    if len(X) < 2:
        app_logger.warning("训练数据不足，跳过相关性评分器训练")
        return
    
    # 特征缩放
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # 训练SVM模型
    model = SVC(kernel='rbf', probability=True, random_state=42)
    model.fit(X_scaled, y)
    
    # 评估
    y_pred = model.predict(X_scaled)
    accuracy = accuracy_score(y, y_pred)
    app_logger.info(f"相关性评分器训练完成，准确率: {accuracy:.2f}")
    
    # 保存模型
    model_dir = Path("./models/relevance")
    model_dir.mkdir(parents=True, exist_ok=True)
    
    model_data = {
        "model": model,
        "scaler": scaler
    }
    
    with open(model_dir / "relevance_scorer.pkl", 'wb') as f:
        pickle.dump(model_data, f)
    
    app_logger.info(f"相关性评分器已保存到: {model_dir / 'relevance_scorer.pkl'}")


def train_ranking_optimizer():
    """训练排序优化器"""
    app_logger.info("开始训练排序优化器...")
    
    from app.knowledge.ml.ranking_optimizer import RankingOptimizer
    
    optimizer = RankingOptimizer()
    
    # 生成示例训练数据
    queries = ["高血压的症状", "糖尿病的治疗"]
    documents = [
        {"text": "高血压的症状包括头痛、头晕等", "score": 0.8, "source": "doc1"},
        {"text": "糖尿病需要控制血糖", "score": 0.7, "source": "doc2"},
    ]
    
    # 提取特征
    X = []
    y = []  # 排序分数（可以使用相关性分数或人工标注）
    
    for query in queries:
        for i, doc in enumerate(documents):
            features = optimizer.extract_ranking_features(query, doc, position=i)
            X.append(features)
            # 使用原始分数作为目标（实际应该使用人工标注或点击数据）
            y.append(doc.get("score", 0.5))
    
    X = np.array(X)
    y = np.array(y)
    
    if len(X) < 2:
        app_logger.warning("训练数据不足，跳过排序优化器训练")
        return
    
    # 特征缩放
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # 训练决策树回归模型
    model = DecisionTreeRegressor(random_state=42, max_depth=10)
    model.fit(X_scaled, y)
    
    # 评估
    y_pred = model.predict(X_scaled)
    mse = mean_squared_error(y, y_pred)
    app_logger.info(f"排序优化器训练完成，MSE: {mse:.4f}")
    
    # 保存模型
    model_dir = Path("./models/ranking")
    model_dir.mkdir(parents=True, exist_ok=True)
    
    model_data = {
        "model": model,
        "scaler": scaler
    }
    
    with open(model_dir / "ranking_optimizer.pkl", 'wb') as f:
        pickle.dump(model_data, f)
    
    app_logger.info(f"排序优化器已保存到: {model_dir / 'ranking_optimizer.pkl'}")


def train_ml_reranker():
    """训练ML重排序器"""
    app_logger.info("开始训练ML重排序器...")
    
    from app.knowledge.rag.ml_reranker import MLReranker
    
    reranker = MLReranker()
    
    # 生成示例训练数据
    query = "高血压的症状"
    documents = [
        {"text": "高血压的症状包括头痛、头晕、心悸等", "score": 0.9},
        {"text": "糖尿病需要控制血糖", "score": 0.3},
    ]
    
    # 提取特征
    X = []
    y = []  # 相关性标签
    
    for doc in documents:
        features = reranker.extract_features(query, doc)
        X.append(features)
        # 使用分数阈值判断相关性（实际应该使用人工标注）
        y.append(1 if doc.get("score", 0) > 0.5 else 0)
    
    X = np.array(X)
    y = np.array(y)
    
    if len(X) < 2:
        app_logger.warning("训练数据不足，跳过ML重排序器训练")
        return
    
    # 特征缩放
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # 训练SVM模型
    svm_model = SVC(kernel='rbf', probability=True, random_state=42)
    svm_model.fit(X_scaled, y)
    
    # 训练决策树模型
    dtree_model = DecisionTreeRegressor(random_state=42, max_depth=10)
    dtree_model.fit(X_scaled, y)
    
    # 保存模型
    model_dir = Path("./models/reranker")
    model_dir.mkdir(parents=True, exist_ok=True)
    
    with open(model_dir / "svm_reranker.pkl", 'wb') as f:
        pickle.dump(svm_model, f)
    
    with open(model_dir / "dtree_reranker.pkl", 'wb') as f:
        pickle.dump(dtree_model, f)
    
    with open(model_dir / "scaler.pkl", 'wb') as f:
        pickle.dump(scaler, f)
    
    app_logger.info(f"ML重排序器已保存到: {model_dir}")


def main():
    """主函数"""
    app_logger.info("=" * 50)
    app_logger.info("开始训练ML模型")
    app_logger.info("=" * 50)
    
    try:
        # 训练意图分类器
        train_intent_classifier()
        
        # 训练相关性评分器
        train_relevance_scorer()
        
        # 训练排序优化器
        train_ranking_optimizer()
        
        # 训练ML重排序器
        train_ml_reranker()
        
        app_logger.info("=" * 50)
        app_logger.info("所有ML模型训练完成！")
        app_logger.info("=" * 50)
        app_logger.info("\n注意：")
        app_logger.info("1. 当前使用的是示例数据，实际应用需要准备真实训练数据")
        app_logger.info("2. 可以使用人工标注、点击数据、用户反馈等作为训练数据")
        app_logger.info("3. 建议定期重新训练模型以提升效果")
        
    except Exception as e:
        app_logger.error(f"模型训练失败: {e}")
        raise


if __name__ == "__main__":
    main()

