"""事务管理工具"""
from functools import wraps
from typing import Callable, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager
from app.database.session import SessionLocal
from app.utils.logger import app_logger
from app.common.exceptions import DatabaseException


def _resolve_db(db_param: str, args: tuple, kwargs: dict) -> Tuple[Session, bool]:
    """从函数参数中解析数据库会话，返回 (db, should_close)"""
    db = kwargs.get(db_param) or (args[0] if args and hasattr(args[0], db_param) else None)
    if db is None:
        db = SessionLocal()
        kwargs[db_param] = db
        return db, True
    return db, False


def _commit_transaction(db: Session, read_only: bool, func_name: str):
    """提交事务（非只读时）"""
    if not read_only:
        db.commit()
        app_logger.debug(f"事务提交成功: {func_name}")


def _rollback_transaction(db: Session, read_only: bool, func_name: str, error: Exception):
    """回滚事务并记录日志"""
    if not read_only:
        db.rollback()
    app_logger.error(f"事务回滚: {func_name}, {error}")


@contextmanager
def transaction_context(db: Session = None):
    """
    事务上下文管理器
    
    Usage:
        with transaction_context() as db:
            # 数据库操作
            pass
    """
    if db is None:
        db = SessionLocal()
        should_close = True
    else:
        should_close = False
    
    try:
        yield db
        db.commit()
        app_logger.debug("事务提交成功")
    except SQLAlchemyError as e:
        db.rollback()
        app_logger.error(f"事务回滚: {e}")
        raise DatabaseException(f"数据库操作失败: {str(e)}", error_code="4002")
    except Exception as e:
        db.rollback()
        app_logger.error(f"事务回滚（未知错误）: {e}")
        raise
    finally:
        if should_close:
            db.close()


def transactional(db_param: str = "db", read_only: bool = False):
    """
    事务装饰器
    
    Args:
        db_param: 数据库会话参数名，默认为"db"
        read_only: 是否为只读事务
    
    Usage:
        @transactional()
        def my_function(db: Session, ...):
            # 数据库操作
            pass
    """
    def decorator(func: Callable) -> Callable:
        import asyncio
        is_async = asyncio.iscoroutinefunction(func)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            db, should_close = _resolve_db(db_param, args, kwargs)
            try:
                result = await func(*args, **kwargs)
                _commit_transaction(db, read_only, func.__name__)
                return result
            except SQLAlchemyError as e:
                _rollback_transaction(db, read_only, func.__name__, e)
                raise DatabaseException(f"数据库操作失败: {str(e)}", error_code="4002")
            except Exception as e:
                _rollback_transaction(db, read_only, func.__name__, e)
                raise
            finally:
                if should_close:
                    db.close()
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            db, should_close = _resolve_db(db_param, args, kwargs)
            try:
                result = func(*args, **kwargs)
                _commit_transaction(db, read_only, func.__name__)
                return result
            except SQLAlchemyError as e:
                _rollback_transaction(db, read_only, func.__name__, e)
                raise DatabaseException(f"数据库操作失败: {str(e)}", error_code="4002")
            except Exception as e:
                _rollback_transaction(db, read_only, func.__name__, e)
                raise
            finally:
                if should_close:
                    db.close()
        
        return async_wrapper if is_async else sync_wrapper
    
    return decorator

