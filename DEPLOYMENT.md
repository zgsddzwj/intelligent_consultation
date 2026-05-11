# 🚢 部署文档

> 智能医疗管家平台 v2.0 - 完整部署指南

## 部署方式概览

| 方式 | 适用场景 | 复杂度 |
|------|----------|--------|
| **Docker Compose** | 本地开发 / 小型部署 | ⭐ 简单 |
| **本地开发模式** | 前后端分离调试 | ⭐⭐ 中等 |
| **Kubernetes** | 生产环境 / 大规模部署 | ⭐⭐⭐ 较复杂 |

---

## 方式一：Docker Compose（推荐）

适用于本地开发和中小型生产环境。

### 启动服务

```bash
# 克隆项目
git clone https://github.com/zgsddzwj/intelligent_consultation.git
cd intelligent_consultation

# 配置环境变量（编辑 backend/.env）
# 确保 QWEN_API_KEY 已设置

# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f backend

# 停止所有服务
docker-compose down

# 停止并清除数据（谨慎使用）
docker-compose down -v
```

### 服务列表

| 服务 | 端口 | 说明 |
|------|------|------|
| backend | 8000 | FastAPI后端API |
| frontend (可选) | 3000 | React前端 (Nginx) |
| postgres | 5432 | PostgreSQL数据库 |
| redis | 6379 | Redis缓存 |
| neo4j | 7474/7687 | Neo4j知识图谱 (HTTP/Bolt) |
| milvus | 19530 | Milvus向量数据库 |
| etcd | 2379 | Milvus元数据存储 |
| minio | 9000 | MinIO对象存储 |

### 初始化数据

```bash
cd backend

# 一键初始化全部数据
python scripts/init_all.py

# 训练ML模型
python scripts/train_ml_models.py
```

---

## 方式二：本地开发模式

适用于前后端分离开发和调试。

### 1. 启动基础设施

```bash
# 仅启动数据库和中间件服务
docker-compose up -d postgres redis neo4j milvus etcd minio
```

### 2. 启动后端

```bash
# 创建并激活Python虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 安装依赖
cd backend
pip install -r requirements.txt

# 启动后端（热重载模式）
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. 启动前端

```bash
# 新开终端
cd frontend

# 安装依赖
npm install

# 开发模式启动 (Vite dev server)
npm run dev

# 访问 http://localhost:5173
```

---

## 方式三：Kubernetes部署

适用于生产环境，支持自动扩缩容和滚动更新。

### 前置要求

- kubectl 已配置且连接到集群
- Helm 3 (可选，用于简化部署)
- PersistentVolume 已配置 (用于数据持久化)

### 部署步骤

```bash
# 1. 创建命名空间
kubectl apply -f k8s/namespace.yaml

# 2. 创建ConfigMap和Secrets
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
# 注意: 需要提前创建 secrets.yaml 并填入实际密钥

# 3. 部署数据层服务
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/neo4j.yaml
kubectl apply -f k8s/milvus.yaml
kubectl apply -f k8s/minio.yaml

# 4. 等待数据层就绪
kubectl get pods -n medical-platform

# 5. 部署应用层
kubectl apply -f k8s/backend.yaml
kubectl apply -f k8s/frontend.yaml

# 6. 配置Ingress路由
kubectl apply -f k8s/ingress.yaml

# 7. 验证部署
kubectl get all -n medical-platform
kubectl logs -f deployment/backend -n medical-platform
```

详细说明请参考 `k8s/README.md`。

---

## 环境变量配置

### 必需变量

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `QWEN_API_KEY` | 阿里云百炼LLM API密钥 | `sk-xxxxxxxx` |

### 数据库连接

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DATABASE_URL` | PostgreSQL异步连接串 | `postgresql+asyncpg://postgres:postgres@localhost:5432/medical` |
| `REDIS_URL` | Redis连接URL | `redis://localhost:6379/0` |

### 知识图谱

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `NEO4J_URI` | Neo4j Bolt连接URI | `bolt://neo4j:neo4j@localhost:7687` |
| `NEO4J_AUTH` | Neo4j认证信息 | `(neo4j, password)` |

### 向量数据库

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `MILVUS_HOST` | Milvus主机地址 | `localhost` |
| `MILVUS_PORT` | Milvus端口 | `19530` |

### 安全

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `SECRET_KEY` | JWT签名密钥 | 自动生成 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token过期时间(分钟) | `1440` (24h) |

完整配置请参考 `backend/app/config.py`。

---

## 初始化数据

首次部署后必须执行：

```bash
cd backend

# 一键初始化（含知识图谱 + 向量库 + ML模型）
python scripts/init_all.py

# 单独训练ML模型
python scripts/train_ml_models.py
```

初始化内容：
- ✅ PostgreSQL表结构 (Alembic migrations)
- ✅ Neo4j知识图谱（科室/疾病/症状/药物/检查）
- ✅ Milvus集合和索引
- ✅ RAG文档导入
- ✅ ML模型训练与保存

---

## 健康检查

```bash
# 后端健康检查
curl http://localhost:8000/health

# 前端可访问性
curl http://localhost:3000 -I

# Prometheus指标
curl http://localhost:8000/metrics
```

---

## 监控和日志

### 日志位置

| 日志类型 | 路径 |
|----------|------|
| 后端应用日志 | `backend/logs/app.log` |
| ML训练报告 | `backend/logs/training_report.json` |
| Docker容器日志 | `docker-compose logs -f <service>` |
| K8s Pod日志 | `kubectl logs -f <pod-name> -n <namespace>` |

### 监控指标

| 监控项 | 地址 |
|--------|------|
| Prometheus指标 | http://localhost:8000/metrics |
| API交互式文档 | http://localhost:8000/docs |
| Langfuse追踪 | (需配置LANGFUSE环境变量) |

---

## 故障排查

### 端口被占用
```bash
# 查找占用进程
lsof -i :8000
lsof -i :3000

# 终止进程
kill -9 <PID>
```

### 数据库连接失败
```bash
# 检查容器状态
docker-compose ps postgres

# 测试连接
docker-compose exec postgres psql -U postgres -d medical -c "SELECT 1"
```

### 内存不足
```bash
# 查看资源使用
docker stats

# 调整Docker内存限制 (在docker-compose.yml中添加)
deploy:
  resources:
    limits:
      memory: 2G
```

### ML模型加载失败
```bash
# 检查模型文件是否存在
ls -la backend/models/intent/
ls -la backend/models/relevance/

# 重新训练
python scripts/train_ml_models.py --model intent --verbose
```

---

## 生产环境建议

### 🔒 安全加固
1. 使用强随机密钥 (`SECRET_KEY`)
2. 配置HTTPS/TLS证书
3. 启用CORS白名单限制
4. 定期轮换API密钥
5. 启用RBAC权限控制

### 📈 性能优化
1. 配置Gunicorn/Uvicorn多worker
2. 启用Redis缓存热点数据
3. 设置PostgreSQL连接池
4. 配置CDN加速前端静态资源
5. 启用HTTP/2和gzip压缩

### 💾 可靠性保障
1. 配置健康检查探针 (liveness/readiness)
2. 设置Pod资源限制和请求
3. 配置PersistentVolume持久化存储
4. 设置自动扩缩容 (HPA)
5. 配置定期备份策略

### 📊 运维监控
1. Prometheus + Grafana监控面板
2. ELK/Loki日志收集系统
3. Sentry错误追踪
4. Langfuse LLM调用链路追踪
5. 告警通知 (邮件/钉钉/企微)

---

*最后更新: 2026-05-07 | 版本: v2.0*
