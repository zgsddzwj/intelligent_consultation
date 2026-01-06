"""数据库初始化脚本"""
from app.database.base import Base
from app.database.session import engine
from app.models import user, consultation, knowledge, agent
from app.utils.logger import app_logger
from app.database.indexes import create_indexes


def init_db():
    """初始化数据库表"""
    try:
        # 导入所有模型以确保它们被注册到Base.metadata
        # 这已经通过上面的import完成
        
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        app_logger.info("数据库表创建成功")
        
        # 创建索引
        create_indexes()
        app_logger.info("数据库索引创建完成")
    except Exception as e:
        app_logger.error(f"数据库初始化失败: {e}")
        raise


if __name__ == "__main__":
    init_db()

