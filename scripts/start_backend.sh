#!/bin/bash

# 启动后端服务脚本（使用 uv 管理依赖）

cd "$(dirname "$0")/../backend"

echo "启动后端服务..."
echo "依赖管理: uv"
PORT="${BACKEND_PORT:-8000}"
echo "端口: ${PORT}"
echo ""

# 使用 uv 运行，自动同步虚拟环境
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port "${PORT}"
