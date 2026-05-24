"""数据验证器 - 增强版（环境校验、输入验证增强、医疗专用验证）"""
import re
from typing import List, Dict, Any, Tuple, Optional


class RiskKeywords:
    """风险关键词（扩展版）"""
    HIGH_RISK_KEYWORDS = [
        "胸痛", "呼吸困难", "意识不清", "大出血", "剧烈疼痛",
        "休克", "昏迷", "抽搐", "急性", "紧急", "心梗", "脑出血",
        "心脏骤停", "窒息", "中毒", "溺水", "触电", "烧伤", "骨折"
    ]
    
    MEDIUM_RISK_KEYWORDS = [
        "持续发热", "持续疼痛", "反复", "加重", "恶化",
        "头晕", "恶心", "呕吐", "腹泻", "皮疹", "肿胀"
    ]
    
    LOW_RISK_KEYWORDS = [
        "轻微", "偶尔", "轻微不适", "咨询", "了解"
    ]


def detect_high_risk_content(text: str) -> Dict[str, Any]:
    """检测高风险内容（增强版，支持风险评分）"""
    text_lower = text.lower()
    
    high_risk_found = []
    medium_risk_found = []
    low_risk_found = []
    
    for keyword in RiskKeywords.HIGH_RISK_KEYWORDS:
        if keyword in text_lower:
            high_risk_found.append(keyword)
    
    for keyword in RiskKeywords.MEDIUM_RISK_KEYWORDS:
        if keyword in text_lower:
            medium_risk_found.append(keyword)
    
    for keyword in RiskKeywords.LOW_RISK_KEYWORDS:
        if keyword in text_lower:
            low_risk_found.append(keyword)
    
    # 计算风险评分
    risk_score = len(high_risk_found) * 3 + len(medium_risk_found) * 1 - len(low_risk_found) * 0.5
    
    if high_risk_found:
        risk_level = "high"
    elif risk_score >= 2:
        risk_level = "medium"
    else:
        risk_level = "low"
    
    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "high_risk_keywords": high_risk_found,
        "medium_risk_keywords": medium_risk_found,
        "low_risk_keywords": low_risk_found,
        "requires_immediate_attention": risk_level == "high"
    }


# XSS防护模式
_XSS_PATTERNS = [
    (r'<script[^>]*>.*?</script>', '', re.IGNORECASE | re.DOTALL),
    (r'javascript:', '', re.IGNORECASE),
    (r'on\w+\s*=', '', re.IGNORECASE),
    (r'<iframe[^>]*>.*?</iframe>', '', re.IGNORECASE | re.DOTALL),
    (r'<object[^>]*>.*?</object>', '', re.IGNORECASE | re.DOTALL),
    (r'<embed[^>]*>', '', re.IGNORECASE),
    (r'data:text/html', '', re.IGNORECASE),
    (r'vbscript:', '', re.IGNORECASE),
    (r'<link[^>]*>', '', re.IGNORECASE),
    (r'<meta[^>]*>', '', re.IGNORECASE),
]


def sanitize_user_input(text: str, max_length: int = 5000) -> str:
    """清理用户输入（增强XSS防护）"""
    if not text:
        return ""
    
    for pattern, replacement, flags in _XSS_PATTERNS:
        text = re.sub(pattern, replacement, text, flags=flags)
    
    # 限制长度
    if len(text) > max_length:
        text = text[:max_length]
    
    return text.strip()


def validate_consultation_input(data: Dict[str, Any]) -> Tuple[bool, str]:
    """验证咨询输入（增强版）"""
    if not data or not isinstance(data, dict):
        return False, "请求数据无效"
    
    message = data.get("message")
    if not message:
        return False, "消息内容不能为空"
    
    if not isinstance(message, str):
        return False, "消息内容必须是字符串"
    
    message = message.strip()
    
    if len(message) < 2:
        return False, "消息内容太短，请至少输入2个字符"
    
    if len(message) > 5000:
        return False, "消息内容太长，请控制在5000字符以内"
    
    # 检查是否全为特殊字符
    if not re.search(r'[\u4e00-\u9fffa-zA-Z0-9]', message):
        return False, "消息内容应包含有效的文字或数字"
    
    return True, ""


# 允许的图片MIME类型
ALLOWED_IMAGE_TYPES = {
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp',
    'image/bmp',
}


def validate_image_file(content_type: str, file_size: int, max_size: int = 10 * 1024 * 1024) -> Tuple[bool, str]:
    """验证图片文件"""
    if not content_type:
        return False, "无法识别文件类型"
    
    if content_type not in ALLOWED_IMAGE_TYPES:
        return False, f"不支持的文件类型: {content_type}，仅支持 JPG/PNG/GIF/WebP/BMP"
    
    if file_size > max_size:
        return False, f"文件大小超过限制，最大允许 {max_size / 1024 / 1024:.0f}MB"
    
    if file_size == 0:
        return False, "文件不能为空"
    
    return True, ""


# ========== 环境校验 ==========

def validate_environment() -> Tuple[bool, List[str]]:
    """验证运行环境配置是否完整"""
    from app.config import get_settings
    settings = get_settings()
    
    errors = []
    warnings = []
    
    # 必需配置
    if not settings.DATABASE_URL:
        errors.append("DATABASE_URL: 数据库连接URL未配置")
    
    if not settings.SECRET_KEY:
        errors.append("SECRET_KEY: JWT密钥未配置")
    
    # LLM配置检查
    if settings.LLM_PROVIDER == "qwen" and not settings.QWEN_API_KEY:
        errors.append("QWEN_API_KEY: 使用Qwen但未配置API Key")
    elif settings.LLM_PROVIDER == "deepseek" and not settings.DEEPSEEK_API_KEY:
        errors.append("DEEPSEEK_API_KEY: 使用DeepSeek但未配置API Key")
    
    # 可选配置警告
    if not settings.REDIS_URL:
        warnings.append("REDIS_URL: Redis未配置，缓存功能将不可用")
    
    if not settings.NEO4J_PASSWORD:
        warnings.append("NEO4J_PASSWORD: Neo4j密码未配置，知识图谱功能可能不可用")
    
    if not settings.LANGFUSE_PUBLIC_KEY or not settings.LANGFUSE_SECRET_KEY:
        warnings.append("Langfuse密钥未配置，可观测性功能将不可用")
    
    return len(errors) == 0, errors + warnings


# ========== 医疗专用验证 ==========

def validate_medical_record_number(mrn: str) -> bool:
    """验证病历号格式"""
    if not mrn:
        return False
    # 支持数字、字母、连字符
    return bool(re.match(r'^[A-Za-z0-9\-]+$', mrn))


def validate_phone_number(phone: str) -> Tuple[bool, str]:
    """验证手机号格式"""
    if not phone:
        return False, "手机号不能为空"
    
    pattern = r'^1[3-9]\d{9}$'
    if re.match(pattern, phone):
        return True, ""
    
    return False, "手机号格式不正确"


def validate_id_card(id_card: str) -> Tuple[bool, str]:
    """验证身份证号格式（简单校验）"""
    if not id_card:
        return False, "身份证号不能为空"
    
    # 15位或18位
    pattern = r'(\d{15})|(\d{17}[\dXx])'
    if not re.match(pattern, id_card):
        return False, "身份证号格式不正确"
    
    return True, ""


def extract_medical_entities(text: str) -> Dict[str, List[str]]:
    """提取文本中的医疗实体（简单规则）"""
    entities = {
        "symptoms": [],
        "diseases": [],
        "drugs": [],
        "body_parts": []
    }
    
    # 常见症状关键词
    symptom_keywords = ["疼痛", "发热", "咳嗽", "头晕", "恶心", "呕吐", "腹泻", "皮疹"]
    for kw in symptom_keywords:
        if kw in text:
            entities["symptoms"].append(kw)
    
    # 常见疾病关键词
    disease_keywords = ["感冒", "流感", "高血压", "糖尿病", "心脏病", "肺炎"]
    for kw in disease_keywords:
        if kw in text:
            entities["diseases"].append(kw)
    
    return entities
