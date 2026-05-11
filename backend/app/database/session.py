"""数据库会话管理"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=3600,        # 连接回收时间：1小时
    pool_timeout=30,          # 连接池获取超时：30秒
    connect_args={
        "connect_timeout": 10,  # 数据库连接超时：10秒
    },
    echo=settings.DEBUG
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """连接建立时的回调（可扩展用于设置连接参数）"""
    pass


@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """连接检出时的回调，可用于连接健康检查"""
    pass
