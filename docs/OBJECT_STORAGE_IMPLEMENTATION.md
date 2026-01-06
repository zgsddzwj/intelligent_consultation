# 对象存储集成与文档管理优化总结

## 完成时间
2024年

## 概述
将文档存储从本地文件系统迁移到对象存储（MinIO/S3/OSS），实现企业级文档管理架构，确保多实例部署、水平扩展和数据持久化。

## 问题分析

### 原有问题
1. **文档直接存储在本地文件系统** (`./data/documents`)
   - Git仓库不应该包含数据文件
   - 多实例部署时文件无法共享
   - 容器重启后数据可能丢失
   - 无法水平扩展
   - 不符合企业级最佳实践

2. **数据存储混乱**
   - 文档文件、元数据、向量数据存储位置不清晰

### 解决方案
- **文档文件** → 对象存储（MinIO/S3/OSS）
- **文档元数据** → PostgreSQL数据库
- **向量数据** → Milvus向量数据库
- **知识图谱** → Neo4j图数据库
- **data目录** → 仅作为本地开发临时目录或挂载点

## 实施内容

### 一、对象存储服务封装 ✅

#### 1.1 创建对象存储服务
- **文件**: `backend/app/services/object_storage.py` (新建)
  - 封装MinIO/S3/OSS客户端
  - 支持多种对象存储后端（MinIO、AWS S3、阿里云OSS、本地存储）
  - 实现文件上传、下载、删除、列表等操作
  - 支持预签名URL生成（用于直接下载）
  - 自动降级机制（对象存储不可用时使用本地存储）

#### 1.2 配置对象存储
- **文件**: `backend/app/config.py`
  - 添加对象存储配置项：
    - `OBJECT_STORAGE_TYPE`: "minio" | "s3" | "oss" | "local"
    - `OBJECT_STORAGE_ENDPOINT`: MinIO/S3/OSS端点
    - `OBJECT_STORAGE_ACCESS_KEY`: 访问密钥
    - `OBJECT_STORAGE_SECRET_KEY`: 密钥
    - `OBJECT_STORAGE_BUCKET`: 存储桶名称
    - `OBJECT_STORAGE_REGION`: 区域（S3/OSS需要）
    - `OBJECT_STORAGE_USE_SSL`: 是否使用SSL

### 二、数据模型更新 ✅

#### 2.1 更新KnowledgeDocument模型
- **文件**: `backend/app/models/knowledge.py`
  - 添加 `object_storage_key` 字段（对象存储键）
  - 添加 `storage_type` 字段（存储类型：local, minio, s3, oss）
  - 添加 `storage_bucket` 字段（存储桶名称）
  - 添加 `file_size` 字段（文件大小）
  - 保留 `file_path` 字段用于向后兼容（标记为deprecated）

#### 2.2 数据库索引
- **文件**: `backend/app/database/indexes.py`
  - 添加 `object_storage_key` 索引
  - 添加 `storage_type` 索引

### 三、文档上传API重构 ✅

#### 3.1 重构文档上传接口
- **文件**: `backend/app/api/v1/knowledge.py`
  - 修改 `upload_document` 函数
  - 上传流程：
    1. 接收文件并验证大小
    2. 上传到对象存储
    3. 临时下载到本地处理（处理完删除）
    4. 处理文档（解析、分块）
    5. 存储元数据到PostgreSQL
    6. 存储向量到Milvus
    7. 返回文档信息（包含对象存储URL）

#### 3.2 添加文档下载接口
- **文件**: `backend/app/api/v1/knowledge.py`
  - 新增 `GET /documents/{document_id}/download` 接口
  - 支持直接下载或生成预签名URL
  - 支持权限验证
  - 向后兼容本地文件系统

#### 3.3 添加文档删除接口
- **文件**: `backend/app/api/v1/knowledge.py`
  - 新增 `DELETE /documents/{document_id}` 接口
  - 删除对象存储中的文件
  - 删除数据库记录
  - 可选删除Milvus中的向量

### 四、文档处理流程优化 ✅

#### 4.1 更新DocumentProcessor
- **文件**: `backend/app/knowledge/rag/document_processor.py`
  - 新增 `process_document_from_storage` 方法
  - 支持从对象存储读取文件
  - 临时下载到本地处理（处理完自动删除）
  - 优化大文件处理流程

#### 4.2 更新数据加载脚本
- **文件**: `backend/scripts/load_medical_knowledge.py`
  - 新增 `upload_local_documents_to_storage` 函数
  - 支持批量上传本地文档到对象存储
  - 支持从对象存储加载文档
  - 添加命令行参数：`--upload-to-storage` 和 `--use-storage`

### 五、data目录说明更新 ✅

#### 5.1 更新data/README.md
- **文件**: `data/README.md`
  - 明确说明这是**本地开发临时目录**
  - 生产环境使用对象存储
  - 说明数据存储架构
  - 添加迁移指南

#### 5.2 更新.gitignore
- **文件**: `.gitignore`
  - 确保data目录下的实际文件不被提交
  - 只保留.gitkeep文件

### 六、配置和部署更新 ✅

#### 6.1 更新docker-compose.yml
- **文件**: `docker-compose.yml`
  - 确保MinIO配置正确
  - 添加对象存储环境变量到backend服务
  - 添加MinIO健康检查依赖

#### 6.2 更新k8s配置
- **文件**: `k8s/configmap.yaml` 和 `k8s/secrets.yaml`
  - 添加对象存储配置到ConfigMap
  - 添加对象存储密钥到Secrets
  - 更新backend.yaml，添加对象存储环境变量
  - 移除data目录的PVC（生产环境不需要）

### 七、依赖添加 ✅

#### 7.1 添加对象存储客户端库
- **文件**: `backend/requirements.txt`
  - `minio==7.2.0` - MinIO客户端
  - `boto3==1.34.0` - AWS S3客户端（可选）
  - `oss2==2.18.4` - 阿里云OSS客户端（可选）

### 八、数据迁移脚本 ✅

#### 8.1 创建迁移脚本
- **文件**: `backend/scripts/migrate_to_object_storage.py` (新建)
  - 扫描现有文档（使用file_path的文档）
  - 批量上传到对象存储
  - 更新数据库记录
  - 验证数据完整性

## 数据存储架构

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

## 新增文件清单

### 核心服务
- `backend/app/services/object_storage.py` - 对象存储服务封装
- `backend/scripts/migrate_to_object_storage.py` - 数据迁移脚本

### 修改的文件
- `backend/app/config.py` - 添加对象存储配置
- `backend/app/models/knowledge.py` - 添加对象存储字段
- `backend/app/api/v1/knowledge.py` - 重构上传API，添加下载/删除接口
- `backend/app/knowledge/rag/document_processor.py` - 支持从对象存储读取
- `backend/scripts/load_medical_knowledge.py` - 支持对象存储
- `backend/app/database/indexes.py` - 添加新字段索引
- `backend/requirements.txt` - 添加对象存储依赖
- `data/README.md` - 更新说明文档
- `.gitignore` - 确保数据文件不被提交
- `docker-compose.yml` - 添加对象存储环境变量
- `k8s/configmap.yaml` - 添加对象存储配置
- `k8s/secrets.yaml` - 添加对象存储密钥
- `k8s/backend.yaml` - 添加对象存储环境变量

## 使用说明

### 1. 配置对象存储

#### 本地开发（使用MinIO）
在 `backend/.env` 文件中配置：
```bash
OBJECT_STORAGE_TYPE=minio
OBJECT_STORAGE_ENDPOINT=localhost:9000
OBJECT_STORAGE_ACCESS_KEY=minioadmin
OBJECT_STORAGE_SECRET_KEY=minioadmin
OBJECT_STORAGE_BUCKET=medical-documents
OBJECT_STORAGE_USE_SSL=false
```

#### 生产环境（使用AWS S3）
```bash
OBJECT_STORAGE_TYPE=s3
OBJECT_STORAGE_ENDPOINT=https://s3.amazonaws.com
OBJECT_STORAGE_ACCESS_KEY=your-access-key
OBJECT_STORAGE_SECRET_KEY=your-secret-key
OBJECT_STORAGE_BUCKET=your-bucket-name
OBJECT_STORAGE_REGION=us-east-1
OBJECT_STORAGE_USE_SSL=true
```

#### 生产环境（使用阿里云OSS）
```bash
OBJECT_STORAGE_TYPE=oss
OBJECT_STORAGE_ENDPOINT=https://oss-cn-hangzhou.aliyuncs.com
OBJECT_STORAGE_ACCESS_KEY=your-access-key
OBJECT_STORAGE_SECRET_KEY=your-secret-key
OBJECT_STORAGE_BUCKET=your-bucket-name
```

### 2. 上传文档

#### 通过API上传（推荐）
```bash
curl -X POST http://localhost:8000/api/v1/knowledge/documents \
  -F "file=@document.pdf" \
  -F "source=guidelines"
```

#### 批量上传本地文档
```bash
cd backend
python scripts/load_medical_knowledge.py --upload-to-storage
```

### 3. 下载文档

#### 直接下载
```bash
curl http://localhost:8000/api/v1/knowledge/documents/1/download
```

#### 获取预签名URL
```bash
curl "http://localhost:8000/api/v1/knowledge/documents/1/download?use_presigned_url=true&expires=3600"
```

### 4. 删除文档
```bash
curl -X DELETE http://localhost:8000/api/v1/knowledge/documents/1
```

### 5. 数据迁移

如果已有本地文档需要迁移到对象存储：

```bash
cd backend
python scripts/migrate_to_object_storage.py
```

## 预期效果

- ✅ 文档存储在对象存储，支持多实例部署
- ✅ 数据持久化，容器重启不丢失
- ✅ 支持水平扩展
- ✅ 符合企业级最佳实践
- ✅ Git仓库不包含数据文件
- ✅ 支持多种对象存储后端（MinIO/S3/OSS）
- ✅ 向后兼容（支持本地文件系统）

## 注意事项

1. **生产环境必须使用对象存储**：本地文件系统不支持多实例部署
2. **MinIO访问控制**：生产环境请修改默认密码
3. **数据备份**：定期备份对象存储和数据库
4. **迁移数据**：使用迁移脚本将现有文档迁移到对象存储
5. **向后兼容**：系统仍支持读取本地文件（用于开发环境）

## 后续优化建议

1. **分片上传**：支持大文件分片上传
2. **CDN集成**：对象存储与CDN集成，加速文件访问
3. **版本控制**：文档版本管理
4. **访问控制**：基于角色的文档访问控制
5. **自动清理**：定期清理临时文件和过期文档

---

**完成状态**: ✅ 所有12个任务已完成
**代码质量**: ✅ 通过Lint检查
**文档完整性**: ✅ 完整

