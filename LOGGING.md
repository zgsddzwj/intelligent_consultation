# 日志查看指南

## 📍 日志位置

### 后端日志

#### 1. 应用日志文件
- **位置**: `backend/logs/app.log`
- **格式**: 文本格式，包含时间戳、级别、模块、消息
- **查看方式**:
  ```bash
  # 查看最新日志
  tail -f backend/logs/app.log
  
  # 查看最后100行
  tail -100 backend/logs/app.log
  
  # 搜索错误
  grep ERROR backend/logs/app.log
  ```

#### 2. 控制台输出（开发模式）
- **位置**: 启动服务的终端
- **格式**: 彩色格式，便于阅读
- **说明**: 使用 `uvicorn --reload` 启动时，日志会输出到控制台

#### 3. 后台运行日志（nohup）
- **位置**: `/tmp/backend.log`
- **说明**: 如果使用 `nohup` 启动服务，日志会输出到这里
- **查看方式**:
  ```bash
  tail -f /tmp/backend.log
  ```

### 前端日志

#### 1. 控制台输出
- **位置**: 启动服务的终端
- **格式**: Vite开发服务器日志
- **说明**: 包含编译信息、代理错误、HMR更新等

#### 2. 后台运行日志（nohup）
- **位置**: `/tmp/frontend.log`
- **说明**: 如果使用 `nohup` 启动服务，日志会输出到这里
- **查看方式**:
  ```bash
  tail -f /tmp/frontend.log
  ```

#### 3. 浏览器控制台
- **位置**: 浏览器开发者工具（F12）
- **说明**: 前端应用的运行时日志、错误、网络请求等

### Docker日志

如果使用Docker Compose运行：

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看后端日志
docker-compose logs -f backend

# 查看前端日志
docker-compose logs -f frontend

# 查看最后100行
docker-compose logs --tail=100 backend
```

## 🔍 日志级别

后端日志级别（可在 `backend/.env` 中配置）：
- `DEBUG`: 详细调试信息
- `INFO`: 一般信息（默认）
- `WARNING`: 警告信息
- `ERROR`: 错误信息
- `CRITICAL`: 严重错误

## 📝 常用日志查看命令

### 实时查看日志
```bash
# 后端日志（文件）
tail -f backend/logs/app.log

# 后端日志（nohup）
tail -f /tmp/backend.log

# 前端日志（nohup）
tail -f /tmp/frontend.log

# Docker日志
docker-compose logs -f
```

### 搜索日志
```bash
# 搜索错误
grep -i error backend/logs/app.log

# 搜索特定模块
grep "app.api" backend/logs/app.log

# 搜索特定时间
grep "2026-01-06 18:" backend/logs/app.log

# 搜索并显示上下文
grep -A 5 -B 5 "ERROR" backend/logs/app.log
```

### 统计日志
```bash
# 统计错误数量
grep -c ERROR backend/logs/app.log

# 统计各日志级别
grep -o "ERROR\|WARNING\|INFO" backend/logs/app.log | sort | uniq -c
```

## 🛠️ 日志配置

### 修改日志级别

编辑 `backend/.env` 文件：
```env
LOG_LEVEL=DEBUG  # 或 INFO, WARNING, ERROR, CRITICAL
```

### 修改日志文件路径

编辑 `backend/app/config.py` 或 `backend/.env`：
```env
LOG_FILE=./logs/app.log
```

### 日志轮转

日志文件会自动轮转：
- **大小限制**: 10 MB
- **保留时间**: 7天
- **压缩**: 自动压缩旧日志

## ⚠️ 常见问题

### 1. 日志文件为空

**原因**: 
- 日志格式错误（已修复）
- 日志路径不正确
- 权限问题

**解决**:
```bash
# 检查日志目录权限
ls -la backend/logs/

# 手动创建日志目录
mkdir -p backend/logs
chmod 755 backend/logs
```

### 2. 看不到实时日志

**解决**:
- 使用 `tail -f` 命令实时查看
- 检查服务是否正在运行
- 检查日志文件路径是否正确

### 3. 日志太多

**解决**:
- 提高日志级别（如改为 WARNING）
- 使用日志轮转功能
- 定期清理旧日志

## 📊 日志格式说明

### 后端日志格式

```
2026-01-06 18:04:35 | INFO     | app.api.logging_middleware:dispatch:41 - HTTP响应
```

格式说明：
- `2026-01-06 18:04:35`: 时间戳
- `INFO`: 日志级别
- `app.api.logging_middleware`: 模块名
- `dispatch:41`: 函数名和行号
- `HTTP响应`: 日志消息

### 前端日志格式

Vite开发服务器日志：
```
5:58:20 PM [vite] http proxy error at /api/v1/image_analysis/analyze:
Error: connect ETIMEDOUT 127.0.0.1:8000
```

## 🎯 快速查看日志

### 一键查看所有日志
```bash
# 创建别名（添加到 ~/.zshrc 或 ~/.bashrc）
alias logs-backend='tail -f /Users/Wangjian/projects/intelligent_consultation/backend/logs/app.log'
alias logs-frontend='tail -f /tmp/frontend.log'
alias logs-all='tail -f /tmp/backend.log /tmp/frontend.log'
```

### 使用脚本查看
```bash
# 查看后端日志
./scripts/view_backend_logs.sh

# 查看前端日志
./scripts/view_frontend_logs.sh
```

## 📌 当前日志状态

✅ **日志已正常工作！**

- **后端日志文件**: `backend/logs/app.log` ✅ (已修复，正常写入)
- **后端控制台**: 启动服务的终端（彩色格式）
- **后端nohup**: `/tmp/backend.log` (如果使用nohup启动)
- **前端控制台**: 启动服务的终端
- **前端nohup**: `/tmp/frontend.log` (如果使用nohup启动)

## 🚀 快速查看日志

### 方法一：使用查看脚本
```bash
./view_logs.sh
```

### 方法二：直接查看
```bash
# 实时查看后端日志
tail -f backend/logs/app.log

# 实时查看前端日志（nohup）
tail -f /tmp/frontend.log

# 同时查看两个日志
tail -f backend/logs/app.log /tmp/frontend.log
```

### 方法三：使用Docker
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
```

