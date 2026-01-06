"""依赖注入"""
from typing import Generator
from fastapi import Depends
from sqlalchemy.orm import Session
from app.database.session import SessionLocal
from app.config import get_settings
from app.infrastructure.repositories.user_repository import UserRepository
from app.infrastructure.repositories.consultation_repository import ConsultationRepository
from app.infrastructure.repositories.knowledge_repository import KnowledgeRepository

settings = get_settings()


def get_db() -> Generator[Session, None, None]:
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    """获取用户Repository"""
    return UserRepository(db)


def get_consultation_repository(db: Session = Depends(get_db)) -> ConsultationRepository:
    """获取咨询Repository"""
    return ConsultationRepository(db)


def get_knowledge_repository(db: Session = Depends(get_db)) -> KnowledgeRepository:
    """获取知识库Repository"""
    return KnowledgeRepository(db)

