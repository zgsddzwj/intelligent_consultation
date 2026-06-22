# 🏥 智能医疗管家平台

<p align="center">
  <strong>一个以AI医生Agent为核心的智能医疗管家平台 v3.0</strong><br>
  集成多Agent协同系统、高级RAG检索、Neo4j知识图谱、ML模型训练和现代化React前端
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python" />
  <img src="https://img.shields.io/badge/React-18-blue.svg" alt="React" />
  <img src="https://img.shields.io/badge/FastAPI-0.100+-green.svg" alt="FastAPI" />
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License" />
  <img src="https://img.shields.io/badge/Platform-K8s/Docker-orange.svg" alt="Platform" />
  <img src="https://img.shields.io/badge/CI/CD-GitHub_Actions-success.svg" alt="CI/CD" />
  <img src="https://img.shields.io/github/actions/workflow/status/zgsddzwj/intelligent_consultation/ci.yml?branch=main&label=CI&style=flat-square" alt="GitHub Actions" />
  <img src="https://img.shields.io/badge/Version-3.0+-brightgreen.svg" alt="Version" />
  <img src="https://img.shields.io/badge/Commit-Active-brightgreen.svg" alt="Active" />
</p>

---

## 📋 版本演进

### 🛡️ 认证闭环
- ✅ **AuthGuard 组件** 实现基于角色的访问保护，支持 `allowedRoles` 配置
- ✅ **Login 页面** 登录成功后自动回跳至原访问页面
- ✅ 用户数据上下文 **user_id 全局关联**，支撑咨询记录绑定与查询
- ✅ **认证中间件** 统一 401 异常处理，前端拦截跳转登录页面
- ✅ 多环境 **配置对齐**，统一 JWT、RBAC、权限策略

### ⚡ 后端性能优化
- ✅ **`/health` 健康检查端点** 增加 Redis 缓存，降低依赖服务查询频率
- ✅ **`/live` 存活探针** 支持容器编排（Kubernetes/Liveness Probe）
- ✅ **Orchestrator Agent 编排器** 单例注入，避免重复初始化，提升线程安全
- ✅ **并行依赖检查** 在应用启动阶段预热数据库、Redis、Milvus、Neo4j 等服务

### 🚀 部署/CI 完善
- ✅ **GHCR (GitHub Container Registry)** 镜像仓库自动化构建与推送
- ✅ **Secrets 模板** 统一敏感信息配置，支持多环境部署
- ✅ **`start.sh` 健康等待** 应用启动前检测依赖服务就绪状态
- ✅ **冒烟测试** API 基本功能端到端验证，确保部署可用性
- ✅ **Trivy 漏洞扫描** 集成安全扫描，阻断高危镜像部署
- ✅ **代码覆盖率门禁** 单元测试覆盖率报告，强制质量阈值

### 🧹 代码质量提升
- ✅ 移除未使用的 `frontend/src/hooks/useAnimations.ts`，精简构建体积
- ✅ **`tsconfig.json` 路径别名** 映射优化（`@/` → `src/`）
- ✅ **复用 Chat 组件** 统一医患聊天气泡样式与交互逻辑
- ✅ **补充认证单元测试** `test_auth_middleware.py`、`test_users_auth.py`
- ✅ **修复导入异常** `test_imports.py` 解决模块循环依赖问题

### 🏗️ 模块功能增强
- ✅ **Agent 工作流状态 Redis 缓存**，支持 L1 LRU + Redis 跨实例缓存
- ✅ **LLM 服务连接池管理**，复用 HTTP 连接，自动重试与降级切换
- ✅ **数据库读写分离**，优化读库负载，支持动态连接池调整
- ✅ **多级缓存穿透防护**，布隆过滤器机制防止无效查询洪峰

### 🎯 工程化收尾整理
- ✅ **统一工程化规范**：Git 提交规范、分支策略、PR 模板、Changelog 生成
- ✅ **API 文档全面优化**：OpenAPI Schema 增强、Swagger 描述补充
- ✅ **全局错误码体系** 统一异常定义与响应格式，便于前后端错误定位

### 🧠 Prompt工程优化（3轮迭代）
- ✅ **Prompt优化1 - 系统提示词工程化**：结构化角色定义（Role/Profile/Goal/Constraints）、JSON Schema输出格式约束、丰富Few-shot示例、思维链（CoT）引导、风险分级体系
- ✅ **Prompt优化2 - 对话上下文管理优化**：意图感知的历史压缩、动态Token预算分配、多层级摘要策略（短期/中期/长期/意图摘要）、话题转移检测、IntentAnalyzer意图分析器（8种医疗意图）
- ✅ **Prompt优化3 - 安全与合规Prompt加固**：输入安全检查（敏感词/注入防护）、输出安全审查（免责声明/幻觉检测/有害内容过滤）、合规性验证（禁止确定诊断/禁止具体处方）、紧急情况强制就医协议、特殊人群保护（孕妇/儿童/老年人）

---

## ✨ 项目概述

本平台旨在为用户提供**精准、可靠、个性化**的健康服务，通过整合多种AI Agent（医学诊断、健康管家、客户服务、运营分析），利用最新的LLM技术与医疗知识图谱，构建新一代智能医疗咨询系统。

### 🎯 核心特性

| 特性 | 描述 |
|------|------|
| **🤖 多Agent协同** | 基于LangGraph编排的专业分工Agent系统（医生/健康管家/客服/运营），支持状态缓存与执行统计 |
| **🔍 高级RAG** | 混合检索（BM25+向量）、多路召回、BGE-Reranker重排序、结构化文档解析、语义缓存 |
| **📊 医疗知识图谱** | 基于Neo4j构建的专业医疗图谱，支持实体识别、关系推理、意图分类与查询缓存 |
| **🧠 ML模型训练** | 生产级ML流水线：SVM意图分类、相关性评分、排序优化、集成学习重排 |
| **👁️ 全链路监控** | Prometheus指标 + 告警规则引擎 + 性能剖析器(p50/p95/p99) + Langfuse LLM追踪 |
| **💅 现代化前端** | React 18 + TypeScript + Vite，代码分割懒加载、Zustand状态分层、暗色模式、响应式设计 |
| **🔐 企业级安全** | JWT认证、RBAC权限、防重放攻击、审计日志、数据加密、请求签名验证 |
| **⚡ 极致性能** | 多级缓存(L1 LRU + L2 Redis)、连接池、批量推理、读写分离、动态连接池调整 |

---

## 🛠️ 技术栈

### 后端
| 类别 | 技术 |
|------|------|
| **核心框架** | Python 3.11+, FastAPI, Uvicorn |
| **AI/LLM** | LangChain, LangGraph, Qwen (DashScope), DeepSeek |
| **RAG & 搜索** | Milvus (向量库), BM25, FlagEmbedding (Reranker), Jieba分词 |
| **知识图谱** | Neo4j (含APOC插件) |
| **数据存储** | PostgreSQL 15 (业务), Redis 7 (缓存), MinIO (对象存储) |
| **文档处理** | PDFPlumber, MinerU, PaddleOCR |
| **机器学习** | Scikit-learn (SVM/随机森林/梯度提升), GridSearchCV调优 |
| **监控告警** | Prometheus Client + 自定义告警规则引擎 + Profiler性能剖析 |
| **安全** | JWT + 防重放攻击 + 审计日志 + HMAC签名验证 |
| **工程化** | 统一响应包装、增强限流中间件、请求校验中间件、优雅关闭 |

### 前端
| 类别 | 技术 |
|------|------|
| **框架** | React 18 + TypeScript 5 + Vite 5 |
| **UI组件** | Ant Design 5 |
| **状态管理** | Zustand 4 (subscribeWithSelector + devtools + persist) |
| **数据获取** | @tanstack/react-query 5 |
| **可视化** | react-force-graph-2d (知识图谱力导向图) |
| **路由** | React Router DOM 6 (路由级懒加载) |
| **设计系统** | CSS变量、暗色模式、骨架屏、玻璃态效果、响应式布局 |

### 部署 & 基础设施
| 类别 | 技术 |
|------|------|
| **容器化** | Docker + Docker Compose |
| **编排** | Kubernetes (完整K8s配置) |
| **CI/CD** | GitHub Actions (代码质量/测试/性能/构建/发布全流程) |

---

## 📁 项目结构

```
intelligent_consultation/
├── backend/                      # 后端服务 (FastAPI)
│   ├── app/
│   │   ├── agents/              # 多Agent系统 (LangGraph编排)
│   │   │   ├── orchestrator.py   # Agent编排器 (状态缓存/指标统计/工作流可视化)
│   │   │   ├── doctor_agent.py   # 医生Agent
│   │   │   ├── health_manager_agent.py  # 健康管家Agent
│   │   │   ├── customer_service_agent.py # 客服Agent
│   │   │   ├── operations_agent.py      # 运营分析Agent
│   │   │   └── tools/             # Agent工具集
│   │   ├── api/
│   │   │   ├── v1/               # API v1版本 (health/consultation/users/image_analysis)
│   │   │   └── middleware/         # 中间件层 (认证/增强限流/响应包装/请求校验)
│   │   ├── common/              # 公共模块 (异常、加密、追踪、RBAC)
│   │   ├── database/            # 数据库 (PostgreSQL + 读写分离 + QueryOptimizer)
│   │   ├── infrastructure/      # 基础设施 (多级缓存、监控告警、限流、重试)
│   │   ├── knowledge/           # 知识层 (RAG + 知识图谱 + ML)
│   │   │   ├── rag/             # 高级RAG系统
│   │   │   ├── graph/           # Neo4j知识图谱 (LRU缓存/连接池/批量查询)
│   │   │   └── ml/              # ML模型 (意图分类等)
│   │   ├── models/              # SQLAlchemy数据模型
│   │   ├── services/            # 业务服务层
│   │   │   ├── llm_service.py   # LLM服务 (连接池/批量推理/智能降级/精确计费)
│   │   │   └── prompt_templates/  # Prompt模板管理
│   │   ├── utils/               # 工具类 (安全/验证/日志)
│   │   └── main.py              # 应用入口 (优雅启动/K8s probes/依赖预热)
│   ├── scripts/                 # 管理脚本
│   │   └── train_ml_models.py   # ML模型训练流水线
│   ├── tests/                   # 测试套件 (单元/集成/性能/工厂模式)
│   │   ├── unit/                # 单元测试
│   │   ├── integration/         # 集成测试
│   │   └── conftest.py          # Pytest配置 (Benchmark/工厂/覆盖率)
│   └── requirements.txt         # Python依赖
├── frontend/                    # 前端应用 (React + Vite)
│   ├── src/
│   │   ├── pages/               # 页面组件 (懒加载)
│   │   │   ├── PatientPortal.tsx     # 患者门户
│   │   │   ├── DoctorDashboard.tsx   # 医生工作台
│   │   │   ├── KnowledgeGraph.tsx    # 知识图谱可视化
│   │   │   └── AdminPanel.tsx        # 管理后台
│   │   ├── components/          # 通用UI组件
│   │   │   ├── DataTable.tsx         # 通用表格 (搜索/分页/刷新)
│   │   │   ├── ConfirmModal.tsx      # 确认对话框 (ARIA/键盘导航)
│   │   │   ├── EmptyState.tsx        # 空状态组件
│   │   │   ├── ErrorBoundary.tsx     # 错误边界
│   │   │   ├── SkeletonLoader.tsx    # 骨架屏
│   │   │   └── chat/                 # 聊天组件集
│   │   ├── hooks/               # 自定义Hooks
│   │   ├── services/            # API服务层 (统一响应/流式SSE)
│   │   ├── stores/              # Zustand状态管理 (分层/派生/精确订阅)
│   │   ├── App.tsx              # 应用布局 (代码分割/懒加载)
│   │   ├── main.tsx             # 入口文件 (主题配置)
│   │   └── index.css            # 全局样式 (CSS设计系统)
│   └── package.json
├── data/                        # 数据目录
├── docs/                        # 详细文档
├── k8s/                         # Kubernetes部署配置
├── .github/workflows/           # CI/CD工作流
│   └── ci.yml                   # 完整CI/CD流水线
├── docker-compose.yml           # Docker Compose编排
└── start.sh                     # 一键启动脚本
```

---

## 🚀 快速开始

### 环境要求
- Docker & Docker Compose
- Python 3.11+ (可选，用于本地运行)
- Node.js 18+ (可选，用于本地运行前端)

### 最小可运行环境
- **仅后端 + LLM**：可只启动后端并配置 `QWEN_API_KEY`，问答可用（无 RAG/知识图谱时会有提示）。
- **完整能力**：需同时运行 **Neo4j**（知识图谱）、**Milvus**（向量检索）、**Redis**（缓存/限流）、**PostgreSQL**（业务库）。详见 `docker-compose.yml`。
- **知识图谱**：首次使用前**必须**执行一次 `python scripts/init_knowledge_graph.py` 以导入图谱数据。
- **ML模型**：使用 `python scripts/train_ml_models.py` 训练所有ML模型。

### 一键启动（推荐）

1. 克隆项目
```bash
git clone https://github.com/zgsddzwj/intelligent_consultation.git
cd intelligent_consultation
```

2. 配置环境变量
```bash
# 编辑 backend/.env 文件，确认API密钥正确
```

3. 启动服务
```bash
chmod +x start.sh
./start.sh

# 或直接使用docker-compose
docker-compose up -d
```

4. 初始化数据（首次运行必须）
```bash
cd backend
python scripts/init_all.py
python scripts/train_ml_models.py
```

5. 访问应用
| 服务 | 地址 |
|------|------|
| **前端问诊界面** | http://localhost:3000 |
| **医生工作台** | http://localhost:3000/doctor |
| **知识图谱可视化** | http://localhost:3000/knowledge-graph |
| **管理后台** | http://localhost:3000/admin |
| **后端API** | http://localhost:8000 |
| **API文档(Swagger)** | http://localhost:8000/docs |
| **健康检查** | http://localhost:8000/health |
| **Prometheus指标** | http://localhost:8000/metrics |
| **Neo4j浏览器** | http://localhost:7474 |

---

## 🏗️ 架构亮点

### 后端架构

| 模块 | 核心能力 |
|------|---------|
| **应用启动** | `DependencyChecker` 并行依赖检查、服务预热、配置校验、K8s probes (`/health`/`/ready`/`/live`) |
| **Agent编排** | `OrchestratorMetrics` 指标收集、状态缓存 (LRU+TTL)、关键词静态缓存、工作流可视化 API |
| **LLM服务** | `LLMConnectionPool` 连接池、`LLMMetrics` 指标、智能 Provider 降级、`batch_generate` 批量推理 |
| **数据库** | `QueryOptimizer` 查询优化器、读写分离 (`get_read_db`)、动态连接池调整、慢查询检测 |
| **缓存系统** | 多级缓存 (L1 本地 LRU + L2 Redis)、`CacheWarmer` 预热器、L1/L2 命中率分别统计 |
| **监控告警** | 告警规则引擎 (normal→pending→firing 状态机)、`TracingContext` 分布式追踪、`Profiler` (p50/p95/p99) |
| **安全体系** | `ReplayProtection` 防重放、`AuditLogger` 审计日志 (脱敏)、`DataEncryption` 加密、请求签名验证 |

### 前端架构

| 模块 | 核心能力 |
|------|---------|
| **性能优化** | `React.lazy` 代码分割、路由级懒加载、`Suspense` 加载占位 |
| **状态管理** | Zustand 状态分层 (核心/UI/派生)、`subscribeWithSelector` 精确订阅、devtools 调试 |
| **组件库** | `DataTable` 通用表格、`ConfirmModal` 确认对话框 (ARIA/键盘导航)、统一索引导出 |

---

## 🧠 ML模型训练系统

```bash
# 训练所有模型
python scripts/train_ml_models.py

# 仅训练指定模型
python scripts/train_ml_models.py --model intent

# 使用自定义数据目录
python scripts/train_ml_models.py --data-dir ./data/training

# 输出详细报告
python scripts/train_ml_models.py --verbose
```

---

## 🧪 测试体系

```bash
cd backend

# 运行单元测试
pytest tests/unit/ -v --cov=app --cov-report=html

# 运行集成测试
pytest tests/integration/ -v

# 运行性能基准测试
pytest tests/ -k benchmark -v

# 并行测试 (加速)
pytest tests/unit/ -n auto --timeout=60
```

**测试特性：**
- ✅ `conftest.py` 增强 (Benchmark 性能基准 / 工厂模式 / 慢测试检测)
- ✅ 安全模块完整单元测试 (密码 / JWT / 防重放 / 签名 / 审计 / 加密)
- ✅ pytest-xdist 并行执行 + pytest-timeout 超时保护

---

## 🔄 CI/CD 流水线

GitHub Actions 工作流 (`.github/workflows/ci.yml`)：

| Stage | 说明 |
|-------|------|
| **Code Quality** | black / isort / flake8 / mypy / bandit 安全扫描 |
| **Backend Test** | 单元测试 + 集成测试 + 覆盖率报告上传 |
| **Frontend Test** | ESLint + TypeScript 类型检查 + 构建验证 |
| **Performance** | Locust 性能基准测试 |
| **Build Images** | Docker 镜像构建 + Trivy 漏洞扫描 |
| **Release** | 语义化版本发布 (SemVer) + 自动生成 Changelog |

---

## 📚 文档索引

| 文档 | 说明 |
|------|------|
| [快速开始指南](QUICKSTART.md) | 快速启动和配置 |
| [部署文档](DEPLOYMENT.md) | 部署方式和环境配置 |
| [架构文档](docs/ARCHITECTURE.md) | 系统架构设计 |
| [RAG使用指南](docs/RAG_GUIDE.md) | RAG系统使用指南 |
| [知识图谱指南](docs/KNOWLEDGE_GRAPH_GUIDE.md) | KG操作与维护 |
| [优化指南](docs/OPTIMIZATION_GUIDE.md) | 系统性能优化 |

---

## 🔧 开发指南

### 前端开发
```bash
cd frontend
npm install
npm run dev      # 开发模式 (http://localhost:3000)
npm run build    # 生产构建
npm run preview  # 预览构建结果
```

### 后端开发
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## ⚖️ 合规声明

本系统仅提供医疗信息参考，不替代医生诊断和治疗，具体医疗方案请遵医嘱。

---

## 📈 Roadmap

### 已完成 ✅
- [x] 多Agent协同系统 (LangGraph) + 状态缓存 + 执行统计
- [x] 高级RAG检索管道 + 语义缓存
- [x] Neo4j知识图谱 + LRU查询缓存
- [x] ML模型训练流水线 + 版本管理
- [x] 前端UI全面美化 + 代码分割懒加载
- [x] 多级缓存系统 (L1+L2)
- [x] LLM服务连接池 + 智能降级 + 批量推理
- [x] 监控告警引擎 + 性能剖析器
- [x] 企业级安全体系 (防重放/审计/加密)
- [x] 完整CI/CD流水线 (代码质量/测试/扫描/发布)

### 进行中 🔄
- [ ] 知识图谱实时更新机制
- [ ] 多模态诊断能力增强
- [ ] Kubernetes资源配置完善

### 规划中 📋
- [ ] 移动端App (React Native / Flutter)
- [ ] 更多垂类医疗模型支持
- [ ] 国际化(i18n)多语言支持
- [ ] 联邦学习隐私保护方案

---

## 📄 许可证

[MIT License](LICENSE)

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给一个Star！ ⭐**

Made with ❤️ by 智能医疗管家团队

</div>
