# ============================================
# 智能医疗管家平台 - 后端 Dockerfile
# 多阶段构建，优化镜像大小和安全性
# ============================================

# ========== 构建阶段 ==========
FROM python:3.11-slim AS builder

WORKDIR /build

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖文件，利用Docker缓存层
COPY requirements.txt .

# 安装Python依赖（不安装缓存以减小体积）
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ========== 运行阶段 ==========
FROM python:3.11-slim AS runtime

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 安装运行时依赖（最小化）
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

# 从构建阶段复制已安装的包
COPY --from=builder /install /usr/local

# 创建必要的目录
RUN mkdir -p /app/logs /app/data/documents /app/models && \
    chown -R appuser:appuser /app

# 切换到非root用户
USER appuser

# 复制应用代码
COPY . .

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

