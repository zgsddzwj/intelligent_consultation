"""安全模块单元测试"""
import pytest
from app.utils.security import (
    verify_password,
    get_password_hash,
    check_password_strength,
    create_access_token,
    decode_token,
    ReplayProtection,
    verify_request_signature,
    AuditLogger,
    DataEncryption,
    sanitize_input,
)


class TestPasswordSecurity:
    """密码安全测试"""

    def test_password_hash_and_verify(self):
        password = "TestPassword123!"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed)
        assert not verify_password("wrong", hashed)

    def test_password_strength_weak(self):
        passed, msg, details = check_password_strength("123")
        assert not passed
        assert details["score"] < 3

    def test_password_strength_strong(self):
        passed, msg, details = check_password_strength("TestP@ssw0rd!2024")
        assert passed
        assert details["score"] >= 4


class TestJWT:
    """JWT令牌测试"""

    def test_create_and_decode_access_token(self):
        token = create_access_token({"sub": "user123"})
        payload = decode_token(token)
        assert payload["sub"] == "user123"
        assert payload["type"] == "access"
        assert "jti" in payload

    def test_decode_invalid_token(self):
        assert decode_token("invalid.token.here") is None


class TestReplayProtection:
    """防重放攻击测试"""

    def test_valid_nonce(self):
        rp = ReplayProtection()
        nonce = rp.generate_nonce()
        assert rp.is_valid(nonce, time.time())

    def test_duplicate_nonce_rejected(self):
        rp = ReplayProtection()
        nonce = rp.generate_nonce()
        ts = time.time()
        assert rp.is_valid(nonce, ts)
        assert not rp.is_valid(nonce, ts)

    def test_expired_timestamp_rejected(self):
        rp = ReplayProtection()
        nonce = rp.generate_nonce()
        old_ts = time.time() - 400
        assert not rp.is_valid(nonce, old_ts)


class TestRequestSignature:
    """请求签名测试"""

    def test_valid_signature(self):
        import time as time_module
        import hmac
        import hashlib

        secret = "test_secret"
        ts = str(int(time_module.time()))
        nonce = "test_nonce_123"
        message = f"POST:/api/test:{{}}:{ts}:{nonce}"
        sig = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()

        assert verify_request_signature("POST", "/api/test", "{}", ts, nonce, sig, secret)

    def test_invalid_signature(self):
        assert not verify_request_signature("POST", "/api/test", "{}", "123", "nonce", "bad_sig", "secret")


class TestAuditLogger:
    """审计日志测试"""

    def test_sanitize_sensitive_data(self):
        data = {"username": "test", "password": "secret123", "api_key": "abc"}
        sanitized = AuditLogger._sanitize(data)
        assert sanitized["password"] == "***REDACTED***"
        assert sanitized["api_key"] == "***REDACTED***"
        assert sanitized["username"] == "test"


class TestDataEncryption:
    """数据加密测试"""

    def test_encrypt_field(self):
        encrypted = DataEncryption.encrypt_field("sensitive", "key123")
        assert len(encrypted) == 16

    def test_hash_and_verify(self):
        value = "test_value"
        hashed = DataEncryption.hash_sensitive(value)
        assert DataEncryption.verify_hashed(value, hashed)
        assert not DataEncryption.verify_hashed("wrong", hashed)


class TestInputSanitization:
    """输入净化测试"""

    def test_sanitize_script_tag(self):
        dirty = "<script>alert('xss')</script>"
        clean = sanitize_input(dirty)
        assert "<script" not in clean

    def test_sanitize_length_limit(self):
        long_text = "a" * 20000
        result = sanitize_input(long_text, max_length=1000)
        assert len(result) == 1000
