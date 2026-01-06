"""API集成测试"""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
def test_health_check(client: TestClient):
    """测试健康检查端点"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@pytest.mark.integration
def test_root_endpoint(client: TestClient):
    """测试根端点"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert "status" in data


@pytest.mark.integration
def test_metrics_endpoint(client: TestClient):
    """测试指标端点"""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers.get("Content-Type", "")


@pytest.mark.integration
def test_consultation_chat(client: TestClient):
    """测试咨询聊天端点"""
    response = client.post(
        "/api/v1/consultation/chat",
        json={
            "message": "我最近有点头疼，是什么原因？",
            "user_id": 1
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "consultation_id" in data


@pytest.mark.integration
def test_request_id_tracking(client: TestClient):
    """测试请求ID追踪"""
    response = client.get("/health")
    assert "X-Request-ID" in response.headers
    request_id = response.headers["X-Request-ID"]
    assert len(request_id) > 0

