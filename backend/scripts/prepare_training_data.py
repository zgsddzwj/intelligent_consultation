"""准备ML模型训练数据"""
import json
from pathlib import Path
from typing import List, Dict, Any


def create_intent_training_data():
    """创建意图分类训练数据"""
    data = [
        {
            "query": "我最近头痛，可能是什么病？",
            "intent": "diagnosis",
            "intent_name": "诊断咨询"
        },
        {
            "query": "高血压应该吃什么药？",
            "intent": "medication",
            "intent_name": "用药咨询"
        },
        {
            "query": "需要做什么检查来诊断糖尿病？",
            "intent": "examination",
            "intent_name": "检查咨询"
        },
        {
            "query": "如何预防心脏病？",
            "intent": "health_management",
            "intent_name": "健康管理"
        },
        {
            "query": "糖尿病的症状有哪些？",
            "intent": "symptom_inquiry",
            "intent_name": "症状询问"
        },
        {
            "query": "什么是高血压？",
            "intent": "disease_info",
            "intent_name": "疾病信息"
        },
    ]
    
    output_file = Path("./data/training/intent_data.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"意图分类训练数据已保存到: {output_file}")


def create_relevance_training_data():
    """创建相关性评分训练数据"""
    data = [
        {
            "query": "高血压的症状",
            "document": "高血压是一种常见的慢性疾病，主要症状包括头痛、头晕、心悸、胸闷等。",
            "label": 1,
            "relevance_score": 0.9
        },
        {
            "query": "高血压的症状",
            "document": "糖尿病需要控制血糖，可以通过药物治疗和生活方式调整。",
            "label": 0,
            "relevance_score": 0.1
        },
        {
            "query": "糖尿病的治疗",
            "document": "糖尿病需要控制血糖，可以通过药物治疗和生活方式调整。",
            "label": 1,
            "relevance_score": 0.9
        },
    ]
    
    output_file = Path("./data/training/relevance_data.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"相关性评分训练数据已保存到: {output_file}")


if __name__ == "__main__":
    print("准备ML模型训练数据...")
    create_intent_training_data()
    create_relevance_training_data()
    print("训练数据准备完成！")

