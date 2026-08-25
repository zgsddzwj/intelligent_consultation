# 智能医疗管家平台 - 后端

AI 驱动的智能医疗咨询系统后端服务，基于 FastAPI 构建。

## 技术栈

- **Web 框架**: FastAPI + Uvicorn
- **数据库**: PostgreSQL + SQLAlchemy + Redis
- **AI/LLM**: LangChain + LangGraph + DeepSeek/Qwen
- **向量数据库**: Milvus
- **知识图谱**: Neo4j
- **监控**: Prometheus + Langfuse

## 快速开始

```bash
# 安装依赖
uv sync

# 配置环境变量
cp .env.example .env

# 初始化数据库
python -m app.database.init_db

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

详细文档请参阅项目根目录的 [README.md](../README.md)。
