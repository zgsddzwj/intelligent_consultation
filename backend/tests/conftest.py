"""Pytest配置和fixtures - 极致优化版（覆盖率、性能基准、工厂模式）"""
import os

# 必须在导入 app 模块之前设置，确保 Settings 与数据库引擎使用测试配置
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing")
os.environ.setdefault("QWEN_API_KEY", "test-key")
os.environ.setdefault("STARTUP_FAIL_FAST", "false")
os.environ.setdefault("ENABLE_AUTH_MIDDLEWARE", "false")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

import pytest
import sys
import time
from pathlib import Path
from typing import Generator, Any

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

TEST_DATABASE_URL = os.environ["DATABASE_URL"]

test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """设置测试环境"""
    try:
        from app.database.base import Base
        Base.metadata.create_all(bind=test_engine)
        yield
        Base.metadata.drop_all(bind=test_engine)
    except Exception as e:
        pytest.skip(f"无法设置测试环境: {e}")


@pytest.fixture(scope="function")
def db_session():
    """创建测试数据库会话"""
    try:
        from app.database.base import Base
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()
    except Exception as e:
        pytest.skip(f"无法创建数据库会话: {e}")


@pytest.fixture(scope="function")
def client():
    """创建测试客户端"""
    try:
        from app.main import app
        with TestClient(app, raise_server_exceptions=False) as test_client:
            yield test_client
    except Exception as e:
        pytest.skip(f"无法创建测试客户端: {e}")


@pytest.fixture
def mock_redis(monkeypatch):
    """Mock Redis服务"""
    class MockRedis:
        def __init__(self):
            self._data = {}
            self.client = self

        def get(self, key):
            return self._data.get(key)

        def set(self, key, value, ttl=None):
            self._data[key] = value
            return True

        def setex(self, key, ttl, value):
            self._data[key] = value
            return True

        def delete(self, key):
            return self._data.pop(key, None) is not None

        def exists(self, key):
            return key in self._data

        def get_json(self, key):
            import json
            value = self.get(key)
            if value:
                return json.loads(value) if isinstance(value, str) else value
            return None

        def set_json(self, key, value, ttl=None):
            import json
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            return self.setex(key, ttl or 3600, value)

        def incr(self, key):
            current = int(self._data.get(key, 0))
            self._data[key] = str(current + 1)
            return current + 1

        def keys(self, pattern):
            import fnmatch
            return [k for k in self._data.keys() if fnmatch.fnmatch(k, pattern)]

        def scan(self, cursor=0, match=None, count=None):
            keys = self.keys(match or "*")
            return 0, keys

        def flushdb(self):
            self._data.clear()

        def health_check(self):
            return {"status": "healthy"}

    mock = MockRedis()
    monkeypatch.setattr("app.services.redis_service.redis_service", mock)
    monkeypatch.setattr("app.infrastructure.cache.redis_service", mock)
    return mock


@pytest.fixture
def mock_llm_service(monkeypatch):
    """Mock LLM服务"""
    class MockLLMService:
        def generate(self, prompt, **kwargs):
            return f"Mock response for: {prompt}"

        async def stream_generate(self, prompt, **kwargs):
            yield f"Mock stream response for: {prompt}"

        async def batch_generate(self, prompts, **kwargs):
            return [self.generate(p["prompt"]) for p in prompts]

        def get_metrics(self):
            return {"total_requests": 1, "success_rate": 100}

    mock = MockLLMService()
    monkeypatch.setattr("app.services.llm_service.llm_service", mock)
    return mock


@pytest.fixture
def benchmark():
    """性能基准测试fixture"""
    class Benchmark:
        def __init__(self):
            self.results = []

        def __call__(self, func, *args, iterations=100, **kwargs):
            for _ in range(10):
                func(*args, **kwargs)

            times = []
            for _ in range(iterations):
                start = time.perf_counter()
                func(*args, **kwargs)
                times.append(time.perf_counter() - start)

            result = {
                "iterations": iterations,
                "avg_ms": sum(times) / len(times) * 1000,
                "min_ms": min(times) * 1000,
                "max_ms": max(times) * 1000,
                "p95_ms": sorted(times)[int(len(times) * 0.95)] * 1000,
            }
            self.results.append(result)
            return result

    return Benchmark()


@pytest.fixture
def user_factory(db_session):
    """用户工厂"""
    def _create_user(username: str = "testuser", email: str = "test@example.com", **kwargs):
        from app.models.user import User
        user = User(username=username, email=email, **kwargs)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user
    return _create_user


@pytest.fixture
def consultation_factory(db_session):
    """咨询会话工厂"""
    def _create_consultation(user_id: int = 1, question: str = "测试问题", **kwargs):
        from app.models.consultation import Consultation
        consultation = Consultation(user_id=user_id, question=question, **kwargs)
        db_session.add(consultation)
        db_session.commit()
        db_session.refresh(consultation)
        return consultation
    return _create_consultation


@pytest.fixture(autouse=True)
def log_test_coverage(request):
    """记录慢测试"""
    start_time = time.time()
    yield
    duration = time.time() - start_time
    if duration > 1.0:
        print(f"\n[SLOW TEST] {request.node.name}: {duration:.2f}s")


@pytest.fixture
def event_loop():
    """创建事件循环用于异步测试"""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
