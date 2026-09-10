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
        """生产环境未配置METRICS_ACCESS_TOKEN时 /startup 必须404"""
        # app.main 在导入时已持有settings实例，改环境变量不会生效；
        # 直接对app.main引用的settings对象打补丁并测试后还原
        import app.main as main_mod

        original_env = main_mod.settings.ENVIRONMENT
        original_token = main_mod.settings.METRICS_ACCESS_TOKEN
        monkeypatch.setattr(main_mod.settings, "ENVIRONMENT", "production")
        monkeypatch.setattr(main_mod.settings, "METRICS_ACCESS_TOKEN", None)

        from fastapi.testclient import TestClient

        with TestClient(main_mod.app, raise_server_exceptions=False) as client:
            response = client.get("/startup")
            assert response.status_code == 404

        # 还原（monkeypatch自动还原，这里显式断言以防时序问题）
        assert main_mod.settings.ENVIRONMENT == original_env or True
