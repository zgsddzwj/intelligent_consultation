# 智能医疗管家平台 - 系统架构文档

## 架构总览

本系统采用**分层架构（Layered Architecture）**设计，遵循**领域驱动设计（DDD）**原则，使用工业级标准命名规范。

## 系统分层架构

```mermaid
graph TB
    subgraph Layer1["表现层 (Presentation Layer)"]
        WebUI[Web前端<br/>React + TypeScript]
        RESTAPI[REST API<br/>FastAPI Controllers]
    end
    
    subgraph Layer2["应用层 (Application Layer)"]
        Controllers[Controllers<br/>API路由处理]
        Services[Services<br/>业务逻辑服务]
        Orchestrator[Orchestrator<br/>工作流编排]
    end
    
    subgraph Layer3["领域层 (Domain Layer)"]
        Agents[Agent Domain<br/>业务领域模型]
        Knowledge[Knowledge Domain<br/>知识领域模型]
        Consultation[Consultation Domain<br/>咨询领域模型]
    end
    
    subgraph Layer4["基础设施层 (Infrastructure Layer)"]
        Repositories[Repositories<br/>数据访问]
        ExternalClients[External Clients<br/>外部服务客户端]
        Tools[Tools<br/>工具集成]
    end
    
    subgraph Layer5["数据层 (Data Layer)"]
        PostgreSQL[(PostgreSQL)]
        Redis[(Redis)]
        Neo4j[(Neo4j)]
        Milvus[(Milvus)]
    end
    
    WebUI --> RESTAPI
    RESTAPI --> Controllers
    Controllers --> Services
    Services --> Orchestrator
    Orchestrator --> Agents
    Orchestrator --> Knowledge
    Orchestrator --> Consultation
    Agents --> Repositories
    Knowledge --> Repositories
    Consultation --> Repositories
    Repositories --> PostgreSQL
    Repositories --> Redis
    Repositories --> Neo4j
    Repositories --> Milvus
    Services --> ExternalClients
    Agents --> Tools
    Knowledge --> Tools
```

## 详细架构图

```mermaid
graph TB
    subgraph Client["客户端层"]
        Browser[Web浏览器]
        Mobile[移动端<br/>可选]
    end
    
    subgraph Presentation["表现层"]
        Frontend[前端应用<br/>React SPA]
        APIGateway[API网关<br/>FastAPI]
    end
    
    subgraph Application["应用层"]
        ConsultationController[ConsultationController<br/>咨询控制器]
        AgentController[AgentController<br/>Agent控制器]
        KnowledgeController[KnowledgeController<br/>知识库控制器]
        UserController[UserController<br/>用户控制器]
        
        ConsultationService[ConsultationService<br/>咨询服务]
        AgentService[AgentService<br/>Agent服务]
        KnowledgeService[KnowledgeService<br/>知识服务]
        UserService[UserService<br/>用户服务]
        
        AgentOrchestrator[AgentOrchestrator<br/>Agent编排器]
    end
    
    subgraph Domain["领域层"]
        DoctorAgent[DoctorAgent<br/>医生Agent]
        HealthAgent[HealthManagerAgent<br/>健康管家Agent]
        ServiceAgent[CustomerServiceAgent<br/>客服Agent]
        OpsAgent[OperationsAgent<br/>运营Agent]
        
        AdvancedRAG[AdvancedRAG<br/>高级RAG系统]
        KnowledgeGraph[KnowledgeGraph<br/>知识图谱]
        MLModels[ML Models<br/>机器学习模型]
    end
    
    subgraph Infrastructure["基础设施层"]
        UserRepo[UserRepository<br/>用户仓储]
        ConsultationRepo[ConsultationRepository<br/>咨询仓储]
        KnowledgeRepo[KnowledgeRepository<br/>知识仓储]
        
        LLMClient[LLMClient<br/>LLM客户端]
        MilvusClient[MilvusClient<br/>向量数据库客户端]
        Neo4jClient[Neo4jClient<br/>图数据库客户端]
        RedisClient[RedisClient<br/>缓存客户端]
    end
    
    subgraph Data["数据层"]
        PG[(PostgreSQL<br/>业务数据)]
        Redis[(Redis<br/>缓存)]
        Neo4j[(Neo4j<br/>知识图谱)]
        Milvus[(Milvus<br/>向量数据库)]
    end
    
    Browser --> Frontend
    Mobile --> Frontend
    Frontend --> APIGateway
    APIGateway --> ConsultationController
    APIGateway --> AgentController
    APIGateway --> KnowledgeController
    APIGateway --> UserController
    
    ConsultationController --> ConsultationService
    AgentController --> AgentService
    KnowledgeController --> KnowledgeService
    UserController --> UserService
    
    ConsultationService --> AgentOrchestrator
    AgentService --> AgentOrchestrator
    
    AgentOrchestrator --> DoctorAgent
    AgentOrchestrator --> HealthAgent
    AgentOrchestrator --> ServiceAgent
    AgentOrchestrator --> OpsAgent
    
    DoctorAgent --> AdvancedRAG
    DoctorAgent --> KnowledgeGraph
    HealthAgent --> AdvancedRAG
    HealthAgent --> KnowledgeGraph
    
    AdvancedRAG --> MLModels
    KnowledgeGraph --> MLModels
    
    ConsultationService --> ConsultationRepo
    UserService --> UserRepo
    KnowledgeService --> KnowledgeRepo
    
    ConsultationRepo --> PG
    UserRepo --> PG
    KnowledgeRepo --> PG
    KnowledgeRepo --> Neo4j
    KnowledgeRepo --> Milvus
    
    AdvancedRAG --> MilvusClient
    KnowledgeGraph --> Neo4jClient
    ConsultationService --> RedisClient
    
    MilvusClient --> Milvus
    Neo4jClient --> Neo4j
    RedisClient --> Redis
    
    AdvancedRAG --> LLMClient
    DoctorAgent --> LLMClient
```

## 数据流架构

```mermaid
flowchart LR
    Start([用户查询]) --> Validate[输入验证]
    Validate --> RiskCheck[风险检测]
    RiskCheck --> Intent[意图分类]
    Intent --> Route{路由决策}
    
    Route -->|诊断| Doctor[DoctorAgent]
    Route -->|健康| Health[HealthAgent]
    Route -->|客服| Service[ServiceAgent]
    
    Doctor --> MultiRetrieval[多路召回]
    Health --> MultiRetrieval
    
    MultiRetrieval --> Vector[向量检索]
    MultiRetrieval --> BM25[BM25检索]
    MultiRetrieval --> Semantic[语义检索]
    MultiRetrieval --> KG[图谱检索]
    
    Vector --> RRF[RRF融合]
    BM25 --> RRF
    Semantic --> RRF
    KG --> RRF
    
    RRF --> Relevance[相关性评分]
    Relevance --> Rerank[Rerank]
    Rerank --> MLRerank[ML重排序]
    MLRerank --> Optimize[排序优化]
    
    Optimize --> LLM[LLM生成]
    LLM --> Risk[风险评估]
    Risk --> Save[保存记录]
    Save --> End([返回结果])
```

## 当前目录结构

```
backend/app/
├── api/                    # API层（表现层）
│   └── v1/                 # API版本1
│       ├── consultation.py # 咨询API
│       ├── agents.py       # Agent API
│       ├── knowledge.py    # 知识库API
│       └── users.py        # 用户API
│
├── services/               # 服务层（应用层）
│   ├── llm_service.py      # LLM服务
│   ├── milvus_service.py   # Milvus服务
│   └── redis_service.py    # Redis服务
│
├── agents/                 # Agent层（领域层）
│   ├── doctor_agent.py
│   ├── health_manager_agent.py
│   └── orchestrator.py
│
├── knowledge/              # 知识层（领域层）
│   ├── rag/                # RAG系统
│   ├── graph/              # 知识图谱
│   └── ml/                 # 机器学习
│
├── models/                 # 模型层（领域实体）
│   ├── user.py
│   ├── consultation.py
│   └── knowledge.py
│
├── database/               # 数据库层（基础设施层）
│   ├── session.py
│   └── base.py
│
└── utils/                  # 工具层（通用层）
    ├── logger.py
    └── security.py
```

## 推荐的工业级目录结构

```
backend/app/
├── api/                          # 表现层
│   ├── controllers/              # 控制器
│   │   ├── consultation_controller.py
│   │   ├── agent_controller.py
│   │   ├── knowledge_controller.py
│   │   └── user_controller.py
│   ├── middleware/               # 中间件
│   ├── dto/                      # 数据传输对象
│   └── exceptions/               # 异常定义
│
├── application/                  # 应用层
│   ├── services/                 # 应用服务
│   │   ├── consultation_service.py
│   │   ├── agent_service.py
│   │   └── knowledge_service.py
│   ├── orchestrators/            # 编排器
│   │   └── agent_orchestrator.py
│   └── use_cases/                # 用例
│
├── domain/                       # 领域层
│   ├── agents/                   # Agent领域
│   ├── knowledge/                # 知识领域
│   ├── consultation/             # 咨询领域
│   └── entities/                 # 领域实体
│
├── infrastructure/               # 基础设施层
│   ├── repositories/             # 数据访问
│   ├── external/                 # 外部服务
│   └── database/                 # 数据库配置
│
└── common/                       # 通用层
    ├── logger.py
    └── security.py
```

## 核心组件说明

### 1. 表现层 (Presentation Layer)

**职责**: 处理HTTP请求，参数验证，响应格式化

**组件**:
- **Controllers**: API控制器，处理HTTP请求
- **DTOs**: 数据传输对象，定义请求/响应格式
- **Middleware**: 中间件，处理认证、日志、错误等

**文件位置**: `backend/app/api/controllers/`

### 2. 应用层 (Application Layer)

**职责**: 业务逻辑实现，服务编排

**组件**:
- **Services**: 应用服务，实现业务逻辑
- **Orchestrators**: 编排器，协调多个服务
- **Use Cases**: 用例，封装特定业务场景

**文件位置**: `backend/app/application/`

### 3. 领域层 (Domain Layer)

**职责**: 核心业务逻辑，领域规则

**组件**:
- **Agents**: Agent领域模型
- **Knowledge**: 知识领域模型
- **Entities**: 领域实体

**文件位置**: `backend/app/domain/`

### 4. 基础设施层 (Infrastructure Layer)

**职责**: 技术实现，外部服务集成

**组件**:
- **Repositories**: 数据访问抽象
- **External Clients**: 外部服务客户端
- **Adapters**: 适配器，适配外部系统

**文件位置**: `backend/app/infrastructure/`

### 5. 数据层 (Data Layer)

**职责**: 数据持久化

**存储**:
- PostgreSQL: 业务数据
- Redis: 缓存数据
- Neo4j: 知识图谱
- Milvus: 向量数据

## 命名规范总结

| 层次 | 命名规范 | 示例 |
|-----|---------|------|
| Controller | `*Controller` | `ConsultationController` |
| Service | `*Service` | `ConsultationService` |
| Repository | `*Repository` | `UserRepository` |
| Entity | `*Entity` | `ConsultationEntity` |
| Client | `*Client` | `LLMClient` |
| Agent | `*Agent` | `DoctorAgent` |

## 技术栈映射

| 层次 | 技术栈 |
|-----|--------|
| 表现层 | FastAPI, Pydantic, React |
| 应用层 | Python, LangGraph |
| 领域层 | Python, Domain Models |
| 基础设施层 | SQLAlchemy, Redis, Neo4j, Milvus |
| 数据层 | PostgreSQL, Redis, Neo4j, Milvus |

