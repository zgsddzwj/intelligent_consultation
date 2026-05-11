# 🏥 智能医疗管家平台

<p align="center">
  <strong>一个以AI医生Agent为核心的智能医疗管家平台 v2.0</strong><br>
  集成多Agent协同系统、高级RAG检索、Neo4j知识图谱、MCP服务器、ML模型训练和现代化React前端
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python" />
  <img src="https://img.shields.io/badge/React-18-blue.svg" alt="React" />
  <img src="https://img.shields.io/badge/FastAPI-0.100+-green.svg" alt="FastAPI" />
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License" />
  <img src="https://img.shields.io/badge/Platform-K8s/Docker-orange.svg" alt="Platform" />
</p>

---

## ✨ 项目概述

本平台旨在为用户提供**精准、可靠、个性化**的健康服务，通过整合多种AI Agent（医学诊断、健康管家、客户服务、运营分析），利用最新的LLM技术与医疗知识图谱，构建新一代智能医疗咨询系统。

### 🎯 核心特性

| 特性 | 描述 |
|------|------|
| **🤖 多Agent协同** | 基于LangGraph编排的专业分工Agent系统（医生/健康管家/客服/运营） |
| **🔍 高级RAG** | 混合检索（BM25+向量）、多路召回、BGE-Reranker重排序、结构化文档解析 |
| **📊 医疗知识图谱** | 基于Neo4j构建的专业医疗图谱，支持实体识别、关系推理与意图分类 |
| **🧠 ML模型训练** | 生产级ML流水线：SVM意图分类、相关性评分、排序优化、集成学习重排 |
| **👁️ 全链路监控** | 集成Langfuse进行LLM可观测性监控和Prometheus指标采集 |
| **💅 现代化前端** | React 18 + TypeScript + Ant Design 5，专业侧边导航、玻璃态UI、暗色模式 |
| **🔐 安全可靠** | JWT认证、RBAC权限控制、数据加密、限流保护 |

---

## 🛠️ 技术栈

### 后端
| 类别 | 技术 |
|------|------|
| **核心框架** | Python 3.11+, FastAPI, Uvicorn |
| **AI/LLM** | LangChain, LangGraph, Qwen/Qwen-Med (DashScope), DeepSeek |
| **RAG & 搜索** | Milvus (向量库), BM25, FlagEmbedding (Reranker), Jieba分词 |
| **知识图谱** | Neo4j (含APOC插件) |
| **数据存储** | PostgreSQL 15 (业务), Redis 7 (缓存), MinIO (对象存储) |
| **文档处理** | PDFPlumber, MinerU, PaddleOCR |
| **机器学习** | Scikit-learn (SVM/随机森林/梯度提升), GridSearchCV调优 |
| **监控** | Langfuse, Prometheus Client |

### 前端
| 类别 | 技术 |
|------|------|
| **框架** | React 18 + TypeScript 5 + Vite 5 |
| **UI组件** | Ant Design 5 (14+组件主题定制) |
| **状态管理** | Zustand 4 (persist中间件) + @tanstack/react-query 5 |
| **可视化** | react-force-graph-2d (知识图谱力导向图) |
| **路由** | React Router DOM 6 |
| **设计系统** | CSS变量v2.0、暗色模式、骨架屏、玻璃态效果 |

### 部署 & 基础设施
| 类别 | 技术 |
|------|------|
| **容器化** | Docker + Docker Compose |
| **编排** | Kubernetes (完整K8s配置) |
| **CI/CD** | GitHub Actions工作流 |

---

## 📁 项目结构

```
intelligent_consultation/
├── backend/                      # 后端服务 (FastAPI)
│   ├── app/
│   │   ├── agents/              # 多Agent系统 (LangGraph编排)
│   │   │   ├── orchestrator.py   # Agent编排器
│   │   │   ├── doctor_agent.py   # 医生Agent
│   │   │   ├── health_manager_agent.py  # 健康管家Agent
│   │   │   ├── customer_service_agent.py # 客服Agent
│   │   │   ├── operations_agent.py      # 运营分析Agent
│   │   │   └── tools/             # Agent工具集
│   │   │       ├── rag_tool.py        # RAG检索工具
│   │   │       ├── knowledge_graph_tool.py  # 知识图谱工具
│   │   │       ├── diagnosis_tool.py  # 诊断辅助工具
│   │   │       └── medical_query_tool.py    # 医疗查询工具
│   │   ├── api/                 # API路由和中间件
│   │   ├── common/              # 公共模块 (异常、加密、追踪)
│   │   ├── database/            # 数据库 (PostgreSQL + Alembic)
│   │   ├── infrastructure/      # 基础设施 (缓存、监控、限流)
│   │   ├── knowledge/           # 知识层 (RAG + 知识图谱 + ML)
│   │   │   ├── rag/             # 高级RAG系统
│   │   │   ├── graph/           # Neo4j知识图谱
│   │   │   └── ml/              # ML模型 (意图分类等)
│   │   ├── models/              # SQLAlchemy数据模型
│   │   ├── services/            # 业务服务层
│   │   ├── utils/               # 工具类
│   │   └── services/prompt_templates/  # Prompt模板管理
│   ├── scripts/                 # 管理脚本
│   │   └── train_ml_models.py   # ML模型训练流水线 (生产级)
│   ├── models/                  # 训练好的ML模型
│   │   ├── intent/              # 意图分类器
│   │   ├── relevance/           # 相关性评分器
│   │   ├── ranking/             # 排序优化器
│   │   └── reranker/            # ML重排序器
│   ├── tests/                   # 测试套件
│   └── requirements.txt         # Python依赖
├── frontend/                    # 前端应用 (React + Vite)
│   ├── src/
│   │   ├── pages/               # 页面组件
│   │   │   ├── PatientPortal.tsx     # 患者门户(聊天界面)
│   │   │   ├── DoctorDashboard.tsx   # 医生工作台
│   │   │   ├── KnowledgeGraph.tsx    # 知识图谱可视化
│   │   │   └── AdminPanel.tsx        # 管理后台
│   │   ├── components/          # 通用UI组件
│   │   │   ├── PageLoading.tsx       # 全局加载组件
│   │   │   ├── EmptyState.tsx        # 空状态组件
│   │   │   ├── ErrorBoundary.tsx     # 错误边界
│   │   │   ├── SkeletonLoader.tsx    # 骨架屏(5种类型)
│   │   │   └── ResponsiveContainer.tsx # 响应式容器
│   │   ├── hooks/               # 自定义Hooks
│   │   │   └── useAnimations.ts      # 交互体验Hooks集
│   │   ├── services/            # API服务层
│   │   │   ├── api.ts                # Axios实例(拦截器增强)
│   │   │   ├── consultation.ts       # 咨询API
│   │   │   └── knowledge.ts          # 知识库API
│   │   ├── stores/              # Zustand状态管理
│   │   │   └── consultation.ts       # 会话Store(persist)
│   │   ├── App.tsx              # 应用布局(侧边导航)
│   │   ├── main.tsx             # 入口文件(主题配置v2.0)
│   │   └── index.css            # 全局样式(CSS设计系统v2.0)
│   └── package.json
├── data/                        # 数据目录
│   ├── documents/               # 文档数据
│   │   ├── guidelines/          # 医疗指南
│   │   ├── manuals/             # 操作手册
│   │   └── papers/              # 学术论文
│   ├── knowledge_graph/         # 知识图谱数据
│   └── sample/                  # 示例数据
├── docs/                        # 详细文档
├── k8s/                         # Kubernetes部署配置
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
- **完整能力**：需同时运行 **Neo4j**（知识图谱）、**Milvus**（向量检索）、**Redis**（缓存/限流）、**PostgreSQL**（业务库）。详见 `docker-compose.yml` 或 [QUICKSTART.md](QUICKSTART.md)。
- **知识图谱**：首次使用前**必须**执行一次 `python scripts/init_knowledge_graph.py`（或 `init_all.py`）以导入图谱数据。
- **ML模型**：使用 `python scripts/train_ml_models.py` 训练所有ML模型（意图分类、相关性评分、排序优化、重排序器）。

### 一键启动（推荐）

1. 克隆项目
```bash
git clone https://github.com/zgsddzwj/intelligent_consultation.git
cd intelligent_consultation
```

2. 配置环境变量
```bash
# .env文件已创建，请确保QWEN_API_KEY已配置
# 编辑 backend/.env 文件，确认API密钥正确
```

3. 启动服务
```bash
# 使用启动脚本（推荐）
chmod +x start.sh
./start.sh

# 或直接使用docker-compose
docker-compose up -d
```

4. 初始化数据（首次运行必须）
```bash
cd backend

# 初始化全部数据（含知识图谱）
python scripts/init_all.py

# 或单独初始化知识图谱
python scripts/init_knowledge_graph.py

# 训练ML模型
python scripts/train_ml_models.py
```

5. 测试系统
```bash
cd backend
python scripts/test_system.py
```

6. 访问应用
| 服务 | 地址 |
|------|------|
| **前端问诊界面** | http://localhost:3000 |
| **医生工作台** | http://localhost:3000/doctor |
| **知识图谱可视化** | http://localhost:3000/knowledge-graph |
| **管理后台** | http://localhost:3000/admin |
| **后端API** | http://localhost:8000 |
| **API文档(Swagger)** | http://localhost:8000/docs |
| **Neo4j浏览器** | http://localhost:7474 (neo4j/neo4j) |

---

## 🧠 ML模型训练系统

平台内置了生产级的机器学习模型训练流水线：

### 支持的模型
| 模型 | 算法 | 用途 |
|------|------|------|
| **Intent Classifier** | SVM + GridSearchCV | 用户查询意图分类(8类) |
| **Relevance Scorer** | Random Forest | 查询-文档对相关性评估 |
| **Ranking Optimizer** | Gradient Boosting | 检索结果排序优化 |
| **ML Reranker** | SVM+RF+DT集成学习 | 多模型融合重排序 |

### 使用方式
```bash
# 训练所有模型
python scripts/train_ml_models.py

# 仅训练指定模型
python scripts/train_ml_models.py --model intent
python scripts/train_ml_models.py --model reranker

# 使用自定义数据目录
python scripts/train_ml_models.py --data-dir ./data/training

# 列出可用模型
python scripts/train_ml_models.py --list-models

# 输出详细报告
python scripts/train_ml_models.py --verbose
```

### 特性
- ✅ 自动超参数调优 (GridSearchCV + 交叉验证)
- ✅ 模板化数据生成（无需外部标注数据即可演示）
- ✅ 完整的训练报告输出 (JSON格式)
- ✅ 模型版本管理与回滚 (`ModelVersionManager`)
- ✅ CLI命令行接口 (argparse)
- ✅ 数据验证工具 (`ModelValidator`)

---

## 💅 前端设计系统 v2.0

前端采用全新的设计语言，提供专业级的用户体验：

### 设计亮点
- **CSS变量体系**: 50+设计token（颜色/阴影/圆角/间距/字体/动画）
- **暗色模式**: 自动适配 `prefers-color-scheme: dark`
- **动画系统**: 12种关键帧动画（fadeIn/scaleIn/float/typingDot等）
- **玻璃态效果**: `backdrop-filter: blur()` 毛玻璃风格
- **骨架屏**: shimmer加载动画，5种场景变体
- **响应式断点**: xs/sm/md/lg/xl/xxl 六级适配
- **无障碍**: reduced-motion、焦点可见性、跳过导航链接

### 页面概览
| 页面 | 路径 | 特点 |
|------|------|------|
| **患者门户** | `/` | AI聊天界面、快捷问题、风险标签、图片上传 |
| **医生工作台** | `/doctor` | 渐变统计卡片、功能模块、活动列表、待办任务 |
| **知识图谱** | `/knowledge-graph` | 力导向图可视化、统计面板、交互图例、节点详情 |
| **管理后台** | `/admin` | 服务监控表格、系统日志、用户/数据/安全管理 |

---

## 📚 文档索引

详细文档位于 `docs/` 目录：

### 基础指南
- [快速开始指南](QUICKSTART.md) - 快速启动和配置指南
- [部署文档](DEPLOYMENT.md) - 部署方式和环境配置
- [日志查看指南](LOGGING.md) - 如何查看前后端日志
- [完整设置指南](docs/COMPLETE_SETUP.md) - 详细的系统设置步骤

### 架构与设计
- [架构文档](docs/ARCHITECTURE.md) - 系统架构设计
- [命名规范](docs/NAMING_CONVENTIONS.md) - 代码命名与开发规范

### 核心功能实现
- [RAG使用指南](docs/RAG_GUIDE.md) - RAG系统使用指南
- [知识图谱指南](docs/KNOWLEDGE_GRAPH_GUIDE.md) - KG操作与维护手册
- [优化指南](docs/OPTIMIZATION_GUIDE.md) - 系统性能优化

---

## 🔧 开发指南

详细开发文档请参考 [docs/](docs/) 目录。

### 前端开发
```bash
cd frontend
npm install
npm run dev      # 开发模式 (http://localhost:5173)
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
- [x] 多Agent协同系统 (LangGraph)
- [x] 高级RAG检索管道
- [x] Neo4j知识图谱
- [x] ML模型训练流水线
- [x] 前端UI全面美化 v2.0
- [x] 模型版本管理系统

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
