#!/bin/bash

# 智能医疗管家平台启动脚本

set -e

# 切换到项目根目录（脚本位于 scripts/ 下）
cd "$(dirname "$0")/.."

echo "=========================================="
echo "智能医疗管家平台 - 启动脚本"
echo "=========================================="

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo "错误: Docker未运行，请先启动Docker"
    exit 1
fi

# 检查 uv 是否安装（用于本地初始化脚本）
if ! command -v uv &> /dev/null; then
    echo "警告: uv 未安装，本地初始化脚本将无法运行"
    echo "请安装: curl -LsSf https://astral.sh/uv/install.sh | sh"
fi

# 检查.env文件
if [ ! -f "backend/.env" ]; then
    echo "警告: backend/.env 文件不存在"
    if [ -f "backend/.env.example" ]; then
        echo "正在从 backend/.env.example 创建 backend/.env ..."
        cp backend/.env.example backend/.env
        echo "请编辑 backend/.env，至少设置 SECRET_KEY 和 QWEN_API_KEY"
    else
        echo "请创建 backend/.env 并配置 SECRET_KEY、QWEN_API_KEY"
    fi
fi

INIT_DATA=false
if [ "${1:-}" = "--init" ]; then
    INIT_DATA=true
fi

# 启动Docker服务（使用 backend/.env 进行变量插值）
echo ""
echo "[1/3] 启动Docker服务..."
docker compose --env-file backend/.env up -d

# 等待后端存活
echo ""
echo "[2/3] 等待服务就绪..."
MAX_WAIT=120
ELAPSED=0
until curl -sf http://localhost:8000/live > /dev/null 2>&1; do
    if [ "$ELAPSED" -ge "$MAX_WAIT" ]; then
        echo "错误: 后端在 ${MAX_WAIT}s 内未就绪，请检查: docker compose logs backend"
        exit 1
    fi
    sleep 3
    ELAPSED=$((ELAPSED + 3))
    echo "  等待后端启动... (${ELAPSED}s)"
done
echo "  后端 /live 探针通过"

# 检查服务状态
echo ""
echo "检查服务状态..."
docker compose ps

# 初始化数据
echo ""
echo "[3/3] 数据初始化..."
if [ "$INIT_DATA" = true ]; then
    echo "正在运行 init_all.py ..."
    (cd backend && uv run python scripts/setup/init_all.py) || {
        echo "警告: init_all.py 执行失败，请手动运行"
    }
else
    echo "提示: 首次运行请执行以下命令初始化数据："
    echo "  ./scripts/start.sh --init"
    echo "  或: cd backend && uv run python scripts/setup/init_all.py"
fi

echo ""
echo "=========================================="
echo "启动完成！"
echo "=========================================="
echo ""
echo "访问地址："
echo "  前端: http://localhost:3000"
echo "  后端API: http://localhost:8000"
echo "  API文档: http://localhost:8000/docs"
echo "  Neo4j浏览器: http://localhost:7474"
echo ""
echo "查看日志: docker compose logs -f"
echo "停止服务: docker compose down"
echo ""
