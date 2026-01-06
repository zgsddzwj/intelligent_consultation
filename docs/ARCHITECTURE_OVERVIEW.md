# 智能医疗管家平台 - 架构总览

## 系统架构全景图

```mermaid
graph TB
    subgraph UserLayer["用户层"]
        WebUser[Web用户]
        MobileUser[移动用户]
    end
    
    subgraph PresentationLayer["表现层 (Presentation Layer)"]
        Frontend[前端应用<br/>React + TypeScript<br/>Port: 3000]
        APIGateway[API网关<br/>FastAPI<br/>Port: 8000]
    end
    
    subgraph ApplicationLayer["应用层 (Application Layer)"]
        ConsultationController[ConsultationController<br/>咨询控制器]
        AgentController[AgentController<br/>Agent控制器]
        KnowledgeController[KnowledgeController<br/>知识库控制器]
        UserController[UserController<br/>用户控制器]
        
        ConsultationService[ConsultationService<br/>咨询服务]
        AgentService[AgentService<br/>Agent服务]
        KnowledgeService[KnowledgeService<br/>知识服务]
        UserService[UserService<br/>用户服务]
        
        AgentOrchestrator[AgentOrchestrator<br/>工作流编排器<br/>LangGraph]
    end
    
    subgraph DomainLayer["领域层 (Domain Layer)"]
        subgraph AgentDomain["Agent领域"]
            DoctorAgent[DoctorAgent<br/>医生Agent]
            HealthAgent[HealthManagerAgent<br/>健康管家Agent]
            ServiceAgent[CustomerServiceAgent<br/>客服Agent]
            OpsAgent[OperationsAgent<br/>运营Agent]
        end
        
        subgraph KnowledgeDomain["知识领域"]
            AdvancedRAG[AdvancedRAG<br/>高级RAG系统]
            MultiRetrieval[MultiRetrieval<br/>多路召回]
            Reranker[Reranker<br/>重排序系统]
            KnowledgeGraph[KnowledgeGraph<br/>知识图谱系统]
            MLSystem[ML System<br/>机器学习系统]
        end
        
        subgraph ConsultationDomain["咨询领域"]
            ConsultationEntity[ConsultationEntity<br/>咨询实体]
            SessionEntity[SessionEntity<br/>会话实体]
        end
    end
    
    subgraph InfrastructureLayer["基础设施层 (Infrastructure Layer)"]
        subgraph RepositoryLayer["Repository层"]
            UserRepository[UserRepository<br/>用户仓储]
            ConsultationRepository[ConsultationRepository<br/>咨询仓储]
            KnowledgeRepository[KnowledgeRepository<br/>知识仓储]
        end
        
        subgraph ExternalServiceLayer["External Service层"]
            LLMClient[LLMClient<br/>Qwen API客户端]
            MilvusClient[MilvusClient<br/>向量数据库客户端]
            Neo4jClient[Neo4jClient<br/>图数据库客户端]
            RedisClient[RedisClient<br/>缓存客户端]
        end
        
        subgraph ToolLayer["Tool层"]
            RAGTool[RAGTool<br/>RAG检索工具]
            KGTool[KnowledgeGraphTool<br/>知识图谱工具]
            DiagnosisTool[DiagnosisTool<br/>诊断工具]
        end
    end
    
    subgraph DataLayer["数据层 (Data Layer)"]
        PostgreSQL[(PostgreSQL<br/>业务数据<br/>Port: 5432)]
        Redis[(Redis<br/>缓存<br/>Port: 6379)]
        Neo4j[(Neo4j<br/>知识图谱<br/>Port: 7474/7687)]
        Milvus[(Milvus<br/>向量数据库<br/>Port: 19530)]
    end
    
    subgraph ExternalAPIs["外部API服务"]
        QwenAPI[Qwen API<br/>LLM/Embedding/VL]
    end
    
    WebUser --> Frontend
    MobileUser --> Frontend
    Frontend -->|HTTP/WebSocket| APIGateway
    
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
    KnowledgeService --> AgentOrchestrator
    
    AgentOrchestrator --> DoctorAgent
    AgentOrchestrator --> HealthAgent
    AgentOrchestrator --> ServiceAgent
    AgentOrchestrator --> OpsAgent
    
    DoctorAgent --> AdvancedRAG
    DoctorAgent --> KnowledgeGraph
    DoctorAgent --> MLSystem
    HealthAgent --> AdvancedRAG
    HealthAgent --> KnowledgeGraph
    
    AdvancedRAG --> MultiRetrieval
    AdvancedRAG --> Reranker
    MultiRetrieval --> RAGTool
    Reranker --> MLSystem
    
    RAGTool --> MilvusClient
    RAGTool --> LLMClient
    KGTool --> Neo4jClient
    DiagnosisTool --> MLSystem
    
    ConsultationService --> ConsultationRepository
    UserService --> UserRepository
    KnowledgeService --> KnowledgeRepository
    
    UserRepository --> PostgreSQL
    ConsultationRepository --> PostgreSQL
    KnowledgeRepository --> PostgreSQL
    KnowledgeRepository --> Neo4j
    KnowledgeRepository --> Milvus
    
    ConsultationService --> RedisClient
    KnowledgeService --> RedisClient
    
    MilvusClient --> Milvus
    Neo4jClient --> Neo4j
    RedisClient --> Redis
    
    LLMClient --> QwenAPI
```

## 分层架构详解

### 1. 表现层 (Presentation Layer)

**职责**: 用户交互和API接口

**组件**:
- **Frontend**: React前端应用
- **API Gateway**: FastAPI网关，路由和认证

**技术栈**:
- React 18 + TypeScript
- FastAPI
- WebSocket (实时通信)

### 2. 应用层 (Application Layer)

**职责**: 业务逻辑编排

**组件**:
- **Controllers**: API控制器，处理HTTP请求
- **Services**: 应用服务，实现业务逻辑
- **Orchestrator**: 工作流编排器

**技术栈**:
- FastAPI
- LangGraph

### 3. 领域层 (Domain Layer)

**职责**: 核心业务逻辑

**组件**:
- **Agents**: Agent领域模型
- **Knowledge**: 知识领域模型
- **Consultation**: 咨询领域模型

**技术栈**:
- Python
- Domain Models

### 4. 基础设施层 (Infrastructure Layer)

**职责**: 技术实现

**组件**:
- **Repositories**: 数据访问
- **External Clients**: 外部服务客户端
- **Tools**: 工具集成

**技术栈**:
- SQLAlchemy
- Redis Client
- Neo4j Driver
- Milvus Client

### 5. 数据层 (Data Layer)

**职责**: 数据持久化

**存储**:
- PostgreSQL: 业务数据
- Redis: 缓存
- Neo4j: 知识图谱
- Milvus: 向量数据

## 核心数据流

### 咨询流程

```mermaid
sequenceDiagram
    participant User as 用户
    participant Frontend as 前端
    participant Controller as ConsultationController
    participant Service as ConsultationService
    participant Orchestrator as AgentOrchestrator
    participant Agent as DoctorAgent
    participant RAG as AdvancedRAG
    participant Repo as ConsultationRepository
    participant DB as PostgreSQL
    
    User->>Frontend: 1. 输入查询
    Frontend->>Controller: 2. POST /api/v1/consultation/chat
    Controller->>Service: 3. process_consultation()
    Service->>Orchestrator: 4. orchestrate()
    Orchestrator->>Agent: 5. route_to_agent()
    Agent->>RAG: 6. retrieve()
    RAG-->>Agent: 7. 返回检索结果
    Agent->>Service: 8. generate_response()
    Service->>Repo: 9. save()
    Repo->>DB: 10. INSERT
    DB-->>Repo: 11. 返回ID
    Repo-->>Service: 12. 返回记录
    Service-->>Controller: 13. 返回结果
    Controller-->>Frontend: 14. JSON响应
    Frontend-->>User: 15. 显示回答
```

### 知识检索流程

```mermaid
sequenceDiagram
    participant Agent as Agent
    participant RAG as AdvancedRAG
    participant MultiRetrieval as MultiRetrieval
    participant VectorRetrieval as VectorRetrieval
    participant BM25Retrieval as BM25Retrieval
    participant SemanticRetrieval as SemanticRetrieval
    participant KGRetrieval as KGRetrieval
    participant Reranker as Reranker
    participant MLReranker as MLReranker
    
    Agent->>RAG: 1. retrieve(query)
    RAG->>MultiRetrieval: 2. multi_retrieve()
    
    par 并行检索
        MultiRetrieval->>VectorRetrieval: 3a. 向量检索
        MultiRetrieval->>BM25Retrieval: 3b. BM25检索
        MultiRetrieval->>SemanticRetrieval: 3c. 语义检索
        MultiRetrieval->>KGRetrieval: 3d. 图谱检索
    end
    
    VectorRetrieval-->>MultiRetrieval: 4a. 结果
    BM25Retrieval-->>MultiRetrieval: 4b. 结果
    SemanticRetrieval-->>MultiRetrieval: 4c. 结果
    KGRetrieval-->>MultiRetrieval: 4d. 结果
    
    MultiRetrieval->>MultiRetrieval: 5. RRF融合
    MultiRetrieval->>Reranker: 6. rerank()
    Reranker->>MLReranker: 7. ml_rerank()
    MLReranker-->>Reranker: 8. 重排序结果
    Reranker-->>RAG: 9. 最终结果
    RAG-->>Agent: 10. 返回文档
```

## 技术栈总览

### 前端技术栈
- **框架**: React 18
- **语言**: TypeScript
- **构建**: Vite
- **UI库**: Ant Design
- **状态管理**: Zustand
- **数据获取**: React Query

### 后端技术栈
- **框架**: FastAPI
- **语言**: Python 3.11+
- **ORM**: SQLAlchemy
- **Agent框架**: LangChain + LangGraph
- **LLM**: Qwen/Qwen-Med

### 数据技术栈
- **关系数据库**: PostgreSQL
- **缓存**: Redis
- **图数据库**: Neo4j
- **向量数据库**: Milvus

### AI/ML技术栈
- **LLM**: Qwen API
- **Embedding**: Qwen Embedding
- **多模态**: Qwen-VL
- **Rerank**: BGE-Reranker
- **ML算法**: scikit-learn (SVM, 决策树)
- **OCR**: PaddleOCR

## 部署架构

```mermaid
graph TB
    subgraph Docker["Docker容器"]
        subgraph AppContainers["应用容器"]
            FrontendContainer[Frontend Container<br/>React App]
            BackendContainer[Backend Container<br/>FastAPI]
        end
        
        subgraph DataContainers["数据容器"]
            PGContainer[(PostgreSQL Container)]
            RedisContainer[(Redis Container)]
            Neo4jContainer[(Neo4j Container)]
            MilvusContainer[(Milvus Container)]
            EtcdContainer[(etcd Container)]
            MinioContainer[(MinIO Container)]
        end
    end
    
    subgraph External["外部服务"]
        QwenAPI[Qwen API<br/>云服务]
    end
    
    FrontendContainer --> BackendContainer
    BackendContainer --> PGContainer
    BackendContainer --> RedisContainer
    BackendContainer --> Neo4jContainer
    BackendContainer --> MilvusContainer
    MilvusContainer --> EtcdContainer
    MilvusContainer --> MinioContainer
    BackendContainer --> QwenAPI
```

## 端口分配

| 服务 | 端口 | 说明 |
|-----|------|------|
| Frontend | 3000 | React应用 |
| Backend API | 8000 | FastAPI |
| PostgreSQL | 5432 | 数据库 |
| Redis | 6379 | 缓存 |
| Neo4j HTTP | 7474 | 图数据库Web界面 |
| Neo4j Bolt | 7687 | 图数据库协议 |
| Milvus | 19530 | 向量数据库 |
| MinIO | 9000/9001 | 对象存储 |

## 关键设计模式

1. **分层架构**: 清晰的层次划分
2. **依赖注入**: 通过依赖注入管理组件
3. **仓储模式**: Repository模式抽象数据访问
4. **服务层模式**: Service层封装业务逻辑
5. **策略模式**: 多种检索策略
6. **工厂模式**: Agent工厂
7. **观察者模式**: 日志和监控

## 扩展性设计

1. **水平扩展**: 无状态设计，支持多实例
2. **垂直扩展**: 模块化设计，按需扩展
3. **插件化**: Agent工具插件化
4. **配置化**: 功能开关配置化

