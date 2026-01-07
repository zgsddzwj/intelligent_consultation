"""查询策略选择器 - 根据问题类型自动选择查询策略"""
from typing import Dict, Any, List, Optional
from app.utils.logger import app_logger
import re


class QueryStrategySelector:
    """查询策略选择器"""
    
    # 问题类型定义
    QUESTION_TYPES = {
        "disease_info": "疾病信息查询",
        "symptom_diagnosis": "症状诊断",
        "drug_info": "药物信息查询",
        "drug_interaction": "药物相互作用",
        "examination_advice": "检查建议",
        "treatment_plan": "治疗方案",
        "general_consultation": "一般咨询"
    }
    
    # 策略映射
    STRATEGY_MAP = {
        "disease_info": "disease_centric",
        "symptom_diagnosis": "symptom_centric",
        "drug_info": "drug_centric",
        "drug_interaction": "drug_interaction",
        "examination_advice": "examination_centric",
        "treatment_plan": "multi_entity",
        "general_consultation": "general"
    }
    
    def __init__(self):
        self.patterns = self._build_patterns()
    
    def _build_patterns(self) -> Dict[str, List[str]]:
        """构建问题类型识别模式"""
        return {
            "disease_info": [
                r'什么是(.+?)[？?]',
                r'(.+?)是什么',
                r'(.+?)的介绍',
                r'了解(.+?)',
                r'(.+?)的症状',
                r'(.+?)的治疗',
                r'(.+?)怎么治',
                r'(.+?)吃什么药'
            ],
            "symptom_diagnosis": [
                r'(.+?)可能是什么病',
                r'(.+?)是什么原因',
                r'(.+?)会不会是(.+?)',
                r'(.+?)需要检查什么',
                r'(.+?)怎么办',
                r'(.+?)怎么治疗',
                r'根据(.+?)诊断'
            ],
            "drug_info": [
                r'(.+?)的作用',
                r'(.+?)的副作用',
                r'(.+?)怎么吃',
                r'(.+?)的用法',
                r'(.+?)的剂量',
                r'(.+?)适合(.+?)吗'
            ],
            "drug_interaction": [
                r'(.+?)和(.+?)能一起吃',
                r'(.+?)和(.+?)的相互作用',
                r'(.+?)不能和(.+?)一起',
                r'药物相互作用'
            ],
            "examination_advice": [
                r'需要做什么检查',
                r'(.+?)检查什么',
                r'(.+?)需要(.+?)检查',
                r'检查项目',
                r'化验什么'
            ],
            "treatment_plan": [
                r'(.+?)的治疗方案',
                r'(.+?)怎么治疗',
                r'(.+?)的治疗方法',
                r'(.+?)的用药',
                r'(.+?)的护理'
            ],
            "general_consultation": [
                r'咨询',
                r'问一下',
                r'请问',
                r'帮忙'
            ]
        }
    
    def classify_question(self, query: str, entities: Dict[str, List[str]]) -> Dict[str, Any]:
        """
        分类问题类型并选择查询策略
        
        Args:
            query: 查询文本
            entities: 提取的实体
        
        Returns:
            包含问题类型和策略的字典
        """
        # 1. 基于模式匹配分类
        question_type = self._classify_by_pattern(query)
        
        # 2. 基于实体类型调整
        question_type = self._adjust_by_entities(question_type, entities)
        
        # 3. 选择策略
        strategy = self.STRATEGY_MAP.get(question_type, "general")
        
        result = {
            "question_type": question_type,
            "question_type_name": self.QUESTION_TYPES.get(question_type, "未知"),
            "strategy": strategy,
            "entities": entities,
            "confidence": self._calculate_confidence(query, question_type, entities)
        }
        
        app_logger.debug(f"问题分类: {query} -> {result}")
        return result
    
    def _classify_by_pattern(self, query: str) -> str:
        """基于模式匹配分类"""
        scores = {qtype: 0 for qtype in self.QUESTION_TYPES.keys()}
        
        for qtype, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, query):
                    scores[qtype] += 1
        
        # 返回得分最高的问题类型
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        return "general_consultation"
    
    def _adjust_by_entities(self, question_type: str, entities: Dict[str, List[str]]) -> str:
        """根据实体类型调整问题类型"""
        # 如果检测到症状但没有疾病，可能是症状诊断
        if entities.get("symptoms") and not entities.get("diseases"):
            if question_type == "general_consultation":
                return "symptom_diagnosis"
        
        # 如果检测到药物，可能是药物信息查询
        if entities.get("drugs") and question_type == "general_consultation":
            return "drug_info"
        
        # 如果检测到疾病，可能是疾病信息查询
        if entities.get("diseases") and question_type == "general_consultation":
            return "disease_info"
        
        return question_type
    
    def _calculate_confidence(self, query: str, question_type: str, entities: Dict[str, List[str]]) -> float:
        """计算分类置信度"""
        confidence = 0.5  # 基础置信度
        
        # 模式匹配得分
        pattern_matches = sum(1 for pattern in self.patterns.get(question_type, []) 
                            if re.search(pattern, query))
        if pattern_matches > 0:
            confidence += min(pattern_matches * 0.1, 0.3)
        
        # 实体匹配得分
        entity_count = sum(len(v) for v in entities.values())
        if entity_count > 0:
            confidence += min(entity_count * 0.05, 0.2)
        
        return min(confidence, 1.0)
    
    def get_query_strategy(self, strategy_name: str) -> Dict[str, Any]:
        """获取查询策略配置"""
        strategies = {
            "disease_centric": {
                "description": "以疾病为中心的查询",
                "priority": ["diseases", "symptoms", "drugs", "examinations"],
                "depth": 2,
                "max_results": 10
            },
            "symptom_centric": {
                "description": "以症状为中心的查询",
                "priority": ["symptoms", "diseases", "examinations"],
                "depth": 2,
                "max_results": 15
            },
            "drug_centric": {
                "description": "以药物为中心的查询",
                "priority": ["drugs", "diseases"],
                "depth": 1,
                "max_results": 10
            },
            "drug_interaction": {
                "description": "药物相互作用查询",
                "priority": ["drugs"],
                "depth": 1,
                "max_results": 20
            },
            "examination_centric": {
                "description": "以检查为中心的查询",
                "priority": ["examinations", "diseases"],
                "depth": 1,
                "max_results": 10
            },
            "multi_entity": {
                "description": "多实体关联查询",
                "priority": ["diseases", "symptoms", "drugs", "examinations"],
                "depth": 3,
                "max_results": 20
            },
            "general": {
                "description": "通用查询",
                "priority": ["diseases", "symptoms", "drugs", "examinations"],
                "depth": 2,
                "max_results": 10
            }
        }
        
        return strategies.get(strategy_name, strategies["general"])

