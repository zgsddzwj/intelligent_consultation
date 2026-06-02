"""API集成测试"""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
def test_health_check(client: TestClient):
    """测试健康检查端点"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data.get("ready") is True
    assert "dependencies" in data


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
def test_live_and_ready_probes(client: TestClient):
    """测试 K8s 探针端点"""
    live = client.get("/live")
    assert live.status_code == 200
    assert live.json()["status"] == "alive"

    ready = client.get("/ready")
    assert ready.status_code in (200, 503)


@pytest.mark.integration
@pytest.mark.skip(reason="需要完整 LLM/数据库依赖，在 CI 中单独启用")
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
    payload = data.get("data", data)
    assert "answer" in payload
    assert "consultation_id" in payload


@pytest.mark.integration
def test_request_id_tracking(client: TestClient):
    """测试请求ID追踪"""
    response = client.get("/health")
    assert "X-Request-ID" in response.headers
    request_id = response.headers["X-Request-ID"]
    assert len(request_id) > 0
