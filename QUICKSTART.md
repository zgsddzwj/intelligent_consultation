# 快速启动指南

## 1. 环境准备

确保已安装：
- Docker 和 Docker Compose
- Python 3.11+（用于运行初始化脚本）

## 2. 验证系统设置

```bash
cd backend
python scripts/verify_setup.py
```

这将检查：
- 环境变量配置
- 目录结构
- Python依赖

## 3. 配置环境变量

`.env` 文件已创建，包含您的阿里云百炼API密钥。

如需修改，编辑 `backend/.env` 文件。

**重要**：确保 `QWEN_API_KEY` 已正确配置！

## 4. 初始化Neo4j知识图谱

```bash
# 确保Neo4j服务已启动（通过Docker Compose）
cd backend
python scripts/init_knowledge_graph.py
```

这将创建：
- 15个科室
- 13种疾病
- 18种症状
- 10种药物
- 5种检查项目
- 完整的关系网络

**或者使用一键初始化**：
```bash
python scripts/init_all.py
```

这将自动执行：
1. 数据库表初始化
2. 医疗数据获取
3. 知识图谱初始化
4. 向量数据库数据加载

## 5. 启动服务

### 方式一：使用Docker Compose（推荐）

```bash
# 在项目根目录
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f backend
```

### 方式二：本地运行

```bash
# 启动后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# 启动前端（新终端）
cd frontend
npm install
npm run dev
```

## 6. 访问系统

- **知识图谱可视化**：http://localhost:3000/knowledge-graph
- **在线问诊**：http://localhost:3000/
- **API文档**：http://localhost:8000/docs
- **Neo4j浏览器**：http://localhost:7474（用户名/密码：neo4j/neo4j）

## 7. 功能使用

### 知识图谱可视化
1. 访问 `/knowledge-graph` 页面
2. 选择科室进行筛选
3. 点击节点查看详情
4. 拖拽节点调整布局

### 在线问诊
1. 访问首页
2. 输入问题或上传图片
3. 系统自动识别意图并路由到相应Agent
4. 查看回答和来源信息

### 图片医疗术语识别
1. 在问诊界面点击"图片"按钮
2. 上传包含医疗信息的图片
3. 系统自动识别并提取医疗术语
4. 显示分析结果和知识图谱关联

## 8. 验证功能

### 测试知识图谱
```bash
# 在Neo4j浏览器中执行
MATCH (n) RETURN n LIMIT 25
```

### 测试API
```bash
# 测试健康检查
curl http://localhost:8000/health

# 测试知识图谱API
curl -X POST http://localhost:8000/api/v1/knowledge/graph/visualization \
  -H "Content-Type: application/json" \
  -d '{"department": "心内科"}'
```

## 9. 常见问题

### Neo4j连接失败
- 检查Neo4j服务是否启动：`docker-compose ps neo4j`
- 检查连接配置：`backend/.env` 中的 `NEO4J_URI`

### Milvus连接失败
- 确保etcd和minio服务已启动
- 检查Milvus健康状态：`docker-compose logs milvus`

### API密钥错误
- 确认 `QWEN_API_KEY` 在 `.env` 文件中正确配置
- 检查API密钥是否有效

## 10. 下一步

- 加载更多医疗文档到RAG系统
- 扩展知识图谱数据
- 优化Agent提示词
- 添加更多可视化功能

