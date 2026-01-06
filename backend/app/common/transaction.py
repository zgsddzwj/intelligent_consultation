"""事务管理工具"""
from functools import wraps
from typing import Callable, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager
from app.database.session import SessionLocal
from app.utils.logger import app_logger
from app.common.exceptions import DatabaseException


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
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 获取数据库会话
            db = kwargs.get(db_param) or (args[0] if args and hasattr(args[0], db_param) else None)
            
            if db is None:
                # 如果没有传入db，创建新的会话
                db = SessionLocal()
                kwargs[db_param] = db
                should_close = True
            else:
                should_close = False
            
            try:
                result = await func(*args, **kwargs)
                if not read_only:
                    db.commit()
                    app_logger.debug(f"事务提交成功: {func.__name__}")
                return result
            except SQLAlchemyError as e:
                if not read_only:
                    db.rollback()
                app_logger.error(f"事务回滚: {func.__name__}, {e}")
                raise DatabaseException(f"数据库操作失败: {str(e)}", error_code="4002")
            except Exception as e:
                if not read_only:
                    db.rollback()
                app_logger.error(f"事务回滚（未知错误）: {func.__name__}, {e}")
                raise
            finally:
                if should_close:
                    db.close()
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 获取数据库会话
            db = kwargs.get(db_param) or (args[0] if args and hasattr(args[0], db_param) else None)
            
            if db is None:
                # 如果没有传入db，创建新的会话
                db = SessionLocal()
                kwargs[db_param] = db
                should_close = True
            else:
                should_close = False
            
            try:
                result = func(*args, **kwargs)
                if not read_only:
                    db.commit()
                    app_logger.debug(f"事务提交成功: {func.__name__}")
                return result
            except SQLAlchemyError as e:
                if not read_only:
                    db.rollback()
                app_logger.error(f"事务回滚: {func.__name__}, {e}")
                raise DatabaseException(f"数据库操作失败: {str(e)}", error_code="4002")
            except Exception as e:
                if not read_only:
                    db.rollback()
                app_logger.error(f"事务回滚（未知错误）: {func.__name__}, {e}")
                raise
            finally:
                if should_close:
                    db.close()
        
        # 判断是否为异步函数
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

