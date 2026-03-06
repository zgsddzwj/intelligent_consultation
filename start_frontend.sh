#!/bin/bash

# 启动前端服务脚本

cd "$(dirname "$0")/frontend"

PORT="${FRONTEND_PORT:-3000}"
echo "启动前端服务..."
echo "监听地址: 0.0.0.0"
echo "端口: ${PORT}"
echo ""

npm run dev -- --host 0.0.0.0 --port "${PORT}"

