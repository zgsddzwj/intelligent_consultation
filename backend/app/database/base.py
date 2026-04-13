"""数据库基类和模型工具

提供SQLAlchemy的声明式基类以及通用的数据库操作工具。
所有ORM模型都应继承自Base类。

Example:
    >>> from app.database.base import Base
    >>> from sqlalchemy import Column, Integer, String
    >>> 
    >>> class User(Base):
    ...     __tablename__ = 'users'
    ...     id = Column(Integer, primary_key=True)
    ...     name = Column(String(50))
"""
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import event
from sqlalchemy.orm import declared_attr
from datetime import datetime
import uuid


# 声明式基类 - 所有ORM模型的父类
Base = declarative_base()


class TimestampMixin:
    """时间戳混入类
    
    为模型自动添加 created_at 和 updated_at 字段。
    
    Usage:
        class MyModel(Base, TimestampMixin):
            __tablename__ = 'my_table'
            id = Column(Integer, primary_key=True)
    """
    
    @declared_attr
    def created_at(cls):
        """记录创建时间"""
        from sqlalchemy import Column, DateTime, func
        return Column(
            DateTime, 
            default=datetime.utcnow, 
            nullable=False,
            comment='创建时间'
        )
    
    @declared_attr
    def updated_at(cls):
        """记录最后更新时间"""
        from sqlalchemy import Column, DateTime, func
        return Column(
            DateTime, 
            default=datetime.utcnow, 
            onupdate=datetime.utcnow,
            nullable=False,
            comment='更新时间'
        )


class UUIDMixin:
    """UUID主键混入类
    
    使用UUID作为主键，适用于分布式系统或需要不可预测ID的场景。
    
    Usage:
        class MyModel(Base, UUIDMixin):
            __tablename__ = 'my_table'
            # 自动拥有 id 字段 (UUID类型)
    """
    
    @declared_attr
    def id(cls):
        from sqlalchemy import Column, String
        return Column(
            String(36), 
            primary_key=True, 
            default=lambda: str(uuid.uuid4()),
            comment='唯一标识符 (UUID)'
        )


class SoftDeleteMixin:
    """软删除混入类
    
    添加 deleted_at 字段实现软删除功能，
    不会真正删除数据，仅标记删除时间。
    
    Usage:
        class MyModel(Base, TimestampMixin, SoftDeleteMixin):
            __tablename__ = 'my_table'
            
        # 查询时过滤已删除记录
        # query.filter(MyModel.deleted_at == None)
    """
    
    @declared_attr
    def deleted_at(cls):
        from sqlalchemy import Column, DateTime
        return Column(
            DateTime, 
            nullable=True,
            default=None,
            comment='删除时间 (NULL表示未删除)'
        )
    
    @property
    def is_deleted(self) -> bool:
        """检查是否已被软删除"""
        return self.deleted_at is not None
    
    def soft_delete(self) -> None:
        """执行软删除"""
        self.deleted_at = datetime.utcnow()

