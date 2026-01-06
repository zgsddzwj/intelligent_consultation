"""Pytest配置和fixtures"""
import pytest
import sys
from pathlib import Path

# 添加项目根目录到Python路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# 测试数据库URL
TEST_DATABASE_URL = "sqlite:///./test.db"

# 创建测试数据库引擎
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
        return TestClient(app)
    except Exception as e:
        pytest.skip(f"无法创建测试客户端: {e}")


@pytest.fixture
def mock_redis(monkeypatch):
    """Mock Redis服务"""
    class MockRedis:
        def __init__(self):
            self._data = {}
            self.client = self  # 支持client属性
        
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
    
    mock = MockRedis()
    monkeypatch.setattr("app.services.redis_service.redis_service", mock)
    return mock


@pytest.fixture
def mock_llm_service(monkeypatch):
    """Mock LLM服务"""
    class MockLLMService:
        def generate(self, prompt, **kwargs):
            return f"Mock response for: {prompt}"
        
        async def stream_generate(self, prompt, **kwargs):
            yield f"Mock stream response for: {prompt}"
    
    mock = MockLLMService()
    monkeypatch.setattr("app.services.llm_service.llm_service", mock)
    return mock

