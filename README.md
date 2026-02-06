# 智能医疗管家平台

一个以AI医生Agent为核心的智能医疗管家平台，集成多Agent协同系统、高级RAG检索、Neo4j知识图谱、MCP服务器和React前端。

## 项目概述

本平台旨在为用户提供精准、可靠、个性化的健康服务，通过整合多种AI Agent（医学诊断、健康管家、客户服务、运营分析），利用最新的LLM技术与医疗知识图谱，构建智能医疗咨询系统。

主要特性：
- **多Agent协同**：基于LangGraph编排的专业分工Agent系统。
- **高级RAG**：混合检索（BM25+向量）、多路召回、重排序（BGE-Reranker）、结构化文档解析（MinerU/PDFPlumber）。
- **医疗知识图谱**：基于Neo4j构建的专业医疗图谱，支持实体识别与意图分类。
- **全链路监控**：集成Langfuse进行LLM可观测性监控。

## 技术栈

### 后端
- **核心框架**: Python 3.11+, FastAPI
- **AI/LLM**: LangChain, LangGraph, Qwen/Qwen-Med (DashScope)
- **RAG & 搜索**: Milvus (向量库), BM25, FlagEmbedding (Reranker), Jieba
- **知识图谱**: Neo4j
- **数据存储**: PostgreSQL (业务), Redis (缓存), MinIO (对象存储)
- **文档处理**: PDFPlumber, Mineru, PaddleOCR
- **监控**: Langfuse, Prometheus

### 前端
- **框架**: React 18 + TypeScript + Vite
- **UI组件**: Ant Design
- **状态管理**: Zustand, React Query
- **可视化**: 知识图谱可视化组件

### 部署
- Docker + Docker Compose (本地开发)
- Kubernetes (云部署)

## 项目结构

```
intelligent_consultation/
├── backend/          # 后端服务
├── frontend/         # 前端应用
├── data/             # 数据目录
├── docs/             # 文档
└── k8s/              # Kubernetes配置
```

## 快速开始

### 环境要求
- Docker & Docker Compose
- Python 3.11+ (可选，用于本地运行)
- Node.js 18+ (可选，用于本地运行前端)

### 最小可运行环境
- **仅后端 + LLM**：可只启动后端并配置 `QWEN_API_KEY`，问答可用（无 RAG/知识图谱时会有提示）。
- **完整能力**：需同时运行 **Neo4j**（知识图谱）、**Milvus**（向量检索）、**Redis**（缓存/限流）、**PostgreSQL**（业务库）。详见 `docker-compose.yml` 或 [QUICKSTART.md](QUICKSTART.md)。
- **知识图谱**：首次使用前**必须**执行一次 `python scripts/init_knowledge_graph.py`（或 `init_all.py`）以导入图谱数据，否则知识图谱检索为空。

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
# 等待服务启动后（约30秒），执行初始化
cd backend
python scripts/init_all.py
```
   - 其中 **知识图谱** 依赖：`init_knowledge_graph.py`（或 `init_all.py` 会调用）。未执行则知识图谱检索无数据，问答会提示「未找到相关知识库结果」。

5. 测试系统
```bash
cd backend
python scripts/test_system.py
```

6. 访问应用
- **前端问诊界面**: http://localhost:3000
- **知识图谱可视化**: http://localhost:3000/knowledge-graph
- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **Neo4j浏览器**: http://localhost:7474 (用户名/密码: neo4j/neo4j)

## 文档

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
- [高级RAG使用](docs/ADVANCED_RAG_USAGE.md) - RAG系统使用指南
- [高级RAG实现](docs/ADVANCED_RAG_IMPLEMENTATION.md) - RAG技术实现细节
- [知识图谱操作](docs/KG_OPERATIONS.md) - KG维护与操作手册
- [知识图谱优化](docs/KG_OPTIMIZATION.md) - KG性能与质量优化
- [对象存储实现](docs/OBJECT_STORAGE_IMPLEMENTATION.md) - MinIO集成说明

### 优化与维护
- [优化清单](docs/OPTIMIZATION_CHECKLIST.md) - 系统优化检查表
- [QA优化总结](docs/QA_OPTIMIZATION_SUMMARY.md) - 问答系统优化总结

## 查看日志

### 后端日志
```bash
# 应用日志文件
tail -f backend/logs/app.log

# 后台运行日志（如果使用nohup）
tail -f /tmp/backend.log
```

### 前端日志
```bash
# 后台运行日志（如果使用nohup）
tail -f /tmp/frontend.log

# 浏览器控制台（F12）
```

### 使用脚本查看
```bash
./view_logs.sh
```

详细说明请参考 [LOGGING.md](LOGGING.md)

## 开发指南

详细开发文档请参考 [docs/](docs/) 目录。

## 合规声明

本系统仅提供医疗信息参考，不替代医生诊断和治疗，具体医疗方案请遵医嘱。

## 许可证

[待定]

## 未来规划 (Roadmap)

1. **系统优化**:
   - 清理冗余脚本与测试文件
   - 优化后端服务模块拆分
   - 前端组件分层优化

2. **功能增强**:
   - 完善知识图谱的实时更新机制
   - 增强多模态诊断能力（图片分析）
   - 扩展更多医疗垂类模型支持

3. **运维升级**:
   - 完善Kubernetes资源配置
   - 增强日志归档与分析策略
   - 依赖包安全性审计与更新
