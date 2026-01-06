"""事务管理测试"""
import pytest
from app.common.transaction import transaction_context
from app.common.exceptions import DatabaseException
from sqlalchemy.exc import SQLAlchemyError


def test_transaction_context_success(db_session):
    """测试事务上下文成功提交"""
    with transaction_context(db_session) as db:
        # 模拟数据库操作
        assert db is not None


def test_transaction_context_rollback(db_session):
    """测试事务上下文回滚"""
    with pytest.raises(DatabaseException):
        with transaction_context(db_session) as db:
            # 模拟数据库错误
            raise SQLAlchemyError("数据库错误")

