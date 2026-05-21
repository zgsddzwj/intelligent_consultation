"""安全工具函数 - 增强版（JWT刷新令牌、密码强度验证、请求签名验证）"""
import re
import hmac
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import get_settings
from app.utils.logger import app_logger

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ========== 密码安全 ==========

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)


def check_password_strength(password: str) -> Tuple[bool, str, Dict[str, Any]]:
    """
    检查密码强度
    
    Returns:
        (是否通过, 提示信息, 详细评分)
    """
    score = 0
    max_score = 5
    checks = {
        "length": len(password) >= 8,
        "uppercase": bool(re.search(r'[A-Z]', password)),
        "lowercase": bool(re.search(r'[a-z]', password)),
        "digit": bool(re.search(r'\d', password)),
        "special": bool(re.search(r'[!@#$%^&*(),.?":{}|<>_\-=+\[\]\\/]', password))
    }
    
    score = sum(checks.values())
    
    if score < 3:
        return False, "密码强度不足，请包含大小写字母、数字和特殊字符", {
            "score": score, "max_score": max_score, "checks": checks
        }
    elif score < 4:
        return True, "密码强度一般", {"score": score, "max_score": max_score, "checks": checks}
    else:
        return True, "密码强度优秀", {"score": score, "max_score": max_score, "checks": checks}


# ========== JWT令牌管理（增强版） ==========

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌（短期有效）"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "type": "access",
        "iat": datetime.now(timezone.utc)
    })
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建刷新令牌（长期有效）
    
    刷新令牌用于在访问令牌过期后获取新的访问令牌，
    无需重新登录。
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=7)  # 默认7天
    
    # 生成唯一的令牌ID（用于撤销）
    jti = secrets.token_urlsafe(32)
    
    to_encode.update({
        "exp": expire,
        "type": "refresh",
        "jti": jti,
        "iat": datetime.now(timezone.utc)
    })
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """解码访问令牌"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        # 验证令牌类型
        if payload.get("type") != "access":
            app_logger.warning("尝试使用非访问令牌作为访问令牌")
            return None
        
        return payload
    except JWTError as e:
        app_logger.debug(f"JWT解码失败: {e}")
        return None


def decode_refresh_token(token: str) -> Optional[dict]:
    """解码刷新令牌"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        # 验证令牌类型
        if payload.get("type") != "refresh":
            app_logger.warning("尝试使用非刷新令牌作为刷新令牌")
            return None
        
        return payload
    except JWTError as e:
        app_logger.debug(f"刷新令牌解码失败: {e}")
        return None


def refresh_access_token(refresh_token: str) -> Optional[Dict[str, str]]:
    """
    使用刷新令牌获取新的访问令牌
    
    Returns:
        包含新访问令牌和刷新令牌的字典，或None（如果刷新令牌无效）
    """
    payload = decode_refresh_token(refresh_token)
    if not payload:
        return None
    
    # 提取用户信息（排除JWT元数据）
    user_data = {k: v for k, v in payload.items() if k not in ("exp", "type", "jti", "iat")}
    
    # 创建新的访问令牌和刷新令牌（轮换刷新令牌）
    new_access_token = create_access_token(user_data)
    new_refresh_token = create_refresh_token(user_data)
    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }


# ========== 请求签名验证 ==========

def generate_request_signature(
    method: str,
    path: str,
    timestamp: str,
    body: str = "",
    secret: str = None
) -> str:
    """
    生成请求签名
    
    使用HMAC-SHA256对请求进行签名，防止请求被篡改。
    
    Args:
        method: HTTP方法
        path: 请求路径
        timestamp: 时间戳
        body: 请求体（JSON字符串）
        secret: 签名密钥
        
    Returns:
        签名字符串
    """
    secret = secret or settings.SECRET_KEY
    
    # 构建签名字符串
    sign_string = f"{method}\n{path}\n{timestamp}\n{body}"
    
    # 使用HMAC-SHA256签名
    signature = hmac.new(
        secret.encode('utf-8'),
        sign_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return signature


def verify_request_signature(
    signature: str,
    method: str,
    path: str,
    timestamp: str,
    body: str = "",
    secret: str = None,
    max_age: int = 300  # 5分钟
) -> Tuple[bool, str]:
    """
    验证请求签名
    
    Args:
        signature: 待验证的签名
        method: HTTP方法
        path: 请求路径
        timestamp: 时间戳
        body: 请求体
        secret: 签名密钥
        max_age: 最大允许的时间差（秒）
        
    Returns:
        (是否验证通过, 错误信息)
    """
    # 检查时间戳是否过期（防止重放攻击）
    try:
        request_time = datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
        now = datetime.now(timezone.utc)
        if abs((now - request_time).total_seconds()) > max_age:
            return False, "请求已过期，请检查系统时间"
    except (ValueError, TypeError):
        return False, "无效的时间戳"
    
    # 重新计算签名
    expected_signature = generate_request_signature(method, path, timestamp, body, secret)
    
    # 使用恒定时间比较防止时序攻击
    if not hmac.compare_digest(signature, expected_signature):
        return False, "签名验证失败"
    
    return True, "验证通过"


# ========== 数据脱敏 ==========

def mask_sensitive_data(text: str) -> str:
    """脱敏处理"""
    if not text:
        return text
    
    # 脱敏身份证号
    text = re.sub(r'\d{17}[\dXx]', lambda m: m.group()[:6] + '********' + m.group()[-4:], text)
    
    # 脱敏手机号
    text = re.sub(r'1[3-9]\d{9}', lambda m: m.group()[:3] + '****' + m.group()[-4:], text)
    
    # 脱敏邮箱
    text = re.sub(r'([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', 
                  lambda m: m.group(1)[:2] + '***@' + m.group(2), text)
    
    # 脱敏银行卡号
    text = re.sub(r'\d{16,19}', lambda m: m.group()[:4] + ' **** **** ' + m.group()[-4:], text)
    
    return text


def mask_dict_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    递归脱敏字典中的敏感数据
    """
    if not isinstance(data, dict):
        return data
    
    sensitive_keys = {
        "password", "token", "api_key", "secret", "authorization",
        "credit_card", "ssn", "phone", "email", "id_card",
        "access_token", "refresh_token"
    }
    
    masked = {}
    for key, value in data.items():
        key_lower = key.lower()
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            if isinstance(value, str):
                if len(value) > 8:
                    masked[key] = value[:3] + "***" + value[-3:]
                else:
                    masked[key] = "***"
            else:
                masked[key] = "***"
        elif isinstance(value, dict):
            masked[key] = mask_dict_sensitive_data(value)
        elif isinstance(value, list):
            masked[key] = [
                mask_dict_sensitive_data(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            masked[key] = value
    
    return masked


# ========== 安全工具 ==========

def generate_secure_token(length: int = 32) -> str:
    """生成安全的随机令牌"""
    return secrets.token_urlsafe(length)


def generate_nonce() -> str:
    """生成一次性随机数（防止重放攻击）"""
    return secrets.token_hex(16)


def hash_sensitive_value(value: str, salt: str = None) -> str:
    """对敏感值进行哈希（用于日志记录等场景）"""
    salt = salt or settings.SECRET_KEY[:16]
    return hashlib.sha256(f"{value}{salt}".encode()).hexdigest()[:16]


DISCLAIMER = """
⚠️ 免责声明：
本系统仅提供医疗信息参考，不替代医生诊断和治疗。
具体医疗方案请遵医嘱。如有紧急情况，请立即就医或拨打急救电话。
"""
