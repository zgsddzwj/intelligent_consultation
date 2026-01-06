# 测试指南

## 测试环境要求

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 环境变量配置

确保 `.env` 文件已配置（测试时会使用测试数据库，但某些模块仍需要配置）：

```bash
# 最小配置
DATABASE_URL=sqlite:///./test.db
REDIS_URL=redis://localhost:6379/0
QWEN_API_KEY=your_key_here
```

## 运行测试

### 基础导入测试（不依赖外部服务）

```bash
python tests/test_imports.py
```

这个测试验证：
- 异常模块导入
- 错误处理模块导入
- 重试模块导入
- 异常类功能

### 单元测试

```bash
# 运行所有单元测试
pytest tests/unit/ -v

# 运行特定测试文件
pytest tests/unit/test_exceptions.py -v

# 运行特定测试函数
pytest tests/unit/test_exceptions.py::test_base_exception -v
```

### 集成测试

```bash
pytest tests/integration/ -v
```

### 端到端测试

```bash
pytest tests/e2e/ -v
```

### 生成覆盖率报告

```bash
pytest --cov=app --cov-report=html --cov-report=term
```

## 测试分类

### 单元测试（Unit Tests）

- **位置**: `tests/unit/`
- **特点**: 测试单个函数/类，使用Mock隔离依赖
- **运行时间**: 快速（<1秒）

**当前测试**:
- `test_exceptions.py` - 异常类测试
- `test_transaction.py` - 事务管理测试
- `test_cache.py` - 缓存功能测试

### 集成测试（Integration Tests）

- **位置**: `tests/integration/`
- **特点**: 测试多个组件协作
- **运行时间**: 中等（1-10秒）

### 端到端测试（E2E Tests）

- **位置**: `tests/e2e/`
- **特点**: 测试完整业务流程
- **运行时间**: 较慢（>10秒）

## 测试Fixtures

### db_session

测试数据库会话，每个测试函数自动创建和清理。

```python
def test_my_function(db_session):
    # 使用db_session进行数据库操作
    pass
```

### client

FastAPI测试客户端，用于测试API端点。

```python
def test_api_endpoint(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
```

### mock_redis

Mock Redis服务，用于测试缓存相关功能。

```python
def test_cache_function(mock_redis):
    # 使用mock_redis进行缓存操作
    pass
```

### mock_llm_service

Mock LLM服务，用于测试LLM相关功能。

```python
def test_llm_function(mock_llm_service):
    # 使用mock_llm_service进行LLM操作
    pass
```

## 测试最佳实践

1. **测试隔离**: 每个测试应该独立，不依赖其他测试
2. **使用Mock**: 外部依赖（数据库、Redis、LLM）应该使用Mock
3. **测试命名**: 使用描述性的测试函数名
4. **断言清晰**: 使用明确的断言消息
5. **测试覆盖**: 目标覆盖率 >80%

## 常见问题

### 1. ModuleNotFoundError

**问题**: 缺少依赖包

**解决**: 
```bash
pip install -r requirements.txt
```

### 2. 数据库连接错误

**问题**: 测试时无法连接数据库

**解决**: 测试使用SQLite内存数据库，不需要真实数据库连接

### 3. Redis连接错误

**问题**: 测试时无法连接Redis

**解决**: 使用 `mock_redis` fixture，不需要真实Redis连接

## 持续集成

测试应该在CI/CD流程中自动运行：

```yaml
# .github/workflows/test.yml
- name: Run tests
  run: |
    pip install -r requirements.txt
    pytest tests/ -v --cov=app
```

## 下一步

- [ ] 添加更多单元测试
- [ ] 实现集成测试
- [ ] 实现端到端测试
- [ ] 设置CI/CD自动测试
- [ ] 提高测试覆盖率到80%+

