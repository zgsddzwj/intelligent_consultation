"""核心模块导入冒烟测试（不依赖外部服务）"""
import importlib

import pytest


def _import(module: str):
    return importlib.import_module(module)


def test_exceptions_import():
    """异常模块导入"""
    mod = _import("app.common.exceptions")
    assert mod.BaseAppException is not None
    assert mod.ValidationException is not None
    assert mod.NotFoundException is not None
    assert mod.ErrorCode is not None


def test_error_handler_import():
    """错误处理器导入"""
    mod = _import("app.common.error_handler")
    assert mod.app_exception_handler is not None
    assert mod.validation_exception_handler is not None


def test_retry_import():
    """重试与熔断模块导入"""
    mod = _import("app.infrastructure.retry")
    assert mod.retry is not None
    assert mod.CircuitBreaker is not None


def test_config_import():
    """配置模块导入"""
    mod = _import("app.config")
    settings = mod.get_settings()
    assert settings.APP_NAME


def test_security_import():
    """安全工具导入"""
    mod = _import("app.utils.security")
    # 端到端小验证：创建并解码一个token
    token = mod.create_access_token({"sub": "1", "role": "patient"})
    payload = mod.decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "1"


def test_validators_import():
    """校验器导入"""
    mod = _import("app.utils.validators")
    ok, msg = mod.validate_image_file("image/png", 100)
    assert ok is True
    ok2, _ = mod.validate_image_file("application/zip", 100)
    assert ok2 is False


def test_transaction_import():
    """事务模块导入"""
    mod = _import("app.common.transaction")
    assert mod.transactional is not None
