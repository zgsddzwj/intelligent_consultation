#!/bin/bash

# 启动前端服务脚本

cd "$(dirname "$0")/frontend"

echo "启动前端服务..."
echo "端口: 3000"
echo ""

npm run dev

