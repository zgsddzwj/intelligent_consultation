# Kubernetes 部署配置

本目录包含智能医疗管家平台的 Kubernetes 部署配置文件。

## 文件说明

### 核心配置
- `namespace.yaml` - 创建命名空间
- `configmap.yaml` - 应用配置（非敏感信息）
- `secrets.yaml` - 敏感信息（密码、API密钥等）

### 数据服务
- `postgres.yaml` - PostgreSQL 数据库（含 PDB + PriorityClass）
- `redis.yaml` - Redis 缓存（含 PDB + PriorityClass）
- `neo4j.yaml` - Neo4j 知识图谱（含 PDB + PriorityClass）
- `milvus.yaml` - Milvus 向量数据库（包含 etcd 和 minio）

### 应用服务
- `backend.yaml` - 后端服务（含 HPA + PDB + PriorityClass）
- `frontend.yaml` - 前端服务（含 HPA + PDB + PriorityClass）
- `ingress.yaml` - Ingress 配置（需要安装 Ingress Controller）

### 安全与运维（v3.1 新增）
- `networkpolicy.yaml` - 网络安全策略（限制 Pod 间通信，仅允许必要流量）
- `servicemonitor.yaml` - Prometheus 监控配置（ServiceMonitor + PrometheusRule 告警规则）
- `resourcequota.yaml` - 命名空间资源配额 + LimitRange 默认资源限制
- `priorityclass.yaml` - Pod 调度优先级（critical / data / batch）

## 部署步骤

### 1. 前置要求

- Kubernetes 集群（1.20+）
- kubectl 已配置
- 已构建 Docker 镜像并推送到镜像仓库

### 2. 构建和推送镜像

```bash
# 构建后端镜像
cd backend
docker build -t ghcr.io/zgsddzwj/intelligent_consultation/backend:latest .
docker push ghcr.io/zgsddzwj/intelligent_consultation/backend:latest

# 构建前端镜像
cd frontend
docker build -t ghcr.io/zgsddzwj/intelligent_consultation/frontend:latest .
docker push ghcr.io/zgsddzwj/intelligent_consultation/frontend:latest
```

### 3. 配置 Secrets

**重要**：部署前必须修改 `secrets.yaml` 中的敏感信息！

```bash
# 编辑 secrets.yaml，修改所有密码和密钥
# 或者使用 kubectl 命令创建：
kubectl create secret generic medical-secrets \
  --from-literal=QWEN_API_KEY='your-key' \
  --from-literal=POSTGRES_PASSWORD='your-password' \
  --from-literal=NEO4J_PASSWORD='your-password' \
  --from-literal=LANGFUSE_PUBLIC_KEY='your-key' \
  --from-literal=LANGFUSE_SECRET_KEY='your-secret' \
  --namespace=medical-consultation
```

### 4. 修改配置

编辑以下文件中的配置：
- `configmap.yaml` - 修改域名、CORS等配置
- `backend.yaml` - 修改镜像地址
- `frontend.yaml` - 修改镜像地址
- `ingress.yaml` - 修改域名

### 5. 部署顺序

```bash
# 1. 创建命名空间
kubectl apply -f namespace.yaml

# 2. 创建 ConfigMap 和 Secrets
kubectl apply -f configmap.yaml
kubectl apply -f secrets.yaml

# 3. 创建资源配额和优先级
kubectl apply -f resourcequota.yaml
kubectl apply -f priorityclass.yaml

# 4. 部署数据服务（按顺序）
kubectl apply -f postgres.yaml
kubectl apply -f redis.yaml
kubectl apply -f neo4j.yaml
kubectl apply -f milvus.yaml

# 5. 等待数据服务就绪
kubectl wait --for=condition=ready pod -l app=postgres -n medical-consultation --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis -n medical-consultation --timeout=300s
kubectl wait --for=condition=ready pod -l app=neo4j -n medical-consultation --timeout=300s
kubectl wait --for=condition=ready pod -l app=milvus -n medical-consultation --timeout=300s

# 6. 部署应用服务
kubectl apply -f backend.yaml
kubectl apply -f frontend.yaml

# 7. 部署网络安全策略
kubectl apply -f networkpolicy.yaml

# 8. 部署 Ingress（可选）
kubectl apply -f ingress.yaml

# 9. 部署监控（需要 Prometheus Operator）
kubectl apply -f servicemonitor.yaml
```

### 6. 一键部署脚本

```bash
#!/bin/bash
# deploy.sh

kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f secrets.yaml
kubectl apply -f resourcequota.yaml
kubectl apply -f priorityclass.yaml

# 数据服务
kubectl apply -f postgres.yaml
kubectl apply -f redis.yaml
kubectl apply -f neo4j.yaml
kubectl apply -f milvus.yaml

# 等待数据服务就绪
echo "等待数据服务启动..."
sleep 60

# 应用服务
kubectl apply -f backend.yaml
kubectl apply -f frontend.yaml

# 安全策略
kubectl apply -f networkpolicy.yaml

# Ingress
kubectl apply -f ingress.yaml

# 监控（可选，需要 Prometheus Operator）
kubectl apply -f servicemonitor.yaml

echo "部署完成！"
```

### 7. 初始化数据

部署完成后，需要初始化数据库和知识图谱：

```bash
# 进入后端 Pod
kubectl exec -it -n medical-consultation deployment/backend -- bash

# 运行初始化脚本
cd /app
python scripts/setup/init_all.py
```

## 验证部署

```bash
# 查看所有 Pod 状态
kubectl get pods -n medical-consultation

# 查看服务状态
kubectl get svc -n medical-consultation

# 查看后端日志
kubectl logs -f -n medical-consultation deployment/backend

# 测试后端健康检查
kubectl port-forward -n medical-consultation svc/backend-service 8000:8000
curl http://localhost:8000/health
```

## 扩缩容

### 手动扩缩容

```bash
# 扩展后端副本
kubectl scale deployment backend -n medical-consultation --replicas=5

# 扩展前端副本
kubectl scale deployment frontend -n medical-consultation --replicas=3
```

### 自动扩缩容（HPA）

HPA 已配置，会根据 CPU 和内存使用率自动扩缩容：
- 后端：3-10 个副本
- 前端：2-5 个副本

## 监控

### Prometheus 监控

已配置 `servicemonitor.yaml`，包含：
- **ServiceMonitor**：自动发现并抓取 backend、frontend、postgres、redis 的 `/metrics` 端点
- **PrometheusRule**：内置告警规则
  - Backend 错误率过高（>5% 5xx）
  - Backend P95 延迟过高（>2s）
  - Pod 频繁重启（1h 内 >3 次）
  - PostgreSQL/Redis/Neo4j 连接断开

部署监控（需要已安装 kube-prometheus-stack 或 prometheus-operator）：
```bash
kubectl apply -f servicemonitor.yaml
```

### Pod 安全

- 所有 Pod 配置了 `securityContext`（非 root 运行、禁止提权、最小权限）
- `NetworkPolicy` 限制 Pod 间通信，仅允许必要流量
- `PriorityClass` 确保关键服务优先调度
- `ResourceQuota` 限制命名空间资源总量
- `LimitRange` 为未设置资源限制的 Pod 提供默认值

## 备份和恢复

### PostgreSQL 备份

```bash
# 备份
kubectl exec -n medical-consultation postgres-0 -- pg_dump -U postgres medical_consultation > backup.sql

# 恢复
kubectl exec -i -n medical-consultation postgres-0 -- psql -U postgres medical_consultation < backup.sql
```

### Neo4j 备份

```bash
# 备份
kubectl exec -n medical-consultation neo4j-0 -- neo4j-admin database dump neo4j --to-path=/backup

# 恢复
kubectl exec -n medical-consultation neo4j-0 -- neo4j-admin database load neo4j --from-path=/backup
```

## 故障排查

### 查看 Pod 日志

```bash
kubectl logs -n medical-consultation <pod-name>
kubectl logs -n medical-consultation -l app=backend --tail=100
```

### 进入 Pod 调试

```bash
kubectl exec -it -n medical-consultation <pod-name> -- bash
```

### 查看事件

```bash
kubectl get events -n medical-consultation --sort-by='.lastTimestamp'
```

## 注意事项

1. **生产环境**：
   - 修改所有默认密码
   - 使用 TLS 证书
   - 配置资源限制
   - 启用监控和告警
   - 定期备份数据

2. **存储**：
   - 确保有足够的 PersistentVolume
   - 考虑使用 StorageClass 自动创建 PV

3. **网络**：
   - 配置 NetworkPolicy 限制网络访问
   - 使用 Ingress Controller 暴露服务

4. **安全**：
   - 使用 RBAC 控制访问权限
   - 定期更新镜像和依赖
   - 扫描镜像漏洞

## 卸载

```bash
kubectl delete -f servicemonitor.yaml
kubectl delete -f networkpolicy.yaml
kubectl delete -f ingress.yaml
kubectl delete -f frontend.yaml
kubectl delete -f backend.yaml
kubectl delete -f milvus.yaml
kubectl delete -f neo4j.yaml
kubectl delete -f redis.yaml
kubectl delete -f postgres.yaml
kubectl delete -f priorityclass.yaml
kubectl delete -f resourcequota.yaml
kubectl delete -f secrets.yaml
kubectl delete -f configmap.yaml
kubectl delete -f namespace.yaml
```

**注意**：删除命名空间会删除所有资源，包括 PersistentVolumeClaim。如需保留数据，请先备份。

