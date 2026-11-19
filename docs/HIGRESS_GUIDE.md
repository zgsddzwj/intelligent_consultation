# Higress AI 网关集成指南

> 本文档介绍如何通过 [Higress](https://higress.io/) AI 网关统一管理项目的 LLM API 调用。

## 📋 概述

Higress AI 网关为智能医疗管家平台提供以下能力：

| 能力 | 说明 |
|------|------|
| **统一路由** | 所有 LLM 请求（Chat/Embedding/Vision）通过统一入口转发 |
| **多 Provider 负载均衡** | SiliconFlow / DeepSeek / OpenAI 按权重分流 |
| **自动故障转移** | Provider 不可用时自动切换到备用 Provider |
| **认证与限流** | API Key 认证 + 分层限流（普通/高级用户） |
| **可观测性** | 请求日志、Prometheus 指标、Grafana Dashboard、链路追踪 |
| **模型路由** | 根据模型名称路由到最优 Provider |

## 🏗️ 架构

```
┌─────────────────────────────────────────────────────────┐
│                    后端服务 (FastAPI)                      │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │llm_service  │  │image_analysis│  │ consultation   │  │
│  │(Chat+Stream)│  │  (Vision)    │  │ API (SSE)      │  │
│  └──────┬──────┘  └──────┬───────┘  └───────┬────────┘  │
│         │                │                   │            │
│         └────────────────┴───────────────────┘            │
│                          │                                │
│              higress_client (HigressClient)               │
│                          │                                │
└──────────────────────────┼────────────────────────────────┘
                           │ HTTP (x-higress-api-key)
                           ▼
┌──────────────────────────────────────────────────────────┐
│                  Higress AI 网关                          │
│  ┌────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ 认证插件   │→│ 限流插件     │→│ 负载均衡插件    │  │
│  │(API Key)   │  │(Rate Limit)  │  │(Weighted RR)    │  │
│  └────────────┘  └──────────────┘  └────────┬────────┘  │
│                                              │            │
│  ┌───────────────────────────────────────────┘           │
│  │ 模型路由 → 故障转移                                    │
│  └──────┬──────────────┬──────────────┬───────────────── │
│         │              │              │                    │
└─────────┼──────────────┼──────────────┼──────────────────┘
          ▼              ▼              ▼
   ┌──────────┐   ┌──────────┐   ┌──────────┐
   │SiliconFlow│   │ DeepSeek │   │  OpenAI  │
   │  (60%)   │   │  (25%)   │   │  (15%)   │
   └──────────┘   └──────────┘   └──────────┘
```

## 🚀 快速开始

### 1. 本地开发（不启用 Higress）

默认配置下，Higress 网关未启用，LLM 请求直连 SiliconFlow API，无需额外配置。

### 2. 启用 Higress 网关

#### 方式一：本地 Docker 启动 Higress

```bash
# 拉取 Higress 镜像
docker pull higress-registry.cn-hangzhou.cr.aliyuncs.com/higress/gateway:1.4.0

# 启动 Higress 网关
docker run -d \
  --name higress-gateway \
  -p 8080:80 \
  -p 8443:443 \
  -p 15010:15010 \
  -e HIGRESS_LOG_LEVEL=info \
  -e AI_GATEWAY_ENABLED=true \
  higress-registry.cn-hangzhou.cr.aliyuncs.com/higress/gateway:1.4.0
```

#### 方式二：Kubernetes 部署

```bash
# 一键部署
chmod +x scripts/deploy_higress.sh
./scripts/deploy_higress.sh

# 配置 Secrets（替换为真实 API Key）
kubectl create secret generic higress-ai-secrets \
  --namespace=higress-system \
  --from-literal=SILICONFLOW_API_KEY='<your-key>' \
  --from-literal=HIGRESS_ADMIN_TOKEN='<your-token>' \
  --dry-run=client -o yaml | kubectl apply -f -
```

### 3. 配置后端启用 Higress

在 `backend/.env` 中配置：

```env
# 启用 Higress AI 网关
HIGRESS_ENABLED=true
HIGRESS_GATEWAY_URL=http://localhost:8080
HIGRESS_API_KEY=medical-ai-gateway-dev-key-2026

# K8s 环境下使用集群内地址
# HIGRESS_GATEWAY_URL=http://higress-gateway.higress-system.svc.cluster.local:80
```

重启后端服务后，所有 LLM 请求将自动通过 Higress 网关转发。

## ⚙️ 配置项说明

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `HIGRESS_ENABLED` | `false` | 是否启用 Higress 网关 |
| `HIGRESS_GATEWAY_URL` | `http://localhost:8080` | 网关地址 |
| `HIGRESS_API_KEY` | - | 网关认证 Key |
| `HIGRESS_CHAT_PATH` | `/ai/chat/completions` | 对话接口路径 |
| `HIGRESS_EMBEDDING_PATH` | `/ai/embeddings` | 嵌入接口路径 |
| `HIGRESS_VISION_PATH` | `/ai/vision/chat/completions` | 视觉模型路径 |
| `HIGRESS_TIMEOUT` | `60` | 请求超时（秒） |
| `HIGRESS_MAX_RETRIES` | `2` | 最大重试次数 |
| `HIGRESS_HEALTH_CHECK_INTERVAL` | `30` | 健康检查间隔（秒） |

## 🔌 API 端点

启用 Higress 后，新增以下 API 端点：

### GET `/api/v1/consultation/gateway-status`

返回 Higress AI 网关的状态信息：

```json
{
  "higress_enabled": true,
  "gateway_url": "http://localhost:8080",
  "is_healthy": true,
  "chat_endpoint": "http://localhost:8080/ai/chat/completions",
  "embedding_endpoint": "http://localhost:8080/ai/embeddings",
  "vision_endpoint": "http://localhost:8080/ai/vision/chat/completions"
}
```

## 📁 文件结构

```
k8s/higress/
├── namespace.yaml              # 命名空间定义
├── configmap.yaml              # 网关核心配置
├── secrets.yaml                # API Key 密钥模板
├── deployment.yaml             # Gateway + Console 部署 + RBAC
├── hpa.yaml                    # 自动扩缩容 + PDB
├── ai-routes.yaml              # AI 路由规则（Chat/Embedding/Vision）
├── auth-ratelimit.yaml         # 认证与限流策略
├── loadbalancer-failover.yaml  # 负载均衡与故障转移
├── observability.yaml          # 可观测性（日志/指标/告警/Dashboard）
├── ingress.yaml                # 外部访问 Ingress
└── networkpolicy.yaml          # 网络安全策略

backend/app/services/
└── higress_client.py           # Higress 网关客户端单例

scripts/
├── deploy_higress.sh           # 部署脚本
└── undeploy_higress.sh         # 卸载脚本
```

## 🔍 监控与运维

### 查看网关状态

```bash
# K8s 环境
kubectl get pods -n higress-system
kubectl logs -n higress-system -l app.kubernetes.io/name=higress-gateway -f

# 查看网关配置
kubectl get configmap higress-config -n higress-system -o yaml
```

### Prometheus 指标

Higress 网关在 `:15020/stats/prometheus` 暴露 Prometheus 指标，包括：

- `higress_ai_request_total` — AI 请求总数（按 model/provider/status 分维度）
- `higress_ai_request_duration` — 请求延迟直方图
- `higress_ai_tokens_total` — Token 使用量（input/output 分维度）
- `higress_ai_provider_error_total` — Provider 错误数

### 告警规则

已配置以下告警规则（见 `k8s/higress/observability.yaml`）：

| 告警 | 触发条件 | 级别 |
|------|----------|------|
| HigressHighErrorRate | 5xx 错误率 > 5% | Critical |
| HigressHighLatency | P95 延迟 > 5s | Warning |
| HigressAIRequestRateLimited | 429 限流 > 1 req/s | Warning |
| HigressPodDown | 可用 Pod < 2 | Critical |
| HigressAIProviderError | Provider 错误 > 0.1 req/s | Warning |

## 🔄 故障转移机制

1. **Provider 健康检查**：每 10-15 秒检查 Provider 可用性
2. **熔断器**：连续 3-5 次错误后触发熔断，30-60 秒后自动恢复
3. **故障转移**：请求失败时自动尝试下一个 Provider（最多 3 次）
4. **降级响应**：所有 Provider 不可用时返回 503 + 友好错误信息

## 🔐 安全注意事项

1. **API Key 保护**：`HIGRESS_API_KEY` 和 Provider API Key 必须通过 K8s Secret 管理
2. **网络隔离**：NetworkPolicy 限制只有 `medical-consultation` 命名空间可访问网关
3. **限流保护**：防止恶意调用消耗 LLM 额度
4. **TLS 加密**：生产环境必须启用 HTTPS
