# 更新日志

本文件记录项目的显著变更。格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [3.3.1] - 2026-10-15

### 🔐 安全

- 管理端点 JWT 认证与管理员校验；注册禁止自选角色；生产强制开启认证
- 咨询记录越权访问（IDOR）修复；知识库写操作要求 admin/doctor 角色
- 本地对象存储路径穿越防护；登录失败锁定加入来源 IP 维度防定向锁号
- 用户信息端点归属校验，防邮箱枚举；/metrics 生产环境默认 404

### ⚡ 性能与稳定

- Agent 工具调用超时真正生效（共享限流 + daemon 线程）
- LLM 重试预算从最坏约 9 分钟收敛至约 2 分钟，Provider 熔断降级防乒乓
- 健康检查/图片分析/知识库上传等阻塞调用移入线程池，事件循环零阻塞
- RAG 检索栈收敛全局单例；语义缓存键加入模型参数；BM25 召回通道接线生效
- 语音文件磁盘 TTL 清理；KG 检索缓存淘汰上限；缓存 flush 节流

### 🧪 工程化

- 测试从 42 通过/3 失败修至 60 通过/全绿，补充安全加固回归测试
- pytest 默认 180s 超时保护；训练模型产物纳入 gitignore
- nginx 生产配置修复（麦克风权限/voice_files 代理/上传限制/安全头生效）
- k8s env 引用顺序、容器探针、CI 镜像扫描等部署阻断项修复

## [3.3.0] - 2026-09-10

### 🔐 安全

- 公开注册一律创建患者角色，禁止通过请求体自选 `admin` 提权
- 生产环境（`ENVIRONMENT=production`）强制开启认证中间件、强制关闭 DEBUG、限流 fail-closed
- 全部管理端点（用户管理/数据统计/系统监控/全量导出）要求 JWT 认证 + 管理员角色
- 修复咨询记录越权访问（IDOR）：历史接口按认证身份强制过滤，详情归属校验（越权返回 404 防枚举），续聊校验记录归属
- 知识库文档上传/删除与知识图谱实体/关系变更要求 admin/doctor 角色，防止匿名篡改医疗知识库
- `/metrics` 生产环境未配置令牌时返回 404；令牌比较改用常数时间比较
- 访问日志的 query string 落盘前脱敏（token/api_key 等不再进入日志）

### 🐛 修复

- Agent 健康检查端点因变量遮蔽 `fastapi.status` 必然 500；响应压缩中间件 `NameError` 静默失效
- CORS 中间件移至最外层：认证/限流的 401/429 响应与 preflight 请求正确携带 CORS 头
- 咨询消息 JSON 列改用 `MutableList`/`MutableDict`，修复原地修改不触发 UPDATE 导致对话历史静默丢失
- 意图分类器 SVM 推理特征空间与训练管线对齐（15 维统计特征 + label_encoder 标签映射）
- Milvus metadata 由 Python repr 改为 JSON 序列化；`ttl=None` 不再被默认 TTL 吞掉（prompt 模板静默过期）
- 统一响应包装中间件真正生效（旧实现对流式响应类型的判断使所有 JSON 响应从未被包装）
- JSON 日志格式修复（旧实现每条日志触发一次 loguru format_map KeyError）
- nginx 生产配置：麦克风权限（语音输入失效）、`/voice_files` 代理（TTS 404）、`client_max_body_size`（大图 413）、安全头继承（CSP 等从未生效）
- vite manualChunks 匹配顺序修复：图谱库不再被打进首屏 chunk，代码分割恢复
- k8s：`DATABASE_URL`/`NEO4J_AUTH` 的 `$(VAR)` 引用顺序错误（Pod 连不上库）、frontend 只读根文件系统缺可写挂载
- CI：Trivy 扫描镜像 tag 与 metadata-action 产出对齐（push 到 main 的扫描步骤不再必挂）

### ⚡ 性能

- 健康检查、图片分析、Agent 工具调用的同步阻塞调用移入线程池/带超时执行，事件循环不再被冻结
- 语义检索裁掉每次 RAG 查询一次的无效 LLM 调用；文档向量改单次批量编码
- RAG 检索栈（RAGTool/Embedder/DocumentProcessor/IntentClassifier）收敛为全局单例，消除 6 份重复实例
- Redis 客户端移除每操作前置 PING；Milvus 连通性探测改为本地检查，消除每请求额外统计 RPC

### 🧹 清理

- 删除 15 个零引用后端模块（死 MCP 包、占位 stub、未接线的读写分离、注入风险的 EXPLAIN 工具等）
- 删除 9 个未引用前端组件/钩子；图片上传校验逻辑迁移回线上入口
- 未知路径新增 404 兜底路由；favicon 落地（旧 `/vite.svg` 404）
- 删除 `ALLOWED_HOSTS`/`MCP_*`/`DATABASE_READ_URL` 等无效配置项与 configmap 死键

### 🧪 测试

- 根治测试假绿：conftest 的 except-skip、`return True` 假断言、错误 monkeypatch 目标全部修复
- 测试结果：51 通过 / 0 失败（修复前 42 通过 / 3 失败 / 3 错误）

### 📚 文档

- README / docs / .env.example / k8s configmap 与代码现状全面对齐（版本号、统一 LLM Provider、配置项逐键校验）
