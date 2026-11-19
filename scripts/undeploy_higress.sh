#!/bin/bash
# ============================================================
# Higress AI 网关卸载脚本
# 从 Kubernetes 集群中卸载 Higress AI 网关
# ============================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
HIGRESS_K8S_DIR="$PROJECT_ROOT/k8s/higress"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Higress AI 网关卸载脚本${NC}"
echo -e "${BLUE}========================================${NC}"

if [ ! -d "$HIGRESS_K8S_DIR" ]; then
    echo -e "${RED}错误: Higress K8s 配置目录不存在${NC}"
    exit 1
fi

read -p "$(echo -e ${YELLOW}'确认卸载 Higress AI 网关？(yes/no): '${NC})" confirm
if [ "$confirm" != "yes" ]; then
    echo -e "${YELLOW}已取消卸载${NC}"
    exit 0
fi

echo -e "\n${YELLOW}删除可观测性配置...${NC}"
kubectl delete -f "$HIGRESS_K8S_DIR/observability.yaml" --ignore-not-found=true

echo -e "${YELLOW}删除负载均衡配置...${NC}"
kubectl delete -f "$HIGRESS_K8S_DIR/loadbalancer-failover.yaml" --ignore-not-found=true

echo -e "${YELLOW}删除认证限流配置...${NC}"
kubectl delete -f "$HIGRESS_K8S_DIR/auth-ratelimit.yaml" --ignore-not-found=true

echo -e "${YELLOW}删除 AI 路由规则...${NC}"
kubectl delete -f "$HIGRESS_K8S_DIR/ai-routes.yaml" --ignore-not-found=true

echo -e "${YELLOW}删除 HPA 和 PDB...${NC}"
kubectl delete -f "$HIGRESS_K8S_DIR/hpa.yaml" --ignore-not-found=true

echo -e "${YELLOW}删除 Gateway 部署...${NC}"
kubectl delete -f "$HIGRESS_K8S_DIR/deployment.yaml" --ignore-not-found=true

echo -e "${YELLOW}删除 Secrets...${NC}"
kubectl delete -f "$HIGRESS_K8S_DIR/secrets.yaml" --ignore-not-found=true

echo -e "${YELLOW}删除 ConfigMap...${NC}"
kubectl delete -f "$HIGRESS_K8S_DIR/configmap.yaml" --ignore-not-found=true

echo -e "${YELLOW}删除命名空间...${NC}"
kubectl delete -f "$HIGRESS_K8S_DIR/namespace.yaml" --ignore-not-found=true

echo -e "\n${GREEN}Higress AI 网关卸载完成！${NC}"
