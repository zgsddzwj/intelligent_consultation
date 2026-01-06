# 系统架构总结

## 架构图总览

系统采用**五层架构**设计：

1. **表现层** (Presentation Layer) - 前端和API
2. **应用层** (Application Layer) - 业务逻辑和服务
3. **领域层** (Domain Layer) - 核心业务模型
4. **基础设施层** (Infrastructure Layer) - 数据访问和外部服务
5. **数据层** (Data Layer) - 数据存储

## 核心组件

### 表现层
- Web前端 (React)
- REST API (FastAPI)

### 应用层
- Controllers (API控制器)
- Services (应用服务)
- Orchestrator (工作流编排)

### 领域层
- Agents (Agent领域)
- Knowledge (知识领域)
- Consultation (咨询领域)

### 基础设施层
- Repositories (数据访问)
- External Clients (外部服务)
- Tools (工具集成)

### 数据层
- PostgreSQL (业务数据)
- Redis (缓存)
- Neo4j (知识图谱)
- Milvus (向量数据库)

## 命名规范

- Controller: `*Controller`
- Service: `*Service`
- Repository: `*Repository`
- Entity: `*Entity`
- Client: `*Client`

详细文档请参考 `ARCHITECTURE.md` 和 `NAMING_CONVENTIONS.md`
