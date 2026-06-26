# 🤝 贡献指南

感谢你对智能医疗管家平台的关注！欢迎任何形式的贡献。

---

## 📋 贡献方式

| 方式 | 说明 |
|------|------|
| 🐛 [提交 Bug](https://github.com/zgsddzwj/intelligent_consultation/issues/new?template=bug_report.md) | 发现问题后提交 Issue |
| ✨ [功能建议](https://github.com/zgsddzwj/intelligent_consultation/issues/new?template=feature_request.md) | 提出新功能想法 |
| 📝 文档改进 | 修正文档错误或补充说明 |
| 🔧 代码贡献 | 提交 Pull Request 修复问题或实现功能 |

---

## 🚀 快速开始贡献

### 1. Fork & Clone

```bash
# Fork 仓库后 clone 到本地
git clone https://github.com/<your-username>/intelligent_consultation.git
cd intelligent_consultation
git remote add upstream https://github.com/zgsddzwj/intelligent_consultation.git
```

### 2. 创建分支

```bash
# 从最新的 main 创建特性分支
git checkout main
git pull upstream main
git checkout -b feat/your-feature-name
```

**分支命名规范：**

| 前缀 | 用途 | 示例 |
|------|------|------|
| `feat/` | 新功能 | `feat/add-voice-input` |
| `fix/` | Bug 修复 | `fix/orchestrator-crash` |
| `docs/` | 文档变更 | `docs/update-api-guide` |
| `refactor/` | 代码重构 | `refactor/simplify-cache` |
| `test/` | 测试相关 | `test/add-agent-tests` |

### 3. 本地开发

```bash
# 后端
cd backend
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 前端
cd frontend
npm install
npm run dev
```

### 4. 代码规范

#### 后端 (Python)

```bash
# 格式化
uv run black app/
uv run isort app/

# 检查
uv run flake8 app/ --max-line-length=120 --ignore=E501,W503
uv run mypy app/ --ignore-missing-imports

# 测试
uv run pytest tests/unit/ -v --cov=app
```

**要求：**
- 遵循 [PEP 8](https://peps.python.org/pep-0008/) 规范
- 使用类型注解（Type Hints）
- 新功能需附带单元测试
- 公共函数/类需编写 Docstring

#### 前端 (TypeScript / React)

```bash
cd frontend
npm run lint     # ESLint 检查
npx tsc --noEmit # TypeScript 类型检查
npm run build    # 构建验证
```

**要求：**
- 使用 TypeScript 严格类型
- 组件使用函数式组件 + Hooks
- 遵循现有代码风格和目录结构

### 5. 提交代码

遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```bash
git add .
git commit -m "feat: 添加语音输入功能"
```

**提交信息格式：**

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

| type | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档变更 |
| `refactor` | 代码重构（不改变功能） |
| `test` | 测试相关 |
| `chore` | 构建/工具变更 |

### 6. 提交 Pull Request

```bash
git push origin feat/your-feature-name
```

然后在 GitHub 上创建 Pull Request，填写 PR 模板。

---

## ✅ PR 检查清单

提交 PR 前请确认：

- [ ] 代码通过本地测试 (`uv run pytest tests/unit/ -v`)
- [ ] 代码通过 Lint 检查 (`black`, `flake8`, `eslint`)
- [ ] 新功能附带对应的单元测试
- [ ] 提交信息符合 Conventional Commits 规范
- [ ] PR 描述清晰，关联相关 Issue
- [ ] 不包含敏感信息（API Key、密码等）

---

## 🏗️ 项目架构概览

了解项目结构有助于快速定位贡献方向：

```
backend/app/
├── agents/          # 多 Agent 系统（LangGraph 编排）
├── api/v1/          # API 路由层
├── common/          # 公共模块（异常、安全、追踪）
├── database/        # 数据库层（PostgreSQL + 读写分离）
├── infrastructure/  # 基础设施（缓存、监控、限流、仓储）
├── knowledge/       # 知识层（RAG + 知识图谱 + ML）
├── models/          # 数据模型（SQLAlchemy）
├── services/        # 业务服务层（LLM、缓存、Prompt）
└── main.py          # 应用入口
```

详细架构请参考 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

---

## 🧪 测试指南

### 运行测试

```bash
cd backend

# 单元测试
uv run pytest tests/unit/ -v --cov=app --cov-report=term

# 集成测试（需要 PostgreSQL + Redis）
uv run pytest tests/integration/ -v

# 并行测试
uv run pytest tests/unit/ -n auto --timeout=60
```

### 编写测试

- 单元测试放在 `backend/tests/unit/` 目录
- 使用 `pytest` + `pytest-asyncio`
- 参考已有的 `conftest.py` 中的 fixture
- 目标覆盖率：核心模块 > 80%

---

## 💬 交流与讨论

- 💡 **功能讨论**：先创建 [Discussion Issue](https://github.com/zgsddzwj/intelligent_consultation/issues) 讨论设计方案
- 🐛 **Bug 报告**：使用 Bug Report 模板
- ❓ **使用问题**：在 Issue 中提问

---

## 📜 行为准则

请保持友善和尊重。我们致力于为所有人提供一个友好的开源环境。

---

再次感谢你的贡献！🎉
