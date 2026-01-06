#!/bin/bash

# 启动后端服务脚本

cd "$(dirname "$0")/backend"

echo "启动后端服务..."
echo "环境: intelligent_consultation"
echo "端口: 8000"
echo ""

conda run -n intelligent_consultation uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

