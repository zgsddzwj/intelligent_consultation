# 智能医疗管家平台 - 文档中心

本文档目录包含项目的核心架构文档、技术指南和开发规范。

## 📚 核心文档

### 架构设计
- [系统架构 (ARCHITECTURE.md)](ARCHITECTURE.md)
  - 分层架构设计与模块依赖
  - 数据流向与技术栈
  - 对象存储与文档管理架构
  - **核心必读**：理解系统整体设计的入口

### 核心功能指南
- [RAG 系统指南 (RAG_GUIDE.md)](RAG_GUIDE.md)
  - **包含内容**：原 `ADVANCED_RAG_IMPLEMENTATION.md` 和 `ADVANCED_RAG_USAGE.md` 的整合
  - 混合检索策略 (Vector + BM25 + KG)
  - 重排序模型 (BGE-Reranker) 配置
  - 检索流程与 API 使用说明

- [知识图谱指南 (KNOWLEDGE_GRAPH_GUIDE.md)](KNOWLEDGE_GRAPH_GUIDE.md)
  - **包含内容**：原 `KG_OPERATIONS.md` 和 `KG_OPTIMIZATION.md` 的整合
  - 图谱导入与导出操作
  - 实体识别 (NER) 与关系抽取
  - 图谱查询优化与 Cypher 模板

- [系统优化与路线图 (OPTIMIZATION_GUIDE.md)](OPTIMIZATION_GUIDE.md)
  - **包含内容**：原 `OPTIMIZATION_*.md` 系列文档的整合
  - 已完成的 QA 优化清单
  - 性能瓶颈分析与推荐方案
  - 未来开发路线图

## 🛠️ 设置与部署

- [完整设置指南](../COMPLETE_SETUP.md) - 环境搭建与初始化
- [部署文档](../DEPLOYMENT.md) - Docker/K8s 部署说明
- [Kubernetes 部署](../k8s/README.md) - K8s 详细配置

## 📏 开发规范

- [命名规范 (NAMING_CONVENTIONS.md)](NAMING_CONVENTIONS.md) - 代码风格与命名约定

## 🔗 其他资源

- [项目主页](../README.md) - 项目概述与快速开始
- [脚本说明](../backend/scripts/README.md) - 数据处理脚本使用说明
- [测试指南](../backend/tests/README.md) - 单元测试与集成测试
