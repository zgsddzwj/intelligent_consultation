# 命名规范文档

## 工业级命名规范

本文档定义了系统的工业级命名规范，用于代码重构和后续开发。

## 命名规范映射表

### 目录结构映射

| 当前命名 | 工业级命名 | 说明 | 示例 |
|---------|-----------|------|------|
| `api/v1/` | `api/controllers/` | API控制器层 | `ConsultationController` |
| `services/` | `application/services/` | 应用服务层 | `ConsultationService` |
| `agents/` | `domain/agents/` | Agent领域模型 | `DoctorAgent` |
| `knowledge/` | `domain/knowledge/` | 知识领域模型 | `RAGSystem` |
| `models/` | `domain/entities/` | 领域实体 | `ConsultationEntity` |
| `database/` | `infrastructure/repositories/` | 数据访问层 | `ConsultationRepository` |
| `utils/` | `common/` | 通用工具 | `Logger`, `Security` |

### 文件命名规范

#### Controller层
- **命名**: `*_controller.py`
- **类名**: `*Controller`
- **示例**: 
  - `consultation_controller.py` → `ConsultationController`
  - `knowledge_controller.py` → `KnowledgeController`

#### Service层
- **命名**: `*_service.py`
- **类名**: `*Service`
- **示例**:
  - `consultation_service.py` → `ConsultationService`
  - `agent_service.py` → `AgentService`

#### Repository层
- **命名**: `*_repository.py`
- **类名**: `*Repository`
- **示例**:
  - `user_repository.py` → `UserRepository`
  - `consultation_repository.py` → `ConsultationRepository`

#### Domain层
- **命名**: `*_entity.py` 或 `*_model.py`
- **类名**: `*Entity` 或 `*Model`
- **示例**:
  - `consultation_entity.py` → `ConsultationEntity`
  - `user_entity.py` → `UserEntity`

#### Infrastructure层
- **命名**: `*_client.py` 或 `*_adapter.py`
- **类名**: `*Client` 或 `*Adapter`
- **示例**:
  - `llm_client.py` → `LLMClient`
  - `milvus_client.py` → `MilvusClient`
  - `neo4j_client.py` → `Neo4jClient`

## 推荐的目录结构

```
backend/app/
├── api/                          # API层
│   ├── controllers/              # 控制器
│   │   ├── consultation_controller.py
│   │   ├── agent_controller.py
│   │   ├── knowledge_controller.py
│   │   ├── user_controller.py
│   │   └── image_controller.py
│   ├── middleware/               # 中间件
│   │   ├── auth_middleware.py
│   │   ├── logging_middleware.py
│   │   └── error_middleware.py
│   ├── dto/                      # 数据传输对象
│   │   ├── request/
│   │   └── response/
│   └── exceptions/               # 异常定义
│
├── application/                  # 应用层
│   ├── services/                 # 应用服务
│   │   ├── consultation_service.py
│   │   ├── agent_service.py
│   │   ├── knowledge_service.py
│   │   └── user_service.py
│   ├── orchestrators/            # 编排器
│   │   └── agent_orchestrator.py
│   └── use_cases/                # 用例
│       ├── create_consultation.py
│       └── process_query.py
│
├── domain/                       # 领域层
│   ├── agents/                   # Agent领域
│   │   ├── doctor_agent.py
│   │   ├── health_manager_agent.py
│   │   ├── customer_service_agent.py
│   │   ├── operations_agent.py
│   │   └── tools/
│   │       ├── rag_tool.py
│   │       ├── kg_tool.py
│   │       └── diagnosis_tool.py
│   │
│   ├── knowledge/                # 知识领域
│   │   ├── rag/
│   │   │   ├── advanced_rag.py
│   │   │   ├── multi_retrieval.py
│   │   │   └── reranker.py
│   │   ├── graph/
│   │   │   ├── knowledge_graph.py
│   │   │   └── graph_builder.py
│   │   └── ml/
│   │       ├── intent_classifier.py
│   │       └── relevance_scorer.py
│   │
│   ├── consultation/             # 咨询领域
│   │   ├── consultation.py
│   │   └── session.py
│   │
│   └── entities/                 # 领域实体
│       ├── user.py
│       ├── consultation.py
│       └── knowledge_document.py
│
├── infrastructure/               # 基础设施层
│   ├── repositories/             # 数据访问
│   │   ├── user_repository.py
│   │   ├── consultation_repository.py
│   │   └── knowledge_repository.py
│   │
│   ├── external/                 # 外部服务
│   │   ├── llm/
│   │   │   └── qwen_client.py
│   │   ├── vector_db/
│   │   │   └── milvus_client.py
│   │   ├── graph_db/
│   │   │   └── neo4j_client.py
│   │   └── cache/
│   │       └── redis_client.py
│   │
│   ├── database/                 # 数据库配置
│   │   ├── session.py
│   │   └── migrations/
│   │
│   └── adapters/                 # 适配器
│       ├── document_adapter.py
│       └── image_adapter.py
│
├── common/                       # 通用层
│   ├── logger.py
│   ├── security.py
│   ├── validators.py
│   └── exceptions.py
│
└── config.py                     # 配置管理
```

## 类命名规范

### Controller类
```python
# 命名: *Controller
class ConsultationController:
    """咨询控制器"""
    pass

class KnowledgeController:
    """知识库控制器"""
    pass
```

### Service类
```python
# 命名: *Service
class ConsultationService:
    """咨询服务"""
    pass

class AgentService:
    """Agent服务"""
    pass
```

### Repository类
```python
# 命名: *Repository
class UserRepository:
    """用户仓储"""
    pass

class ConsultationRepository:
    """咨询仓储"""
    pass
```

### Entity类
```python
# 命名: *Entity 或 *Model
class UserEntity:
    """用户实体"""
    pass

class ConsultationEntity:
    """咨询实体"""
    pass
```

### Client类
```python
# 命名: *Client
class LLMClient:
    """LLM客户端"""
    pass

class MilvusClient:
    """Milvus客户端"""
    pass
```

## 方法命名规范

### Controller方法
- **查询**: `get_*`, `list_*`, `query_*`
- **创建**: `create_*`, `add_*`
- **更新**: `update_*`, `modify_*`
- **删除**: `delete_*`, `remove_*`
- **操作**: `process_*`, `execute_*`

### Service方法
- **业务操作**: `process_*`, `handle_*`, `execute_*`
- **查询**: `get_*`, `find_*`, `search_*`
- **创建**: `create_*`, `build_*`
- **更新**: `update_*`, `modify_*`

### Repository方法
- **查询**: `find_*`, `get_*`, `query_*`
- **保存**: `save_*`, `create_*`, `insert_*`
- **更新**: `update_*`, `modify_*`
- **删除**: `delete_*`, `remove_*`

## 变量命名规范

- **常量**: `UPPER_SNAKE_CASE` (如: `MAX_RETRY_COUNT`)
- **类名**: `PascalCase` (如: `ConsultationService`)
- **函数/方法**: `snake_case` (如: `process_consultation`)
- **私有方法**: `_snake_case` (如: `_validate_input`)
- **私有变量**: `_snake_case` (如: `_cache`)

## 模块命名规范

- **模块名**: `snake_case` (如: `consultation_service.py`)
- **包名**: `snake_case` (如: `application/services/`)
- **避免**: 使用连字符、空格、特殊字符

## 接口命名规范

### RESTful API
- **资源**: 复数名词 (如: `/api/v1/consultations`)
- **操作**: HTTP动词 (GET, POST, PUT, DELETE)
- **示例**:
  - `GET /api/v1/consultations` - 获取咨询列表
  - `POST /api/v1/consultations` - 创建咨询
  - `GET /api/v1/consultations/{id}` - 获取单个咨询
  - `PUT /api/v1/consultations/{id}` - 更新咨询
  - `DELETE /api/v1/consultations/{id}` - 删除咨询

### 内部接口
- **命名**: `I*` 或 `*Interface`
- **示例**: `IConsultationService`, `IUserRepository`

## 配置文件命名

- **环境配置**: `.env`, `.env.production`, `.env.development`
- **应用配置**: `config.py`, `settings.py`
- **部署配置**: `docker-compose.yml`, `kubernetes.yaml`

## 测试文件命名

- **单元测试**: `test_*.py`
- **集成测试**: `integration_test_*.py`
- **端到端测试**: `e2e_test_*.py`
- **示例**: `test_consultation_service.py`

## 文档命名

- **架构文档**: `ARCHITECTURE.md`
- **API文档**: `API.md` 或自动生成
- **部署文档**: `DEPLOYMENT.md`
- **开发文档**: `DEVELOPMENT.md`

## 重构建议

### 阶段1: 重命名文件
1. `api/v1/consultation.py` → `api/controllers/consultation_controller.py`
2. `services/llm_service.py` → `application/services/llm_service.py`
3. `models/user.py` → `domain/entities/user_entity.py`
4. `database/session.py` → `infrastructure/repositories/session_manager.py`

### 阶段2: 重命名类
1. 更新类名以符合规范
2. 更新导入语句
3. 更新测试文件

### 阶段3: 重构目录结构
1. 创建新的目录结构
2. 移动文件到新位置
3. 更新所有导入路径
4. 运行测试确保功能正常

## 注意事项

1. **向后兼容**: 重构时保持API向后兼容
2. **渐进式重构**: 分阶段进行，避免大规模改动
3. **测试覆盖**: 重构前确保有足够的测试覆盖
4. **文档更新**: 及时更新相关文档

