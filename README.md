# 智能医疗管家平台

一个以AI医生Agent为核心的智能医疗管家平台，集成多Agent协同系统、RAG检索、Neo4j知识图谱、MCP服务器和React前端。

## 项目概述

本平台旨在为用户提供精准、可靠、个性化的健康服务，通过整合多种AI Agent（医学诊断、健康管家、客户服务、运营分析），利用最新的LLM技术与医疗知识图谱，构建智能医疗咨询系统。

## 技术栈

### 后端
- Python 3.11+
- FastAPI (API框架)
- LangChain + LangGraph (Agent编排)
- Qwen/Qwen-Med (LLM模型)
- Neo4j (知识图谱)
- Milvus (向量数据库)
- PostgreSQL (业务数据)
- Redis (缓存)

### 前端
- React 18 + TypeScript
- Vite (构建工具)
- Ant Design (UI组件库)
- React Query (数据获取)
- Zustand (状态管理)

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
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose

### 安装步骤

1. 克隆项目
```bash
git clone <repository-url>
cd intelligent_consultation
```

2. 配置环境变量
```bash
cp backend/.env.example backend/.env
# 编辑 backend/.env 文件，填入必要的配置
```

3. 启动服务
```bash
docker-compose up -d
```

4. 访问应用
- 前端: http://localhost:3000
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs

## 开发指南

详细开发文档请参考 [docs/](docs/) 目录。

## 合规声明

本系统仅提供医疗信息参考，不替代医生诊断和治疗，具体医疗方案请遵医嘱。

## 许可证

[待定]

