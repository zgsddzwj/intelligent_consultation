"""Repository基类"""
from typing import Generic, TypeVar, Type, Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.database.base import Base
from app.common.exceptions import DatabaseException, NotFoundException, ErrorCode
from app.utils.logger import app_logger

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Repository基类 - 提供通用CRUD操作"""
    
    def __init__(self, model: Type[ModelType], db: Session):
        """
        初始化Repository
        
        Args:
            model: SQLAlchemy模型类
            db: 数据库会话
        """
        self.model = model
        self.db = db
    
    def get(self, id: Any) -> Optional[ModelType]:
        """根据ID获取单个记录"""
        try:
            return self.db.query(self.model).filter(self.model.id == id).first()
        except SQLAlchemyError as e:
            app_logger.error(f"查询失败: {e}")
            raise DatabaseException(f"查询失败: {str(e)}", error_code=ErrorCode.DATABASE_ERROR)
    
    def get_by_id_or_raise(self, id: Any) -> ModelType:
        """根据ID获取记录，不存在则抛出异常"""
        record = self.get(id)
        if not record:
            raise NotFoundException(
                f"{self.model.__name__} with id {id} not found",
                error_code=ErrorCode.DATA_NOT_FOUND
            )
        return record
    
    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None
    ) -> List[ModelType]:
        """获取所有记录（支持分页、过滤、排序）"""
        try:
            query = self.db.query(self.model)
            
            # 应用过滤条件
            if filters:
                for key, value in filters.items():
                    if hasattr(self.model, key):
                        query = query.filter(getattr(self.model, key) == value)
            
            # 应用排序
            if order_by:
                if order_by.startswith("-"):
                    # 降序
                    field = order_by[1:]
                    if hasattr(self.model, field):
                        query = query.order_by(getattr(self.model, field).desc())
                else:
                    # 升序
                    if hasattr(self.model, order_by):
                        query = query.order_by(getattr(self.model, order_by))
            
            # 应用分页
            return query.offset(skip).limit(limit).all()
        except SQLAlchemyError as e:
            app_logger.error(f"查询失败: {e}")
            raise DatabaseException(f"查询失败: {str(e)}", error_code=ErrorCode.DATABASE_ERROR)
    
    def create(self, **kwargs) -> ModelType:
        """创建新记录"""
        try:
            instance = self.model(**kwargs)
            self.db.add(instance)
            self.db.flush()  # 获取ID但不提交
            return instance
        except SQLAlchemyError as e:
            app_logger.error(f"创建失败: {e}")
            raise DatabaseException(f"创建失败: {str(e)}", error_code=ErrorCode.DATABASE_ERROR)
    
    def update(self, id: Any, **kwargs) -> ModelType:
        """更新记录"""
        try:
            instance = self.get_by_id_or_raise(id)
            for key, value in kwargs.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            self.db.flush()
            return instance
        except NotFoundException:
            raise
        except SQLAlchemyError as e:
            app_logger.error(f"更新失败: {e}")
            raise DatabaseException(f"更新失败: {str(e)}", error_code=ErrorCode.DATABASE_ERROR)
    
    def delete(self, id: Any) -> bool:
        """删除记录"""
        try:
            instance = self.get_by_id_or_raise(id)
            self.db.delete(instance)
            self.db.flush()
            return True
        except NotFoundException:
            raise
        except SQLAlchemyError as e:
            app_logger.error(f"删除失败: {e}")
            raise DatabaseException(f"删除失败: {str(e)}", error_code=ErrorCode.DATABASE_ERROR)
    
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """统计记录数"""
        try:
            query = self.db.query(self.model)
            if filters:
                for key, value in filters.items():
                    if hasattr(self.model, key):
                        query = query.filter(getattr(self.model, key) == value)
            return query.count()
        except SQLAlchemyError as e:
            app_logger.error(f"统计失败: {e}")
            raise DatabaseException(f"统计失败: {str(e)}", error_code=ErrorCode.DATABASE_ERROR)
    
    def exists(self, id: Any) -> bool:
        """检查记录是否存在"""
        try:
            return self.db.query(self.model).filter(self.model.id == id).first() is not None
        except SQLAlchemyError as e:
            app_logger.error(f"检查失败: {e}")
            raise DatabaseException(f"检查失败: {str(e)}", error_code=ErrorCode.DATABASE_ERROR)

