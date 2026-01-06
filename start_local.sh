#!/bin/bash

# 本地启动脚本（使用conda环境）

set -e

echo "=========================================="
echo "智能医疗管家平台 - 本地启动脚本"
echo "=========================================="

# 激活conda环境
echo ""
echo "[1/4] 激活conda环境..."
source /opt/anaconda3/etc/profile.d/conda.sh
conda activate intelligent_consultation

# 检查数据库服务
echo ""
echo "[2/4] 检查数据库服务..."
sleep 5
docker-compose ps | grep -E "(postgres|redis|neo4j|milvus|minio)" | grep -q "Up" && echo "✓ 数据库服务运行中" || echo "⚠️  部分数据库服务可能未启动"

# 启动后端服务
echo ""
echo "[3/4] 启动后端服务..."
cd backend
echo "后端服务将在 http://localhost:8000 启动"
echo "API文档: http://localhost:8000/docs"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "后端服务PID: $BACKEND_PID"

# 等待后端启动
sleep 3

# 启动前端服务
echo ""
echo "[4/4] 启动前端服务..."
cd ../frontend
echo "前端服务将在 http://localhost:3000 启动"
npm run dev &
FRONTEND_PID=$!
echo "前端服务PID: $FRONTEND_PID"

echo ""
echo "=========================================="
echo "启动完成！"
echo "=========================================="
echo ""
echo "访问地址："
echo "  前端: http://localhost:3000"
echo "  后端API: http://localhost:8000"
echo "  API文档: http://localhost:8000/docs"
echo ""
echo "停止服务:"
echo "  kill $BACKEND_PID $FRONTEND_PID"
echo "  或按 Ctrl+C"
echo ""

# 等待用户中断
wait
