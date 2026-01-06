# 完整系统设置指南

## 系统审查结果

经过全面审查，系统核心功能已完整实现，可以直接运行使用。

## ✅ 已实现的核心功能

### 1. 后端API服务
- ✅ FastAPI应用完整实现
- ✅ 所有API端点已实现
- ✅ 错误处理和日志记录
- ✅ 数据库连接（支持延迟初始化）

### 2. Agent系统
- ✅ 4个Agent全部实现（医生、健康管家、客服、运营）
- ✅ LangGraph工作流编排
- ✅ 意图识别和路由
- ✅ 风险评估机制

### 3. 知识系统
- ✅ RAG检索系统（支持降级）
- ✅ Neo4j知识图谱（延迟连接）
- ✅ Milvus向量数据库（延迟连接）
- ✅ 知识图谱可视化API

### 4. 前端功能
- ✅ React应用完整实现
- ✅ 问诊对话界面
- ✅ 知识图谱可视化
- ✅ 图片上传功能

### 5. 图片分析
- ✅ Qwen-VL图片识别
- ✅ 医疗术语提取
- ✅ 知识图谱关联

## 🚀 快速启动（3步）

### 步骤1: 启动服务
```bash
docker-compose up -d
```

### 步骤2: 初始化数据（首次运行）
```bash
cd backend
python scripts/init_all.py
```

### 步骤3: 访问系统
- 问诊界面: http://localhost:3000
- 知识图谱: http://localhost:3000/knowledge-graph
- API文档: http://localhost:8000/docs

## 📋 详细启动流程

### 1. 验证环境
```bash
cd backend
python scripts/verify_setup.py
```

### 2. 启动Docker服务
```bash
# 在项目根目录
docker-compose up -d

# 等待所有服务启动（约30-60秒）
docker-compose ps
```

### 3. 初始化数据

#### 方式A: 一键初始化（推荐）
```bash
cd backend
python scripts/init_all.py
```

#### 方式B: 分步初始化
```bash
cd backend

# 1. 初始化数据库表
python scripts/init_db.py

# 2. 获取医疗数据
python scripts/fetch_medical_data_enhanced.py

# 3. 初始化知识图谱
python scripts/init_knowledge_graph.py

# 4. 加载数据到向量数据库
python scripts/load_sample_data.py
python scripts/load_medical_knowledge.py
```

### 4. 测试系统
```bash
cd backend
python scripts/test_system.py
```

## 🎯 用户可以直接使用的功能

### ✅ 在线问诊
1. 访问 http://localhost:3000
2. 在输入框输入问题，例如：
   - "我最近有点头痛，应该怎么办？"
   - "高血压患者需要注意什么？"
   - "糖尿病的症状有哪些？"
3. 点击"发送"或按Enter
4. 系统自动识别意图，路由到合适的Agent
5. 获得专业的医疗咨询回答

### ✅ 知识图谱可视化
1. 访问 http://localhost:3000/knowledge-graph
2. 选择科室进行筛选
3. 查看疾病、症状、药物之间的关系
4. 点击节点查看详情

### ✅ 图片医疗术语识别
1. 在问诊界面点击"图片"按钮
2. 上传包含医疗信息的图片
3. 系统自动识别医疗术语
4. 显示分析结果和知识图谱关联

## 📊 医疗知识库数据来源

### 当前数据
- **ICD-10疾病编码**：基于WHO标准
- **药物信息**：基于国家药监局数据格式
- **医疗指南**：示例数据（可扩展）

### 数据获取脚本
- `scripts/fetch_medical_data.py` - 基础数据获取
- `scripts/fetch_medical_data_enhanced.py` - 增强版数据获取

### 扩展数据源（可选）
1. **PubMed API**：医学文献（需要API key）
2. **ICD-10公开数据集**：GitHub上的公开数据
3. **医疗指南网站**：从公开网站爬取（需遵守使用条款）

## ⚠️ 重要提示

### 系统容错机制
- **数据库未连接**：咨询功能仍可工作，但无法保存记录
- **Milvus未连接**：RAG检索返回空结果，但不会崩溃
- **Neo4j未连接**：知识图谱功能不可用，但其他功能正常

### 必需配置
- ✅ Qwen API密钥（已配置）
- ⚠️ 数据库服务（PostgreSQL、Redis、Neo4j、Milvus）

### 可选配置
- 更多医疗文档（上传到 `data/documents/`）
- 扩展知识图谱数据（运行初始化脚本）

## 🔍 验证系统是否正常工作

### 快速检查
```bash
# 1. 检查API
curl http://localhost:8000/health

# 2. 测试咨询
curl -X POST http://localhost:8000/api/v1/consultation/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你好"}'

# 3. 检查知识图谱
curl http://localhost:8000/api/v1/knowledge/graph/departments
```

### 完整测试
```bash
cd backend
python scripts/test_system.py
```

## 📝 使用示例

### 示例1: 疾病咨询
```
用户: "我最近经常头痛，还伴有头晕，这是什么原因？"
系统: [自动识别为医疗诊断咨询]
      [路由到医生Agent]
      [检索相关医疗文献]
      [查询知识图谱]
      [生成专业回答 + 来源标注 + 风险提示]
```

### 示例2: 健康管理
```
用户: "我想制定一个高血压的健康管理计划"
系统: [自动识别为健康管理咨询]
      [路由到健康管家Agent]
      [生成个性化健康计划]
```

### 示例3: 知识图谱查询
```
用户: 在知识图谱页面选择"心内科"
系统: [显示心内科相关的所有疾病、症状、药物]
      [可视化展示关系网络]
```

## 🎉 系统已就绪！

所有核心功能已实现，系统可以直接运行使用。用户可以通过Web界面进行：
- ✅ 在线医疗咨询
- ✅ 查看知识图谱
- ✅ 上传图片识别医疗术语

开始使用吧！

