# 数据目录说明

## ⚠️ 重要提示

**本目录仅用于本地开发环境！**

在生产环境中，文档文件应存储在**对象存储**（MinIO/S3/OSS）中，而不是本地文件系统。

## 数据存储架构

### 生产环境（推荐）

```
用户上传文档
    ↓
[API层] 验证和接收
    ↓
[对象存储服务] 上传到MinIO/S3/OSS
    ├─ 文档文件 → 对象存储（MinIO/S3/OSS）
    ├─ 文档元数据 → PostgreSQL数据库
    └─ 向量数据 → Milvus向量数据库
```

### 本地开发环境

```
data/ 目录（临时存储）
    ├─ documents/     # 本地文档（仅开发用）
    ├─ knowledge_graph/  # 知识图谱JSON数据（仅开发用）
    └─ sample/        # 示例数据
```

## 目录结构

```
data/
├── documents/          # 医疗文档（PDF、Word等）- 仅本地开发用
│   ├── guidelines/     # 医疗指南
│   ├── manuals/        # 操作手册
│   └── papers/         # 医学论文
├── knowledge_graph/    # 知识图谱数据（JSON格式）- 仅开发用
│   ├── entities/       # 实体数据（JSON格式）
│   └── relationships/  # 关系数据（JSON格式）
└── sample/             # 示例数据
```

## 使用说明

### 1. 文档上传（生产环境）

**推荐方式**：通过API上传文档，系统会自动存储到对象存储。

```bash
# 使用API上传
curl -X POST http://localhost:8000/api/v1/knowledge/documents \
  -F "file=@document.pdf" \
  -F "source=guidelines"
```

文档会自动：
1. 上传到对象存储（MinIO/S3/OSS）
2. 解析和分块
3. 向量化并存储到Milvus
4. 元数据存储到PostgreSQL

### 2. 本地开发环境

**仅用于开发测试**：将文档放入 `documents/` 目录，然后使用脚本批量上传：

```bash
# 批量上传本地文档到对象存储
cd backend
python scripts/load_medical_knowledge.py --upload-to-storage

# 从对象存储加载到向量数据库
python scripts/load_medical_knowledge.py --use-storage
```

**支持的格式**：
- PDF (.pdf)
- Word (.docx, .doc)
- PowerPoint (.pptx, .ppt)
- 文本文件 (.txt)

### 3. 知识图谱数据

知识图谱数据通过脚本自动从Neo4j加载，也可以手动导入JSON格式的实体和关系数据。

**注意**：`knowledge_graph/` 目录下的JSON文件仅用于开发环境的数据导入，生产环境数据存储在Neo4j数据库中。

**数据格式示例**：

`entities/diseases.json`:
```json
[
  {
    "name": "高血压",
    "type": "Disease",
    "properties": {
      "description": "血压持续升高的疾病",
      "category": "心血管疾病"
    }
  }
]
```

`relationships/treats.json`:
```json
[
  {
    "from": "药物名称",
    "to": "疾病名称",
    "type": "TREATS",
    "properties": {
      "effectiveness": "high"
    }
  }
]
```

### 4. 示例数据

`sample/` 目录包含示例数据，用于测试和演示。

## 数据加载

### 生产环境

1. **知识图谱初始化**：
   ```bash
   cd backend
   python scripts/init_knowledge_graph.py
   ```

2. **文档上传**：
   - 通过API上传（推荐）
   - 或批量上传本地文档：`python scripts/load_medical_knowledge.py --upload-to-storage`

3. **从对象存储加载到向量数据库**：
   ```bash
   python scripts/load_medical_knowledge.py --use-storage
   ```

### 本地开发环境

1. **一键初始化**：
   ```bash
   python scripts/init_all.py
   ```

2. **从本地文件系统加载**（仅开发用）：
   ```bash
   python scripts/load_medical_knowledge.py
   ```

## 数据存储位置

| 数据类型 | 开发环境 | 生产环境 |
|---------|---------|---------|
| 文档文件 | `data/documents/` | 对象存储（MinIO/S3/OSS） |
| 文档元数据 | PostgreSQL | PostgreSQL |
| 向量数据 | Milvus | Milvus |
| 知识图谱 | Neo4j | Neo4j |

## 迁移指南

### 从本地文件系统迁移到对象存储

```bash
# 1. 批量上传本地文档到对象存储
cd backend
python scripts/load_medical_knowledge.py --upload-to-storage

# 2. 验证上传结果
# 检查对象存储中的文件

# 3. 从对象存储加载到向量数据库
python scripts/load_medical_knowledge.py --use-storage
```

## 注意事项

- ⚠️ **Git仓库不包含数据文件**：`data/` 目录下的实际文件不会被提交到Git
- ⚠️ **生产环境必须使用对象存储**：本地文件系统不支持多实例部署
- ✅ **文档文件会自动处理**：包括OCR识别图片中的文字
- ✅ **知识图谱数据会验证格式**：确保数据质量
- ✅ **大量数据加载可能需要较长时间**：请耐心等待
- ✅ **建议定期备份重要数据**：对象存储和数据库都需要备份

