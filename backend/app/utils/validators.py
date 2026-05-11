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


# 更全面的XSS防护模式
_XSS_PATTERNS = [
    (r'<script[^>]*>.*?</script>', '', re.IGNORECASE | re.DOTALL),
    (r'javascript:', '', re.IGNORECASE),
    (r'on\w+\s*=', '', re.IGNORECASE),  # 事件处理器
    (r'<iframe[^>]*>.*?</iframe>', '', re.IGNORECASE | re.DOTALL),
    (r'<object[^>]*>.*?</object>', '', re.IGNORECASE | re.DOTALL),
    (r'<embed[^>]*>', '', re.IGNORECASE),
    (r'data:text/html', '', re.IGNORECASE),
    (r'vbscript:', '', re.IGNORECASE),
]


def sanitize_user_input(text: str) -> str:
    """清理用户输入（增强XSS防护）"""
    for pattern, replacement, flags in _XSS_PATTERNS:
        text = re.sub(pattern, replacement, text, flags=flags)
    
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
        return False, "消息内容太长，请控制在5000字符以内"
    
    return True, ""


# 允许的图片MIME类型
ALLOWED_IMAGE_TYPES = {
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp',
}


def validate_image_file(content_type: str, file_size: int, max_size: int = 10 * 1024 * 1024) -> tuple[bool, str]:
    """验证图片文件"""
    if content_type not in ALLOWED_IMAGE_TYPES:
        return False, f"不支持的文件类型: {content_type}，仅支持 JPG/PNG/GIF/WebP"
    
    if file_size > max_size:
        return False, f"文件大小超过限制，最大允许 {max_size / 1024 / 1024:.0f}MB"
    
    if file_size == 0:
        return False, "文件不能为空"
    
    return True, ""
