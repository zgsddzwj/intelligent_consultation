"""依赖注入"""
from typing import Generator
from sqlalchemy.orm import Session
from app.database.session import SessionLocal
from app.config import get_settings

settings = get_settings()


def get_db() -> Generator[Session, None, None]:
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

