"""诊断辅助工具"""
from typing import Dict, Any, List
from app.utils.logger import app_logger
import re


class DiagnosisTool:
    """诊断辅助工具"""
    
    def __init__(self):
        self.name = "diagnosis_assistant"
        self.description = "辅助诊断工具，分析症状并提供诊断建议"
    
    def execute(self, symptoms: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行诊断辅助"""
        try:
            # 提取症状关键词
            symptom_keywords = self.extract_symptoms(symptoms)
            
            # 风险等级评估
            risk_level = self.assess_risk_level(symptoms, symptom_keywords)
            
            result = {
                "symptoms": symptoms,
                "symptom_keywords": symptom_keywords,
                "risk_level": risk_level,
                "requires_immediate_attention": risk_level in ["high", "critical"]
            }
            
            app_logger.info(f"诊断辅助完成，风险等级: {risk_level}")
            return result
        except Exception as e:
            app_logger.error(f"诊断辅助失败: {e}")
            return {"error": str(e)}
    
    def extract_symptoms(self, text: str) -> List[str]:
        """提取症状关键词"""
        # 常见症状关键词（可以扩展）
        symptom_keywords = [
            "疼痛", "发热", "咳嗽", "呼吸困难", "胸痛", "腹痛",
            "头痛", "头晕", "恶心", "呕吐", "腹泻", "便秘",
            "乏力", "失眠", "心悸", "水肿", "皮疹", "出血"
        ]
        
        found_symptoms = []
        text_lower = text.lower()
        for keyword in symptom_keywords:
            if keyword in text_lower:
                found_symptoms.append(keyword)
        
        return found_symptoms
    
    def assess_risk_level(self, symptoms: str, symptom_keywords: List[str]) -> str:
        """评估风险等级"""
        # 高风险关键词
        high_risk_keywords = [
            "胸痛", "呼吸困难", "意识不清", "大出血", "剧烈疼痛",
            "休克", "昏迷", "抽搐", "急性", "紧急"
        ]
        
        # 中风险关键词
        medium_risk_keywords = [
            "持续发热", "持续疼痛", "反复", "加重", "恶化"
        ]
        
        text_lower = symptoms.lower()
        
        # 检查高风险关键词
        for keyword in high_risk_keywords:
            if keyword in text_lower:
                return "high"
        
        # 检查中风险关键词
        for keyword in medium_risk_keywords:
            if keyword in text_lower:
                return "medium"
        
        # 默认低风险
        return "low"
    
    def get_risk_recommendation(self, risk_level: str) -> str:
        """获取风险建议"""
        recommendations = {
            "high": "建议立即前往医院急诊科就诊，或拨打急救电话。",
            "medium": "建议尽快前往医院就诊，进行详细检查。",
            "low": "建议观察症状变化，如持续或加重，请及时就医。"
        }
        return recommendations.get(risk_level, recommendations["low"])

