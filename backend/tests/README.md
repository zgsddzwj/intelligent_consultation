# 测试文档

## 测试结构

```
tests/
├── conftest.py          # Pytest配置和fixtures
├── unit/                # 单元测试
│   ├── test_exceptions.py
│   ├── test_transaction.py
│   └── test_cache.py
├── integration/         # 集成测试
└── e2e/                 # 端到端测试
```

## 运行测试

### 运行所有测试
```bash
pytest
```

### 运行单元测试
```bash
pytest tests/unit/
```

### 运行集成测试
```bash
pytest tests/integration/
```

### 运行特定测试文件
```bash
pytest tests/unit/test_exceptions.py
```

### 运行特定测试函数
```bash
pytest tests/unit/test_exceptions.py::test_base_exception
```

### 生成覆盖率报告
```bash
pytest --cov=app --cov-report=html
```

## 测试标记

- `@pytest.mark.unit`: 单元测试
- `@pytest.mark.integration`: 集成测试
- `@pytest.mark.e2e`: 端到端测试
- `@pytest.mark.slow`: 慢速测试

## Fixtures

- `db_session`: 测试数据库会话
- `client`: FastAPI测试客户端
- `mock_redis`: Mock Redis服务
- `mock_llm_service`: Mock LLM服务

