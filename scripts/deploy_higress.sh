#!/bin/bash
# ============================================================
# Higress AI 网关部署脚本
# 用于在 Kubernetes 集群中部署 Higress AI 网关
# ============================================================
set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
HIGRESS_K8S_DIR="$PROJECT_ROOT/k8s/higress"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Higress AI 网关部署脚本${NC}"
echo -e "${BLUE}========================================${NC}"

# 检查 kubectl
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}错误: 未找到 kubectl，请先安装 kubectl${NC}"
    exit 1
fi

# 检查 Higress K8s 配置目录
if [ ! -d "$HIGRESS_K8S_DIR" ]; then
    echo -e "${RED}错误: Higress K8s 配置目录不存在: $HIGRESS_K8S_DIR${NC}"
    exit 1
fi

echo -e "\n${YELLOW}[1/8] 创建 Higress 命名空间...${NC}"
kubectl apply -f "$HIGRESS_K8S_DIR/namespace.yaml"

echo -e "\n${YELLOW}[2/8] 部署 Higress 配置 ConfigMap...${NC}"
kubectl apply -f "$HIGRESS_K8S_DIR/configmap.yaml"

echo -e "\n${YELLOW}[3/8] 部署 Higress Secrets（请先修改 secrets.yaml 中的 REPLACE_ME）...${NC}"
kubectl apply -f "$HIGRESS_K8S_DIR/secrets.yaml" 2>/dev/null || {
    echo -e "${YELLOW}提示: Secrets 可能已存在，跳过...${NC}"
}

echo -e "\n${YELLOW}[4/8] 部署 Higress Gateway 和 Console...${NC}"
kubectl apply -f "$HIGRESS_K8S_DIR/deployment.yaml"

echo -e "\n${YELLOW}[5/8] 部署 AI 网关路由规则...${NC}"
kubectl apply -f "$HIGRESS_K8S_DIR/ai-routes.yaml"

echo -e "\n${YELLOW}[6/8] 部署认证与限流策略...${NC}"
kubectl apply -f "$HIGRESS_K8S_DIR/auth-ratelimit.yaml"

echo -e "\n${YELLOW}[7/8] 部署负载均衡与故障转移配置...${NC}"
kubectl apply -f "$HIGRESS_K8S_DIR/loadbalancer-failover.yaml"

echo -e "\n${YELLOW}[8/8] 部署可观测性配置...${NC}"
kubectl apply -f "$HIGRESS_K8S_DIR/observability.yaml"

echo -e "\n${YELLOW}部署 HPA 和 PDB...${NC}"
kubectl apply -f "$HIGRESS_K8S_DIR/hpa.yaml"

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}  Higress AI 网关部署完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "\n${BLUE}后续步骤:${NC}"
echo -e "  1. 更新 Secrets 中的 API Key:"
echo -e "     kubectl create secret generic higress-ai-secrets \\"
echo -e "       --namespace=higress-system \\"
echo -e "       --from-literal=SILICONFLOW_API_KEY='<your-key>' \\"
echo -e "       --from-literal=HIGRESS_ADMIN_TOKEN='<your-token>' \\"
echo -e "       --dry-run=client -o yaml | kubectl apply -f -"
echo -e "\n  2. 查看网关状态:"
echo -e "     kubectl get pods -n higress-system"
echo -e "\n  3. 查看网关日志:"
echo -e "     kubectl logs -n higress-system -l app.kubernetes.io/name=higress-gateway -f"
echo -e "\n  4. 在后端 .env 中启用 Higress:"
echo -e "     HIGRESS_ENABLED=true"
echo -e "     HIGRESS_GATEWAY_URL=http://higress-gateway.higress-system.svc.cluster.local:80"
