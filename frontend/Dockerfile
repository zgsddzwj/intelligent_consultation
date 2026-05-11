# ============================================
# 智能医疗管家平台 - 前端 Dockerfile
# 支持开发模式和生产构建两种方式
# ============================================

# ========== 构建阶段 ==========
FROM node:18-alpine AS builder

WORKDIR /build

# 复制package文件（先复制以利用缓存）
COPY package*.json ./

# 安装依赖
RUN npm ci --silent && npm cache clean --force

# 复制源代码
COPY . .

# 构建生产版本
RUN npm run build


# ========== 生产运行阶段（默认） ==========
FROM nginx:alpine AS production

# 复制构建产物到nginx目录
COPY --from=builder /build/dist /usr/share/nginx/html

# 自定义nginx配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 暴露端口
EXPOSE 80

# 启动nginx
CMD ["nginx", "-g", "daemon off;"]


# ========== 开发环境 ==========
FROM node:18-alpine AS development

WORKDIR /app

# 设置开发环境变量
ENV NODE_ENV=development \
    CHOKIDAR_USEPOLLING=true \
    WATCHPACK_POLLING=true

# 复制package文件
COPY package*.json ./

# 安装依赖
RUN npm install && npm cache clean --force

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 3000

# 启动开发服务器
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
