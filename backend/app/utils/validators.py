"""数据验证器"""
import re
from typing import List, Dict, Any


class RiskKeywords:
    """风险关键词"""
    HIGH_RISK_KEYWORDS = [
        "胸痛", "呼吸困难", "意识不清", "大出血", "剧烈疼痛",
        "休克", "昏迷", "抽搐", "急性", "紧急", "心梗", "脑出血"
    ]
    
    MEDIUM_RISK_KEYWORDS = [
        "持续发热", "持续疼痛", "反复", "加重", "恶化"
    ]


def detect_high_risk_content(text: str) -> Dict[str, Any]:
    """检测高风险内容"""
    text_lower = text.lower()
    
    high_risk_found = []
    medium_risk_found = []
    
    for keyword in RiskKeywords.HIGH_RISK_KEYWORDS:
        if keyword in text_lower:
            high_risk_found.append(keyword)
    
    for keyword in RiskKeywords.MEDIUM_RISK_KEYWORDS:
        if keyword in text_lower:
            medium_risk_found.append(keyword)
    
    risk_level = "high" if high_risk_found else ("medium" if medium_risk_found else "low")
    
    return {
        "risk_level": risk_level,
        "high_risk_keywords": high_risk_found,
        "medium_risk_keywords": medium_risk_found,
        "requires_immediate_attention": risk_level == "high"
    }


def sanitize_user_input(text: str) -> str:
    """清理用户输入"""
    # 移除潜在的恶意代码
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
    
    # 限制长度
    max_length = 5000
    if len(text) > max_length:
        text = text[:max_length]
    
    return text.strip()


def validate_consultation_input(data: Dict[str, Any]) -> tuple[bool, str]:
    """验证咨询输入"""
    if not data.get("message"):
        return False, "消息内容不能为空"
    
    message = data["message"]
    if len(message) < 2:
        return False, "消息内容太短"
    
    if len(message) > 5000:
        return False, "消息内容太长"
    
    return True, ""

