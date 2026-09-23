# ✅ 生产上线检查清单

> 智能医疗管家平台 v3.3.0 - 上线前逐项核对
>
> 本清单基于 12 轮上线优化（后端性能/并发、前端类型与构建、部署链路修复）的最终验证结论整理。

## 1. 质量门禁（全部通过）

| 检查项 | 命令 | 通过标准 | 状态 |
|--------|------|----------|------|
| 前端 Lint | `cd frontend && npm run lint` | 0 error / 0 warning（`--max-warnings 0`） | ✅ |
| 前端类型检查 | `npx tsc --noEmit -p tsconfig.json` | 无错误 | ✅ |
| 前端生产构建 | `npm run build` | 构建成功，代码分割生效 | ✅ |
| 后端语法检查 | `python -m compileall -q backend/app` | 无输出即通过 | ✅ |
| 后端导入冒烟 | `python -c "from app.main import app; print(len(app.routes))"` | 路由数 55 | ✅ |
| 编排配置校验 | `docker compose config --quiet` | 无错误（含变量插值校验） | ✅ |

### 前端构建产物基线（gzip 后）

| Chunk | 体积 | 说明 |
|-------|------|------|
| 路由级 chunk | 0.6 ~ 27 KB | 全部懒加载 |
| graph-viz | 33 KB | react-force-graph 按需分包 |
| markdown | 35 KB | react-markdown 全家桶独立分包 |
| react-core | 49 KB | react / react-dom / router |
| vendor | 96 KB | 其余第三方库 |
| antd | 302 KB | 组件库整体（见 §7 遗留项） |

## 2. 环境变量与密钥

- [ ] `backend/.env` 已创建（**不入库**，`.gitignore` 已覆盖），至少包含：
  - `SECRET_KEY` — 生产环境（`ENVIRONMENT=production`）缺失时应用启动即报错（应用层 fail-fast，见 `backend/app/config.py`）
  - `SILICONFLOW_API_KEY` — LLM 主 Provider 密钥
  - 数据库 / Redis / Neo4j / Milvus / 对象存储连接配置
- [ ] Docker Compose 插值变量（根目录 `.env` 或 shell 环境提供，**compose 插值不读取 `backend/.env`**）：
  - `POSTGRES_USER` / `POSTGRES_PASSWORD`（默认 postgres）
  - `NEO4J_PASSWORD`（默认 medical123，**生产必须修改**）
  - `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD`（默认 minioadmin，**生产必须修改**）
  - `CORS_ORIGINS` / `TRUSTED_HOSTS`（默认仅 localhost，生产改为实际域名）
- [ ] 已知约定：`SECRET_KEY` / `SILICONFLOW_API_KEY` 由 `env_file: ./backend/.env` 注入容器，勿在 compose `environment` 段对其做 `${VAR}` 插值（插值读不到 env_file，会导致 `docker compose up` 失败）

## 3. 后端运行时（已具备）

- [x] 中间件栈：gzip 压缩、安全响应头（HSTS/CSP 仅生产启用）、TrustedHost 白名单、接口限流
- [x] K8s 兼容探针：`/health`、`/ready`、`/live`
- [x] `/metrics` 由 `METRICS_ACCESS_TOKEN` 保护
- [x] 优雅关闭（SIGTERM 处理）
- [x] 依赖服务 healthcheck 就绪后才启动 backend（`depends_on: condition: service_healthy`）
- [x] 异步路由中的同步阻塞操作已移入线程池；bcrypt 密码操作已线程池化
- [x] 对象存储 / Redis 连接失败自动降级（本地存储 / 无缓存），不阻塞启动

## 4. 部署步骤（Docker Compose）

```bash
# 1. 准备配置
cp backend/.env.example backend/.env && vim backend/.env   # 填写必填密钥

# 2. 校验编排配置（会暴露缺失的必填插值变量）
docker compose config --quiet

# 3. 构建并启动
docker compose up -d --build

# 4. 健康检查
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl -I http://localhost:3000/

# 5. 初始化数据（首次部署，见 docs/DEPLOYMENT.md）
```

Kubernetes 部署见 [k8s/README.md](../k8s/README.md)。

## 5. 上线后观察

- [ ] `docker compose logs -f backend` 无启动错误
- [ ] `/ready` 返回 200 后再接入流量（网关 / 负载均衡探针指向 `/ready`）
- [ ] 前端页面首屏加载正常，聊天流式输出、语音输入输出、知识图谱三个主链路人工验证
- [ ] Prometheus 抓取 `/metrics`（携带 `METRICS_ACCESS_TOKEN`）

## 6. 回滚预案

- 镜像回滚：`docker compose up -d --no-deps --build backend`（回退到上一个 git tag 构建同理）
- 数据库：确认 alembic 迁移可回退（`alembic downgrade -1`）后再执行升级
- 配置回滚：`backend/.env` 与根目录插值变量变更前先备份

## 7. 已知遗留项（不阻塞上线）

| 项目 | 影响 | 说明 |
|------|------|------|
| antd chunk 995 KB 超 vite 500 KB 警告阈值 | 仅构建告警 | gzip 后 302 KB，为组件库整体，按需引入改造收益有限 |
| Windows 控制台 GBK 编码下 loguru 打印 `✓/✗` 报 UnicodeEncodeError | 仅本地开发日志显示 | 生产 Linux（UTF-8）无影响 |
| 意图分类模型文件缺失 | 自动降级规则分类 | 有日志提示，可按需补充模型文件 |
| DoctorDashboard 使用演示数据 | 仅医生工作台 | 页面已加「演示数据」标注，接入真实接口时替换 |
