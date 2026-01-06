# 代码重构计划 - 工业级命名规范

## 重构目标

将当前代码结构重构为符合工业级标准的命名规范，提升代码可维护性和可扩展性。

## 重构原则

1. **渐进式重构**: 分阶段进行，不影响现有功能
2. **向后兼容**: 保持API接口不变
3. **测试驱动**: 重构前确保测试覆盖
4. **文档同步**: 及时更新文档

## 命名映射表

### 目录结构映射

| 当前路径 | 目标路径 | 说明 |
|---------|---------|------|
| `api/v1/consultation.py` | `api/controllers/consultation_controller.py` | 控制器层 |
| `api/v1/agents.py` | `api/controllers/agent_controller.py` | 控制器层 |
| `api/v1/knowledge.py` | `api/controllers/knowledge_controller.py` | 控制器层 |
| `api/v1/users.py` | `api/controllers/user_controller.py` | 控制器层 |
| `api/v1/image_analysis.py` | `api/controllers/image_controller.py` | 控制器层 |
| `services/llm_service.py` | `application/services/llm_service.py` | 应用服务层 |
| `services/milvus_service.py` | `infrastructure/external/milvus_client.py` | 基础设施层 |
| `services/redis_service.py` | `infrastructure/external/redis_client.py` | 基础设施层 |
| `agents/` | `domain/agents/` | 领域层 |
| `knowledge/` | `domain/knowledge/` | 领域层 |
| `models/` | `domain/entities/` | 领域实体 |
| `database/` | `infrastructure/repositories/` | 数据访问层 |
| `utils/` | `common/` | 通用层 |

### 类名映射

| 当前类名 | 目标类名 | 说明 |
|---------|---------|------|
| `router` (变量) | `*Controller` (类) | API控制器 |
| `LLMService` | `LLMClient` | 外部服务客户端 |
| `MilvusService` | `MilvusClient` | 外部服务客户端 |
| `RedisService` | `RedisClient` | 外部服务客户端 |
| `Neo4jClient` | `Neo4jClient` | 保持不变 |
| `User` (Model) | `UserEntity` | 领域实体 |
| `Consultation` (Model) | `ConsultationEntity` | 领域实体 |

## 重构步骤

### Phase 1: 创建新目录结构（不移动文件）

1. 创建新的目录结构
2. 创建适配器/包装类，保持向后兼容
3. 更新导入路径

### Phase 2: 重命名类和文件

1. 重命名Controller类
2. 重命名Service类
3. 重命名Repository类
4. 更新所有引用

### Phase 3: 移动文件到新位置

1. 移动文件到新目录
2. 更新导入路径
3. 运行测试确保功能正常

### Phase 4: 清理和优化

1. 删除旧文件
2. 更新文档
3. 代码审查

## 实施建议

由于重构涉及大量文件移动和重命名，建议：

1. **创建重构分支**: `git checkout -b refactor/industrial-naming`
2. **分模块重构**: 一次重构一个模块
3. **保持测试**: 确保所有测试通过
4. **代码审查**: 每个阶段进行代码审查

## 当前架构 vs 目标架构对比

### 当前架构
```
api/v1/consultation.py (router)
  → agents/orchestrator.py
    → agents/doctor_agent.py
      → knowledge/rag/hybrid_search.py
        → services/milvus_service.py
```

### 目标架构
```
api/controllers/consultation_controller.py (ConsultationController)
  → application/services/consultation_service.py (ConsultationService)
    → application/orchestrators/agent_orchestrator.py (AgentOrchestrator)
      → domain/agents/doctor_agent.py (DoctorAgent)
        → domain/knowledge/rag/advanced_rag.py (AdvancedRAG)
          → infrastructure/external/milvus_client.py (MilvusClient)
```

## 注意事项

1. **导入路径**: 需要更新所有导入语句
2. **测试文件**: 需要同步更新测试文件路径
3. **配置文件**: 可能需要更新配置引用
4. **文档**: 需要更新所有相关文档

## 重构检查清单

- [ ] 创建新目录结构
- [ ] 重命名Controller类
- [ ] 重命名Service类
- [ ] 重命名Repository类
- [ ] 重命名Entity类
- [ ] 重命名Client类
- [ ] 更新所有导入路径
- [ ] 更新测试文件
- [ ] 更新配置文件
- [ ] 更新文档
- [ ] 运行所有测试
- [ ] 代码审查
- [ ] 合并到主分支

