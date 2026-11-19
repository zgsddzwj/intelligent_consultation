#!/bin/bash
# ============================================================
# Higress AI 网关运维管理脚本
# 提供常用运维操作：状态查看、日志查看、配置更新、重启等
# ============================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

NAMESPACE="higress-system"
GATEWAY_LABEL="app.kubernetes.io/name=higress-gateway"
CONSOLE_LABEL="app.kubernetes.io/name=higress-console"

usage() {
    echo -e "${BLUE}Higress AI 网关运维管理脚本${NC}"
    echo ""
    echo "用法: $0 <command> [options]"
    echo ""
    echo "命令:"
    echo "  status              查看网关状态（Pod/Service/Ingress）"
    echo "  logs [N]            查看网关日志（N=行数，默认100）"
    echo "  console-logs [N]    查看控制台日志"
    echo "  restart             重启网关"
    echo "  scale <N>           扩缩容网关 Pod 数量"
    echo "  routes              查看 AI 路由规则"
    echo "  metrics             查看 Prometheus 指标"
    echo "  health              健康检查"
    echo "  config              查看当前配置"
    echo "  update-secret        更新 Secrets（交互式）"
    echo "  failover-status     查看故障转移状态"
    echo "  cleanup-cache       清理网关缓存"
    echo ""
    echo "示例:"
    echo "  $0 status"
    echo "  $0 logs 200"
    echo "  $0 scale 4"
    exit 1
}

# 检查 kubectl
check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        echo -e "${RED}错误: 未找到 kubectl${NC}"
        exit 1
    fi
}

# 查看状态
cmd_status() {
    echo -e "${BLUE}=== Higress 网关状态 ===${NC}"
    echo ""
    echo -e "${YELLOW}[Pods]${NC}"
    kubectl get pods -n "$NAMESPACE" -o wide 2>/dev/null || echo -e "${RED}无法获取 Pod 信息${NC}"

    echo ""
    echo -e "${YELLOW}[Services]${NC}"
    kubectl get svc -n "$NAMESPACE" 2>/dev/null || echo -e "${RED}无法获取 Service 信息${NC}"

    echo ""
    echo -e "${YELLOW}[Ingress]${NC}"
    kubectl get ingress -n "$NAMESPACE" 2>/dev/null || echo -e "${RED}无法获取 Ingress 信息${NC}"

    echo ""
    echo -e "${YELLOW}[HPA]${NC}"
    kubectl get hpa -n "$NAMESPACE" 2>/dev/null || echo -e "${RED}无法获取 HPA 信息${NC}"

    echo ""
    echo -e "${YELLOW}[Resources]${NC}"
    kubectl top pods -n "$NAMESPACE" 2>/dev/null || echo -e "${YELLOW}无法获取资源使用（需要 metrics-server）${NC}"
}

# 查看日志
cmd_logs() {
    local lines=${1:-100}
    echo -e "${BLUE}=== Higress 网关日志 (最近 ${lines} 行) ===${NC}"
    kubectl logs -n "$NAMESPACE" -l "$GATEWAY_LABEL" --tail="$lines" 2>/dev/null || echo -e "${RED}无法获取日志${NC}"
}

# 查看控制台日志
cmd_console_logs() {
    local lines=${1:-100}
    echo -e "${BLUE}=== Higress Console 日志 (最近 ${lines} 行) ===${NC}"
    kubectl logs -n "$NAMESPACE" -l "$CONSOLE_LABEL" --tail="$lines" 2>/dev/null || echo -e "${RED}无法获取日志${NC}"
}

# 重启网关
cmd_restart() {
    echo -e "${YELLOW}重启 Higress 网关...${NC}"
    kubectl rollout restart deployment higress-gateway -n "$NAMESPACE"
    echo -e "${YELLOW}等待 rollout 完成...${NC}"
    kubectl rollout status deployment higress-gateway -n "$NAMESPACE" --timeout=120s
    echo -e "${GREEN}网关重启完成${NC}"
}

# 扩缩容
cmd_scale() {
    local replicas=$1
    if [ -z "$replicas" ]; then
        echo -e "${RED}请指定副本数: $0 scale <N>${NC}"
        exit 1
    fi
    echo -e "${YELLOW}扩缩容 Higress 网关到 ${replicas} 副本...${NC}"
    kubectl scale deployment higress-gateway -n "$NAMESPACE" --replicas="$replicas"
    echo -e "${GREEN}扩缩容完成${NC}"
}

# 查看路由规则
cmd_routes() {
    echo -e "${BLUE}=== Higress AI 路由规则 ===${NC}"
    echo ""
    echo -e "${YELLOW}[Ingress 路由]${NC}"
    kubectl get ingress -n "$NAMESPACE" -o yaml 2>/dev/null | grep -E "name:|path:|host:" || echo "无路由"

    echo ""
    echo -e "${YELLOW}[McpBridge Provider]${NC}"
    kubectl get mcpbridge -n "$NAMESPACE" 2>/dev/null || echo "无 McpBridge 资源"

    echo ""
    echo -e "${Yellow}[HigressConfig 插件]${NC}"
    kubectl get higressconfig -n "$NAMESPACE" 2>/dev/null || echo "无 HigressConfig 资源"
}

# 查看指标
cmd_metrics() {
    echo -e "${BLUE}=== Higress Prometheus 指标 ===${NC}"
    local gateway_pod=$(kubectl get pods -n "$NAMESPACE" -l "$GATEWAY_LABEL" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    if [ -z "$gateway_pod" ]; then
        echo -e "${RED}未找到网关 Pod${NC}"
        exit 1
    fi
    echo -e "${YELLOW}从 Pod ${gateway_pod} 获取指标...${NC}"
    kubectl exec -n "$NAMESPACE" "$gateway_pod" -- curl -s http://localhost:15020/stats/prometheus 2>/dev/null | grep -E "higress_ai|higress_envoy" | head -50
}

# 健康检查
cmd_health() {
    echo -e "${BLUE}=== Higress 网关健康检查 ===${NC}"
    echo ""

    # Pod 健康状态
    echo -e "${YELLOW}[Pod 健康状态]${NC}"
    kubectl get pods -n "$NAMESPACE" -o custom-columns=NAME:.metadata.name,READY:.status.containerStatuses[0].ready,STATUS:.status.phase,RESTARTS:.status.containerStatuses[0].restartCount 2>/dev/null

    echo ""
    echo -e "${Yellow}[就绪探针]${NC}"
    local gateway_pod=$(kubectl get pods -n "$NAMESPACE" -l "$GATEWAY_LABEL" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    if [ -n "$gateway_pod" ]; then
        kubectl exec -n "$NAMESPACE" "$gateway_pod" -- curl -s http://localhost:15010/ready 2>/dev/null || echo -e "${RED}就绪检查失败${NC}"
    fi

    echo ""
    echo -e "${Yellow}[事件]${NC}"
    kubectl get events -n "$NAMESPACE" --sort-by='.lastTimestamp' 2>/dev/null | tail -10
}

# 查看配置
cmd_config() {
    echo -e "${BLUE}=== Higress 配置 ===${NC}"
    echo ""
    echo -e "${Yellow}[ConfigMap]${NC}"
    kubectl get configmap higress-config -n "$NAMESPACE" -o yaml 2>/dev/null

    echo ""
    echo -e "${Yellow}[Secrets（仅显示键名）]${NC}"
    kubectl get secret higress-ai-secrets -n "$NAMESPACE" -o jsonpath='{.data}' 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); [print(f'  {k}') for k in d.keys()]" 2>/dev/null || echo "无法获取"
}

# 更新 Secrets
cmd_update_secret() {
    echo -e "${BLUE}=== 更新 Higress Secrets ===${NC}"
    echo ""

    read -p "SILICONFLOW_API_KEY: " sf_key
    read -p "OPENAI_API_KEY (可选，直接回车跳过): " openai_key
    read -p "DEEPSEEK_API_KEY (可选，直接回车跳过): " ds_key
    read -p "HIGRESS_ADMIN_TOKEN: " admin_token

    local args="--from-literal=SILICONFLOW_API_KEY='${sf_key}'"
    [ -n "$openai_key" ] && args="$args --from-literal=OPENAI_API_KEY='${openai_key}'"
    [ -n "$ds_key" ] && args="$args --from-literal=DEEPSEEK_API_KEY='${ds_key}'"
    [ -n "$admin_token" ] && args="$args --from-literal=HIGRESS_ADMIN_TOKEN='${admin_token}'"

    echo -e "${Yellow}更新 Secrets...${NC}"
    eval kubectl create secret generic higress-ai-secrets --namespace=\"$NAMESPACE\" $args --dry-run=client -o yaml | kubectl apply -f -
    echo -e "${GREEN}Secrets 更新完成${NC}"
    echo -e "${Yellow}建议重启网关使配置生效: $0 restart${NC}"
}

# 故障转移状态
cmd_failover_status() {
    echo -e "${BLUE}=== Higress 故障转移状态 ===${NC}"
    echo ""
    local gateway_pod=$(kubectl get pods -n "$NAMESPACE" -l "$GATEWAY_LABEL" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    if [ -z "$gateway_pod" ]; then
        echo -e "${RED}未找到网关 Pod${NC}"
        exit 1
    fi
    echo -e "${Yellow}[上游集群状态]${NC}"
    kubectl exec -n "$NAMESPACE" "$gateway_pod" -- curl -s http://localhost:15010/clusters 2>/dev/null | grep -E "siliconflow|deepseek|openai" | head -20
    echo ""
    echo -e "${Yellow}[熔断器状态]${NC}"
    kubectl exec -n "$NAMESPACE" "$gateway_pod" -- curl -s http://localhost:15010/circuit_breakers 2>/dev/null | head -20
}

# 清理缓存
cmd_cleanup_cache() {
    echo -e "${Yellow}清理 Higress 网关缓存...${NC}"
    local gateway_pod=$(kubectl get pods -n "$NAMESPACE" -l "$GATEWAY_LABEL" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    if [ -z "$gateway_pod" ]; then
        echo -e "${RED}未找到网关 Pod${NC}"
        exit 1
    fi
    kubectl exec -n "$NAMESPACE" "$gateway_pod" -- curl -s -X POST http://localhost:15010/clear_cache 2>/dev/null || echo -e "${Yellow}缓存清理端点不可用（可能是版本不支持）${NC}"
    echo -e "${GREEN}缓存清理完成${NC}"
}

# 主入口
check_kubectl

case "${1:-}" in
    status)          cmd_status ;;
    logs)            cmd_logs "${2:-100}" ;;
    console-logs)    cmd_console_logs "${2:-100}" ;;
    restart)         cmd_restart ;;
    scale)           cmd_scale "${2:-}" ;;
    routes)          cmd_routes ;;
    metrics)         cmd_metrics ;;
    health)          cmd_health ;;
    config)          cmd_config ;;
    update-secret)   cmd_update_secret ;;
    failover-status) cmd_failover_status ;;
    cleanup-cache)   cmd_cleanup_cache ;;
    *)               usage ;;
esac
