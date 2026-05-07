# 🚀 快速启动指南

> 智能医疗管家平台 v2.0 - 从零到运行，5分钟完成

## 1. 环境准备

确保已安装：
1. **Docker** 和 **Docker Compose** (用于一键启动全部服务)
2. **Python 3.11+** (用于运行初始化脚本和ML模型训练)
3. **Node.js 18+** (可选，用于本地开发前端)
4. **Git** (用于克隆项目)

## 2. 克隆项目

```bash
git clone https://github.com/zgsddzwj/intelligent_consultation.git
cd intelligent_consultation
```

## 3. 配置环境变量

`.env` 文件已创建在 `backend/.env`，包含阿里云百炼API密钥配置。

如需修改，编辑 `backend/.env` 文件：

```bash
# 必需：LLM API密钥
QWEN_API_KEY=your_api_key_here

# 可选：其他服务连接配置（Docker Compose启动时通常使用默认值）
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/medical
REDIS_URL=redis://localhost:6379/0
NEO4J_URI=bolt://neo4j:neo4j@localhost:7687
MILVUS_HOST=localhost
MILVUS_PORT=19530
```

**⚠️ 重要**：确保 `QWEN_API_KEY` 已正确配置！

## 4. 启动服务

### 方式一：Docker Compose 一键启动（推荐）

```bash
# 启动所有服务（后端 + 数据库 + 缓存 + 向量库 + 知识图谱）
docker-compose up -d

# 查看所有服务状态
docker-compose ps

# 查看后端日志
docker-compose logs -f backend
```

### 方式二：本地开发模式

```bash
# 终端1: 启动数据库基础设施
docker-compose up -d postgres redis neo4j milvus etcd minio

# 终端2: 启动后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 终端3: 启动前端
cd frontend
npm install
npm run dev
```

## 5. 初始化数据

首次运行**必须**执行初始化：

### 5.1 初始化知识图谱和基础数据

```bash
cd backend

# 一键初始化全部（推荐）
python scripts/init_all.py
```

这将自动执行：
1. ✅ 数据库表结构创建 (Alembic migrations)
2. ✅ 医疗文档数据加载
3. ✅ **Neo4j知识图谱初始化**（15个科室、13种疾病、18种症状、10种药物、5种检查）
4. ✅ **Milvus向量数据库索引构建**
5. ✅ RAG系统文档导入

### 5.2 训练ML模型（新增）

```bash
cd backend

# 训练所有ML模型（约2-3分钟）
python scripts/train_ml_models.py

# 或仅训练指定模型
python scripts/train_ml_models.py --model intent      # 意图分类器
python scripts/train_ml_models.py --model relevance    # 相关性评分器
python scripts/train_ml_models.py --model ranking      # 排序优化器
python scripts/train_ml_models.py --model reranker     # ML重排序器

# 列出所有可用模型
python scripts/train_ml_models.py --list-models
```

训练的模型将保存在 `backend/models/` 目录下。

## 6. 访问系统

| 服务 | 地址 | 说明 |
|------|------|------|
| **🏥 患者门户** | http://localhost:3000 | AI智能问诊聊天界面 |
| **👨‍⚕️ 医生工作台** | http://localhost:3000/doctor | 医生诊断管理面板 |
| **🔬 知识图谱** | http://localhost:3000/knowledge-graph | 医疗知识可视化 |
| **⚙️ 管理后台** | http://localhost:3000/admin | 系统运维管理中心 |
| **📡 后端API** | http://localhost:8000 | FastAPI RESTful API |
| **📖 API文档** | http://localhost:8000/docs | Swagger交互式文档 |
| **📊 Neo4j浏览器** | http://localhost:7474 | 图谱数据浏览 (neo4j/neo4j) |

## 7. 功能使用指南

### 💬 在线AI问诊
1. 访问首页 (`/`)
2. 输入健康问题或点击快捷问题卡片
3. 可上传医疗图片进行术语识别
4. 系统自动识别意图 → 路由Agent → 返回专业回答
5. 查看回答、信息来源和风险等级标签

### 🔬 知识图谱探索
1. 访问 `/knowledge-graph` 页面
2. 使用科室选择器筛选图谱范围
3. 点击节点查看实体详情
4. 拖拽节点调整布局
5. 查看图例了解不同颜色含义

### 👨‍⚕️ 医生工作台
1. 访问 `/doctor` 页面
2. 查看实时统计面板（患者数/问诊量/待审阅/响应时间）
3. 使用功能模块（患者管理/诊断辅助/用药指导/数据分析）
4. 查看最近活动列表和待办任务

### ⚙️ 管理后台
1. 访问 `/admin` 页面
2. 监控各服务运行状态（CPU/内存/运行时间）
3. 查看系统日志（INFO/WARN/ERROR分级）
4. 管理用户权限和数据

## 8. 验证功能

### 健康检查
```bash
curl http://localhost:8000/health
```

### 测试知识图谱API
```bash
curl -X POST http://localhost:8000/api/v1/knowledge/graph/visualization \
  -H "Content-Type: application/json" \
  -d '{"department": "心内科", "depth": 2}'
```

### 测试AI对话API
```bash
curl -X POST http://localhost:8000/api/v1/consultation/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "头痛怎么办？"}'
```

### Neo4j数据验证
在Neo4j浏览器 (http://localhost:7474) 中执行：
```cypher
MATCH (n) RETURN labels(n), count(n)
```

## 9. 常见问题排查

### Neo4j连接失败
```bash
# 检查Neo4j容器状态
docker-compose ps neo4j

# 查看日志
docker-compose logs neo4j

# 重启服务
docker-compose restart neo4j
```

### Milvus连接失败
```bash
# Milvus依赖etcd和minio，确保都已启动
docker-compose ps etcd minio milvus

# 重启整个Milvus相关栈
docker-compose restart milvus etcd minio
```

### 前端页面空白
```bash
# 确认后端API正常运行
curl http://localhost:8000/health

# 检查前端控制台是否有CORS错误
# 确认前端代理配置正确 (vite.config.ts)
```

### API密钥错误
- 确认 `backend/.env` 中 `QWEN_API_KEY` 正确
- 检查密钥是否有效（访问[阿里云百炼控制台](https://bailian.console.aliyun.com/)）

### ML模型训练失败
```bash
# 确保scikit-learn已安装
pip install scikit-learn numpy

# 查看详细错误日志
python scripts/train_ml_models.py --verbose
```

## 10. 下一步

- [ ] 加载更多医疗文档到RAG系统
- [ ] 扩展知识图谱数据和关系
- [ ] 优化Agent提示词模板
- [ ] 定期重新训练ML模型
- [ ] 配置生产环境HTTPS和域名
- [ ] 设置Prometheus+Grafana监控面板

---

*最后更新: 2026-05-07 | 版本: v2.0*
