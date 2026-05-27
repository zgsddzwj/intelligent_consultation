"""安全工具函数 - 极致优化版（防重放攻击、审计日志、数据加密、请求签名）"""
import re
import hmac
import hashlib
import secrets
import time
import threading
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple, Set
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import get_settings
from app.utils.logger import app_logger

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ========== 密码安全 ==========

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def check_password_strength(password: str) -> Tuple[bool, str, Dict[str, Any]]:
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


# ========== JWT令牌管理 ==========

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "type": "access",
        "iat": datetime.now(timezone.utc),
        "jti": secrets.token_urlsafe(16)  # 唯一令牌ID
    })
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({
        "exp": expire,
        "type": "refresh",
        "iat": datetime.now(timezone.utc),
        "jti": secrets.token_urlsafe(16)
    })
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


# ========== 防重放攻击 ==========

class ReplayProtection:
    """请求重放保护器"""

    def __init__(self, window_seconds: int = 300):
        self._nonces: Set[str] = set()
        self._timestamps: Dict[str, float] = {}
        self._window = window_seconds
        self._lock = threading.Lock()

    def is_valid(self, nonce: str, timestamp: float) -> bool:
        """验证nonce是否有效"""
        with self._lock:
            now = time.time()

            # 时间戳检查（5分钟窗口）
            if abs(now - timestamp) > self._window:
                return False

            # nonce唯一性检查
            if nonce in self._nonces:
                return False

            self._nonces.add(nonce)
            self._timestamps[nonce] = now

            # 清理过期nonce
            self._cleanup(now)

            return True

    def _cleanup(self, now: float):
        """清理过期nonce"""
        expired = [n for n, ts in self._timestamps.items() if now - ts > self._window]
        for n in expired:
            self._nonces.discard(n)
            del self._timestamps[n]

    def generate_nonce(self) -> str:
        """生成唯一nonce"""
        return secrets.token_urlsafe(32)


replay_protection = ReplayProtection()


def verify_request_signature(
    method: str,
    path: str,
    body: str,
    timestamp: str,
    nonce: str,
    signature: str,
    secret: str
) -> bool:
    """验证请求签名（防篡改）"""
    try:
        # 时间戳检查
        ts = int(timestamp)
        if abs(time.time() - ts) > 300:
            return False

        # nonce检查
        if not replay_protection.is_valid(nonce, ts):
            return False

        # 签名验证
        message = f"{method}:{path}:{body}:{timestamp}:{nonce}"
        expected = hmac.new(
            secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected, signature)
    except Exception as e:
        app_logger.warning(f"签名验证失败: {e}")
        return False


# ========== 审计日志 ==========

class AuditLogger:
    """审计日志记录器"""

    SENSITIVE_FIELDS = {"password", "token", "secret", "api_key", "credit_card", "id_card"}

    @classmethod
    def log_access(
        cls,
        user_id: Optional[str],
        action: str,
        resource: str,
        result: str = "success",
        details: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """记录访问审计日志"""
        # 脱敏处理
        safe_details = cls._sanitize(details) if details else None

        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "result": result,
            "details": safe_details,
            "ip_address": ip_address,
            "user_agent": user_agent,
        }

        app_logger.info(f"AUDIT: {json.dumps(log_entry, ensure_ascii=False, default=str)}")

    @classmethod
    def log_security_event(
        cls,
        event_type: str,
        severity: str,
        description: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """记录安全事件"""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "severity": severity,
            "description": description,
            "user_id": user_id,
            "ip_address": ip_address,
        }

        if severity in ["high", "critical"]:
            app_logger.error(f"SECURITY: {json.dumps(log_entry, ensure_ascii=False, default=str)}")
        else:
            app_logger.warning(f"SECURITY: {json.dumps(log_entry, ensure_ascii=False, default=str)}")

    @classmethod
    def _sanitize(cls, data: Dict) -> Dict:
        """脱敏处理"""
        if not isinstance(data, dict):
            return data

        sanitized = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in cls.SENSITIVE_FIELDS):
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = cls._sanitize(value)
            else:
                sanitized[key] = value
        return sanitized


# ========== 数据加密 ==========

class DataEncryption:
    """数据加密工具"""

    @staticmethod
    def encrypt_field(value: str, key: Optional[str] = None) -> str:
        """简单字段加密（基于HMAC）"""
        if not value:
            return value
        secret = key or settings.SECRET_KEY
        return hmac.new(
            secret.encode(),
            value.encode(),
            hashlib.sha256
        ).hexdigest()[:16]

    @staticmethod
    def hash_sensitive(value: str) -> str:
        """敏感数据哈希（不可逆）"""
        if not value:
            return value
        salt = secrets.token_hex(8)
        hashed = hashlib.sha256(f"{value}{salt}".encode()).hexdigest()
        return f"{salt}${hashed}"

    @staticmethod
    def verify_hashed(value: str, hashed: str) -> bool:
        """验证哈希值"""
        if not hashed or "$" not in hashed:
            return False
        salt, hash_value = hashed.split("$", 1)
        expected = hashlib.sha256(f"{value}{salt}".encode()).hexdigest()
        return hmac.compare_digest(expected, hash_value)


# ========== 输入净化 ==========

def sanitize_input(text: str, max_length: int = 10000) -> str:
    """净化用户输入"""
    if not text:
        return text

    # 长度限制
    text = text[:max_length]

    # 移除危险字符
    dangerous = ["<script", "javascript:", "onerror=", "onload=", "eval(", "expression("]
    for pattern in dangerous:
        text = text.replace(pattern, "")

    return text


def validate_ip_address(ip: str) -> bool:
    """验证IP地址格式"""
    import ipaddress
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


# 导入json用于审计日志
import json
