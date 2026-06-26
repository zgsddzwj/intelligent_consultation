# 脚本使用说明

本目录存放后端所有管理脚本，按用途分类到子目录中。所有脚本均在 `backend/` 目录下通过 `uv run` 执行。

## 目录结构

```
scripts/
├── setup/          # 系统初始化与验证
├── data/           # 数据获取与加载
├── kg/             # 知识图谱导入
├── ml/             # ML 模型训练
└── maintenance/    # 运维与测试
```

## setup/ - 系统初始化与验证

### `setup/init_all.py` - 一键初始化（推荐）
```bash
uv run python scripts/setup/init_all.py
```
执行所有初始化步骤：数据库表、医疗数据获取、知识图谱初始化、向量数据库数据加载。

### `setup/init_knowledge_graph.py` - 初始化知识图谱
```bash
uv run python scripts/setup/init_knowledge_graph.py
```
在 Neo4j 中创建科室、疾病、症状、药物、检查项目及关系网络。

### `setup/verify_setup.py` - 验证系统设置
```bash
uv run python scripts/setup/verify_setup.py
```
检查环境变量配置、目录结构、Python 依赖。

## data/ - 数据获取与加载

### `data/fetch_medical_data.py` - 获取基础医疗数据
```bash
uv run python scripts/data/fetch_medical_data.py
```

### `data/fetch_medical_data_enhanced.py` - 获取增强医疗数据
```bash
uv run python scripts/data/fetch_medical_data_enhanced.py
```
获取更丰富的医疗数据（疾病详情、药物详情、医疗指南）。

### `data/load_sample_data.py` - 加载示例数据到向量数据库
```bash
uv run python scripts/data/load_sample_data.py
```

### `data/load_medical_knowledge.py` - 加载医疗知识
```bash
uv run python scripts/data/load_medical_knowledge.py
```
将医疗数据加载到知识图谱和向量数据库。

### `data/check_import_status.py` - 检查知识图谱导入状态
```bash
uv run python scripts/data/check_import_status.py
```

## kg/ - 知识图谱导入

### `kg/import_medical_kg.py` - 从外部数据源导入知识图谱
```bash
uv run python scripts/kg/import_medical_kg.py
```

### `kg/import_medical_kg_realtime.py` - 实时进度导入
```bash
uv run python scripts/kg/import_medical_kg_realtime.py
```

## ml/ - ML 模型训练

### `ml/train_ml_models.py` - 训练 ML 模型
```bash
# 训练所有模型
uv run python scripts/ml/train_ml_models.py

# 仅训练指定模型
uv run python scripts/ml/train_ml_models.py --model intent

# 列出可用模型
uv run python scripts/ml/train_ml_models.py --list-models
```

### `ml/prepare_training_data.py` - 准备训练数据
```bash
uv run python scripts/ml/prepare_training_data.py
```

## maintenance/ - 运维与测试

### `maintenance/migrate_to_object_storage.py` - 迁移到对象存储
```bash
uv run python scripts/maintenance/migrate_to_object_storage.py
```

### `maintenance/test_system.py` - 系统功能测试
```bash
uv run python scripts/maintenance/test_system.py
```
测试 API 健康检查、知识图谱 API、咨询功能。

## 使用顺序

### 首次运行
```bash
cd backend
# 1. 验证设置
uv run python scripts/setup/verify_setup.py

# 2. 一键初始化（推荐）
uv run python scripts/setup/init_all.py

# 3. 训练 ML 模型
uv run python scripts/ml/train_ml_models.py

# 4. 测试系统
uv run python scripts/maintenance/test_system.py
```

### 分步初始化
```bash
cd backend
uv run python scripts/data/fetch_medical_data_enhanced.py
uv run python scripts/setup/init_knowledge_graph.py
uv run python scripts/data/load_sample_data.py
uv run python scripts/data/load_medical_knowledge.py
```

## 注意事项

- 确保依赖服务已启动（PostgreSQL、Neo4j、Milvus、Redis 等，可用 `docker compose up -d`）
- 确保 `.env` 文件中的 API 密钥已配置
- 某些脚本需要等待服务完全启动后再运行
