"""用户认证 API 单元测试"""
import pytest
from app.models.user import User, UserRole
from app.utils.security import get_password_hash


@pytest.fixture
def registered_user(db_session):
    user = User(
        username="testauth",
        email="testauth@example.com",
        hashed_password=get_password_hash("TestPass123!"),
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_register_user(client):
    response = client.post(
        "/api/v1/users/register",
        json={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "SecurePass123!",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["username"] == "newuser"
    assert data["data"]["role"] == "patient"


def test_login_success(client, registered_user):
    response = client.post(
        "/api/v1/users/login",
        json={"username": "testauth", "password": "TestPass123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["access_token"]
    assert data["data"]["user_id"] == registered_user.id
    assert data["data"]["username"] == "testauth"


def test_login_wrong_password(client, registered_user):
    response = client.post(
        "/api/v1/users/login",
        json={"username": "testauth", "password": "WrongPassword!"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False
