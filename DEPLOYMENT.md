# 部署文档

## 部署方式

### 方式一：Docker Compose（推荐）

适用于本地开发和生产环境。

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 方式二：本地开发

适用于开发环境，需要手动启动各个服务。

#### 1. 启动数据库服务

```bash
docker-compose up -d postgres redis neo4j milvus etcd minio
```

#### 2. 启动后端服务

```bash
# 激活conda环境
source /opt/anaconda3/etc/profile.d/conda.sh
conda activate intelligent_consultation

# 启动后端
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 3. 启动前端服务

```bash
cd frontend
npm run dev
```

### 方式三：Kubernetes部署

适用于生产环境。

```bash
# 创建命名空间
kubectl apply -f k8s/namespace.yaml

# 创建配置和密钥
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml

# 部署数据库服务
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/neo4j.yaml
kubectl apply -f k8s/milvus.yaml

# 部署应用服务
kubectl apply -f k8s/backend.yaml
kubectl apply -f k8s/frontend.yaml

# 配置Ingress
kubectl apply -f k8s/ingress.yaml
```

详细说明请参考 `k8s/README.md`。

## 环境变量配置

### 必需配置

- `QWEN_API_KEY`: 阿里云百炼API密钥

### 可选配置

- `DATABASE_URL`: 数据库连接URL
- `REDIS_URL`: Redis连接URL
- `NEO4J_URI`: Neo4j连接URI
- `MILVUS_HOST`: Milvus主机地址
- `MILVUS_PORT`: Milvus端口

完整配置请参考 `backend/app/config.py`。

## 初始化数据

首次部署后需要初始化数据：

```bash
cd backend
python scripts/init_all.py
```

这将初始化：
- 数据库表结构
- 知识图谱数据
- 向量数据库索引

## 健康检查

```bash
# 后端健康检查
curl http://localhost:8000/health

# 前端访问
curl http://localhost:3000
```

## 监控和日志

### 日志位置

- 后端日志: `backend/logs/app.log`
- Docker日志: `docker-compose logs -f`

### 监控指标

- Prometheus指标: http://localhost:8000/metrics
- API文档: http://localhost:8000/docs

## 故障排查

### 常见问题

1. **端口被占用**
   - 检查端口占用: `lsof -i :8000`
   - 修改 `docker-compose.yml` 中的端口映射

2. **数据库连接失败**
   - 检查数据库服务是否运行: `docker-compose ps`
   - 检查环境变量配置

3. **API密钥错误**
   - 确认 `QWEN_API_KEY` 已正确配置
   - 检查API密钥是否有效

## 生产环境建议

1. 使用环境变量管理敏感信息
2. 配置HTTPS和域名
3. 设置资源限制和健康检查
4. 配置日志收集和监控
5. 定期备份数据库

