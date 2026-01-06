#!/bin/bash

# 智能医疗管家平台启动脚本

set -e

echo "=========================================="
echo "智能医疗管家平台 - 启动脚本"
echo "=========================================="

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo "错误: Docker未运行，请先启动Docker"
    exit 1
fi

# 检查.env文件
if [ ! -f "backend/.env" ]; then
    echo "警告: backend/.env 文件不存在，将使用默认配置"
    echo "请确保已配置QWEN_API_KEY"
fi

# 启动Docker服务
echo ""
echo "[1/3] 启动Docker服务..."
docker-compose up -d

# 等待服务就绪
echo ""
echo "[2/3] 等待服务就绪..."
sleep 10

# 检查服务状态
echo ""
echo "检查服务状态..."
docker-compose ps

# 初始化数据
echo ""
echo "[3/3] 初始化数据..."
echo "提示: 如果这是首次运行，请执行以下命令初始化数据："
echo "  cd backend"
echo "  python scripts/init_all.py"
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
echo "查看日志: docker-compose logs -f"
echo "停止服务: docker-compose down"
echo ""

