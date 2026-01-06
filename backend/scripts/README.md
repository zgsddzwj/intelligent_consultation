# 脚本使用说明

## 初始化脚本

### 1. `init_all.py` - 一键初始化（推荐）
```bash
python scripts/init_all.py
```
执行所有初始化步骤：
- 数据库表初始化
- 医疗数据获取
- 知识图谱初始化
- 向量数据库数据加载

### 2. `init_db.py` - 初始化数据库表
```bash
python scripts/init_db.py
```
创建所有数据库表（users, consultations, knowledge_documents, agent_logs）

### 3. `init_knowledge_graph.py` - 初始化知识图谱
```bash
python scripts/init_knowledge_graph.py
```
在Neo4j中创建：
- 15个科室
- 13种疾病
- 18种症状
- 10种药物
- 5种检查项目
- 完整的关系网络

### 4. `fetch_medical_data.py` - 获取医疗数据
```bash
python scripts/fetch_medical_data.py
```
获取基础医疗数据并保存到JSON文件

### 5. `fetch_medical_data_enhanced.py` - 获取增强医疗数据
```bash
python scripts/fetch_medical_data_enhanced.py
```
获取更丰富的医疗数据，包括：
- 详细的疾病信息
- 药物详细信息
- 医疗指南文档

### 6. `load_sample_data.py` - 加载示例数据到向量数据库
```bash
python scripts/load_sample_data.py
```
将示例医疗文档处理并加载到Milvus向量数据库

### 7. `load_medical_knowledge.py` - 加载医疗知识
```bash
python scripts/load_medical_knowledge.py
```
将医疗数据加载到知识图谱和向量数据库

## 验证和测试脚本

### 8. `verify_setup.py` - 验证系统设置
```bash
python scripts/verify_setup.py
```
检查：
- 环境变量配置
- 目录结构
- Python依赖

### 9. `test_system.py` - 系统功能测试
```bash
python scripts/test_system.py
```
测试：
- API健康检查
- 知识图谱API
- 咨询功能

## 使用顺序

### 首次运行
```bash
# 1. 验证设置
python scripts/verify_setup.py

# 2. 一键初始化（推荐）
python scripts/init_all.py

# 3. 测试系统
python scripts/test_system.py
```

### 分步初始化
```bash
# 1. 初始化数据库
python scripts/init_db.py

# 2. 获取医疗数据
python scripts/fetch_medical_data_enhanced.py

# 3. 初始化知识图谱
python scripts/init_knowledge_graph.py

# 4. 加载数据
python scripts/load_sample_data.py
python scripts/load_medical_knowledge.py
```

## 注意事项

- 确保Docker服务已启动（PostgreSQL、Neo4j、Milvus等）
- 确保`.env`文件中的API密钥已配置
- 某些脚本需要等待服务完全启动后再运行

