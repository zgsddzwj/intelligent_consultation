"""知识图谱模式定义"""
from typing import Dict, List


# 实体类型定义
ENTITY_TYPES = {
    "Disease": {
        "label": "疾病",
        "properties": ["name", "icd10", "description", "etiology", "pathophysiology"]
    },
    "Symptom": {
        "label": "症状",
        "properties": ["name", "severity", "description"]
    },
    "Drug": {
        "label": "药物",
        "properties": ["name", "generic_name", "dosage_form", "indication", "contraindication"]
    },
    "Examination": {
        "label": "检查项目",
        "properties": ["name", "type", "reference_range", "description"]
    },
    "Department": {
        "label": "科室",
        "properties": ["name", "description", "scope"]
    }
}

# 关系类型定义
RELATIONSHIP_TYPES = {
    "HAS_SYMPTOM": {
        "label": "有症状",
        "from": "Disease",
        "to": "Symptom",
        "properties": ["frequency", "severity"]
    },
    "REQUIRES_EXAM": {
        "label": "需要检查",
        "from": "Disease",
        "to": "Examination",
        "properties": ["necessity", "priority"]
    },
    "TREATED_BY": {
        "label": "用药物治疗",
        "from": "Disease",
        "to": "Drug",
        "properties": ["effectiveness", "dosage", "duration"]
    },
    "CONTRAINDICATED_FOR": {
        "label": "禁忌",
        "from": "Drug",
        "to": "Disease",
        "properties": ["reason", "severity"]
    },
    "INTERACTS_WITH": {
        "label": "相互作用",
        "from": "Drug",
        "to": "Drug",
        "properties": ["interaction_type", "severity", "description"]
    },
    "BELONGS_TO": {
        "label": "属于",
        "from": "Symptom",
        "to": "Department",
        "properties": []
    }
}


def get_entity_schema(entity_type: str) -> Dict:
    """获取实体模式"""
    return ENTITY_TYPES.get(entity_type, {})


def get_relationship_schema(rel_type: str) -> Dict:
    """获取关系模式"""
    return RELATIONSHIP_TYPES.get(rel_type, {})

