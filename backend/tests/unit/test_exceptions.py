"""异常类测试"""
import pytest
from app.common.exceptions import (
    BaseAppException,
    BusinessException,
    ValidationException,
    NotFoundException,
    UnauthorizedException,
    ErrorCode
)


def test_base_exception():
    """测试基础异常类"""
    exc = BaseAppException("测试错误", error_code="TEST001")
    assert str(exc) == "测试错误"
    assert exc.error_code == "TEST001"
    assert exc.details == {}


def test_business_exception():
    """测试业务异常"""
    exc = BusinessException("业务错误", details={"field": "value"})
    assert exc.message == "业务错误"
    assert exc.details == {"field": "value"}


def test_validation_exception():
    """测试验证异常"""
    exc = ValidationException("验证失败")
    assert exc.message == "验证失败"


def test_not_found_exception():
    """测试未找到异常"""
    exc = NotFoundException("资源不存在")
    assert exc.message == "资源不存在"


def test_unauthorized_exception():
    """测试未授权异常"""
    exc = UnauthorizedException("未授权")
    assert exc.message == "未授权"

