"""ML模型训练脚本"""
import sys
from pathlib import Path
import numpy as np
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, mean_squared_error
import pickle
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.logger import app_logger


def generate_sample_data():
    """生成示例训练数据"""
    # 意图分类数据
    intent_data = {
        "queries": [
            "我最近头痛，可能是什么病？",
            "高血压应该吃什么药？",
            "需要做什么检查来诊断糖尿病？",
            "如何预防心脏病？",
            "糖尿病的症状有哪些？",
            "什么是高血压？",
            "你好，我想咨询一下",
        ],
        "intents": [
            "diagnosis",
            "medication",
            "examination",
            "health_management",
            "symptom_inquiry",
            "disease_info",
            "general"
        ]
    }
    
    # 相关性评分数据（简化示例）
    relevance_data = {
        "queries": [
            "高血压的症状",
            "糖尿病的治疗",
        ],
        "documents": [
            "高血压是一种常见的慢性疾病，主要症状包括头痛、头晕、心悸等。",
            "糖尿病需要控制血糖，可以通过药物治疗和生活方式调整。",
        ],
        "labels": [1, 1]  # 1表示相关，0表示不相关
    }
    
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

