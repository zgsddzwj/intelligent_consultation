# ============================================
# 智能医疗管家平台 - 后端 Dockerfile
# 多阶段构建，使用 uv 管理依赖，优化镜像大小和安全性
# ============================================

# ========== 构建阶段 ==========
FROM python:3.11-slim AS builder

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /build

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖文件，利用Docker缓存层
COPY pyproject.toml uv.lock ./

# 使用 uv 安装依赖到虚拟环境（不安装项目本身，仅依赖）
RUN uv sync --frozen --no-dev --no-install-project

# ========== 运行阶段 ==========
FROM python:3.11-slim AS runtime

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# 安装运行时依赖并创建用户（合并为单个RUN减少层数）
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser \
    && mkdir -p /app/logs /app/data/documents /app/models \
    && chown -R appuser:appuser /app

# 从构建阶段复制虚拟环境
COPY --from=builder --chown=appuser:appuser /build/.venv /app/.venv

# 切换到非root用户
USER appuser

# 复制应用代码
COPY --chown=appuser:appuser . .

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
