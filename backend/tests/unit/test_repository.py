"""Repository测试"""
import pytest
from app.infrastructure.repositories.user_repository import UserRepository
from app.infrastructure.repositories.consultation_repository import ConsultationRepository
from app.models.user import User, UserRole
from app.models.consultation import Consultation, ConsultationStatus, AgentType


@pytest.mark.unit
def test_user_repository_create(db_session):
    """测试用户Repository创建"""
    repo = UserRepository(db_session)
    user = repo.create(
        username="test_user",
        email="test@example.com",
        hashed_password="hashed_password",
        role=UserRole.PATIENT
    )
    assert user.id is not None
    assert user.username == "test_user"


@pytest.mark.unit
def test_user_repository_get_by_email(db_session):
    """测试根据邮箱获取用户"""
    repo = UserRepository(db_session)
    # 先创建用户
    user = repo.create(
        username="test_user",
        email="test@example.com",
        hashed_password="hashed_password",
        role=UserRole.PATIENT
    )
    db_session.commit()
    
    # 根据邮箱查询
    found_user = repo.get_by_email("test@example.com")
    assert found_user is not None
    assert found_user.email == "test@example.com"


@pytest.mark.unit
def test_consultation_repository_create(db_session):
    """测试咨询Repository创建"""
    repo = ConsultationRepository(db_session)
    consultation = repo.create(
        user_id=1,
        agent_type=AgentType.DOCTOR,
        status=ConsultationStatus.IN_PROGRESS
    )
    assert consultation.id is not None
    assert consultation.user_id == 1

