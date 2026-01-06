#!/bin/bash
# 日志查看脚本

echo "=== 日志查看工具 ==="
echo ""
echo "1. 后端日志 (backend/logs/app.log)"
echo "2. 后端日志 (nohup: /tmp/backend.log)"
echo "3. 前端日志 (nohup: /tmp/frontend.log)"
echo "4. Docker日志"
echo "5. 查看所有日志"
echo ""
read -p "请选择 (1-5): " choice

case $choice in
    1)
        if [ -f "backend/logs/app.log" ]; then
            tail -f backend/logs/app.log
        else
            echo "日志文件不存在: backend/logs/app.log"
        fi
        ;;
    2)
        if [ -f "/tmp/backend.log" ]; then
            tail -f /tmp/backend.log
        else
            echo "日志文件不存在: /tmp/backend.log"
        fi
        ;;
    3)
        if [ -f "/tmp/frontend.log" ]; then
            tail -f /tmp/frontend.log
        else
            echo "日志文件不存在: /tmp/frontend.log"
        fi
        ;;
    4)
        docker-compose logs -f
        ;;
    5)
        echo "同时查看后端和前端日志..."
        tail -f /tmp/backend.log /tmp/frontend.log 2>/dev/null || echo "部分日志文件不存在"
        ;;
    *)
        echo "无效选择"
        ;;
esac
