"""生产就绪能力单元测试"""
import pytest
from app.utils.security import DISCLAIMER, decode_access_token, create_access_token, create_refresh_token
from app.services.cache_service import cache_service


class TestSecurityReadiness:
    def test_disclaimer_defined(self):
        assert "免责声明" in DISCLAIMER
        assert len(DISCLAIMER) > 20

    def test_decode_access_token_rejects_refresh_token(self):
        refresh = create_refresh_token({"sub": "1"})
        assert decode_access_token(refresh) is None

    def test_decode_access_token_accepts_access_token(self):
        access = create_access_token({"sub": "42", "role": "patient"})
        payload = decode_access_token(access)
        assert payload is not None
        assert payload["sub"] == "42"
        assert payload["type"] == "access"


class TestCacheHealth:
    def test_cache_health_check_structure(self):
        result = cache_service.health_check()
        assert "status" in result
        assert result["status"] in ("healthy", "unhealthy")


class TestStartupEndpointProtection:
    def test_startup_hidden_in_production_without_token(self, monkeypatch):
        pytest.importorskip("langgraph")
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.delenv("METRICS_ACCESS_TOKEN", raising=False)
        from app.config import get_settings
        get_settings.cache_clear()

        from app.main import app
        from fastapi.testclient import TestClient

        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/startup")
            assert response.status_code == 404

        get_settings.cache_clear()
        monkeypatch.setenv("ENVIRONMENT", "testing")
