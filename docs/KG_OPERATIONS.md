# 知识图谱操作指南

## 概述

本文档介绍如何操作和管理项目中的医疗知识图谱（基于Neo4j）。包括数据导入、查询、验证等操作。

## 目录

- [数据来源](#数据来源)
- [环境准备](#环境准备)
- [数据导入](#数据导入)
- [数据验证](#数据验证)
- [数据查询](#数据查询)
- [常见问题](#常见问题)
- [维护操作](#维护操作)

---

## 数据来源

### 数据源

医疗知识图谱数据来自GitHub项目：
- **项目**: [QASystemOnMedicalKG](https://github.com/liuhuanyong/QASystemOnMedicalKG)
- **数据文件**: `medical.json`
- **数据格式**: JSONL (JSON Lines)
- **数据大小**: 约47MB

### 数据内容

包含以下类型的医疗实体和关系：

**实体类型**:
- **Disease** (疾病): 8,807个
- **Symptom** (症状): 5,998个
- **Examination** (检查): 3,353个
- **Drug** (药物): 数量待统计
- **Department** (科室): 54个

**关系类型**:
- `HAS_SYMPTOM`: 疾病 → 症状
- `TREATED_BY`: 疾病 → 药物
- `REQUIRES_EXAM`: 疾病 → 检查
- `BELONGS_TO`: 症状 → 科室
- `ACCOMPANIES`: 症状 → 症状（伴随关系）

**总计**:
- 节点数: 18,212个
- 关系数: 110,909条

---

## 环境准备

### 1. 启动Neo4j服务

使用Docker Compose启动Neo4j：

```bash
# 启动Neo4j服务
docker-compose up -d neo4j

# 检查服务状态
docker-compose ps neo4j
```

### 2. 配置信息

Neo4j连接信息在 `.env` 文件中配置：

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=medical123
```

**注意**: Neo4j要求密码不能是默认的 `neo4j`，必须设置自定义密码。

### 3. 访问Neo4j浏览器

启动后可通过浏览器访问Neo4j管理界面：

```
http://localhost:7474
```

- 用户名: `neo4j`
- 密码: `medical123` (或你在.env中配置的密码)

---

## 数据导入

### 导入脚本

使用 `backend/scripts/import_medical_kg_realtime.py` 脚本导入数据。

### 导入步骤

1. **激活conda环境**:
```bash
source /opt/anaconda3/etc/profile.d/conda.sh
conda activate intelligent_consultation
```

2. **运行导入脚本**:
```bash
cd backend
python scripts/import_medical_kg_realtime.py
```

### 导入过程

脚本会自动执行以下步骤：

1. **下载数据**: 从GitHub下载 `medical.json` 文件
   - 使用流式下载，显示进度条
   - 文件保存到 `backend/data/medical.json`

2. **解析数据**: 
   - 支持JSON和JSONL格式
   - 提取实体和关系

3. **导入到Neo4j**:
   - 使用 `MERGE` 语句避免重复创建
   - 显示实时进度（每500个实体/每5000条关系）
   - 显示当前Neo4j统计信息

4. **完成提示**:
   - 显示最终统计信息
   - 提供Neo4j浏览器链接

### 导入时间

- 实体导入: 约1-2分钟
- 关系导入: 约2-3分钟
- 总计: 约3-5分钟（取决于网络和硬件）

### 重复导入

**安全**: 脚本使用 `MERGE` 语句，可以安全地重复运行，不会创建重复数据。

- 实体: 基于 `name` 属性去重
- 关系: 基于起点、终点、关系类型去重

---

## 数据验证

### 检查导入状态

使用 `backend/scripts/check_import_status.py` 脚本检查数据：

```bash
python scripts/check_import_status.py
```

输出示例：
```
📊 Neo4j知识图谱统计
========================================
总节点数: 18,212
总关系数: 110,909

节点类型分布:
- Disease: 8,807
- Symptom: 5,998
- Examination: 3,353
- Department: 54
- Drug: 0 (待统计)

关系类型分布:
- HAS_SYMPTOM: 45,234
- TREATED_BY: 32,156
- REQUIRES_EXAM: 28,456
- BELONGS_TO: 4,063
- ACCOMPANIES: 1,000
========================================
```

### 在Neo4j浏览器中验证

1. **打开Neo4j浏览器**: http://localhost:7474

2. **查询节点数量**:
```cypher
MATCH (n) RETURN count(n) as total_nodes
```

3. **查询关系数量**:
```cypher
MATCH ()-[r]->() RETURN count(r) as total_relationships
```

4. **查看节点类型分布**:
```cypher
MATCH (n)
RETURN labels(n)[0] as node_type, count(n) as count
ORDER BY count DESC
```

5. **查看关系类型分布**:
```cypher
MATCH ()-[r]->()
RETURN type(r) as relationship_type, count(r) as count
ORDER BY count DESC
```

6. **查看示例数据**:
```cypher
// 查看一个疾病及其关系
MATCH (d:Disease {name: "高血压"})-[r]-(related)
RETURN d, r, related
LIMIT 50
```

---

## 数据查询

### 常用Cypher查询

#### 1. 查询疾病信息

```cypher
// 查询疾病及其症状、药物、检查
MATCH (d:Disease {name: "高血压"})
OPTIONAL MATCH (d)-[:HAS_SYMPTOM]->(s:Symptom)
OPTIONAL MATCH (d)-[:TREATED_BY]->(dr:Drug)
OPTIONAL MATCH (d)-[:REQUIRES_EXAM]->(e:Examination)
RETURN d.name as disease,
       collect(DISTINCT s.name) as symptoms,
       collect(DISTINCT dr.name) as drugs,
       collect(DISTINCT e.name) as examinations
```

#### 2. 根据症状查找疾病

```cypher
// 根据症状查找可能的疾病
MATCH (d:Disease)-[:HAS_SYMPTOM]->(s:Symptom)
WHERE s.name IN ["头痛", "发热", "咳嗽"]
WITH d, count(s) as symptom_count
WHERE symptom_count >= 2
RETURN d.name as disease, symptom_count
ORDER BY symptom_count DESC
LIMIT 10
```

#### 3. 查询药物信息

```cypher
// 查询药物及其适用疾病
MATCH (d:Disease)-[:TREATED_BY]->(dr:Drug {name: "阿司匹林"})
RETURN dr.name as drug, collect(d.name) as diseases
```

#### 4. 查询检查项目

```cypher
// 查询检查项目及其相关疾病
MATCH (d:Disease)-[:REQUIRES_EXAM]->(e:Examination {name: "血常规"})
RETURN e.name as examination, collect(d.name) as diseases
```

#### 5. 知识图谱可视化

```cypher
// 查看疾病的知识图谱（2度关系）
MATCH path = (d:Disease {name: "高血压"})-[*1..2]-(related)
RETURN path
LIMIT 50
```

### 在代码中使用

项目中的知识图谱检索器已经封装了常用查询：

```python
from app.knowledge.rag.kg_retriever import KnowledgeGraphRetriever

retriever = KnowledgeGraphRetriever()
results = retriever.retrieve("高血压有什么症状？", top_k=5)
```

---

## 常见问题

### 1. Neo4j连接失败

**错误**: `Connection refused` 或 `ServiceUnavailable`

**解决方案**:
```bash
# 检查Neo4j是否运行
docker-compose ps neo4j

# 启动Neo4j
docker-compose up -d neo4j

# 检查日志
docker-compose logs neo4j
```

### 2. 密码错误

**错误**: `Invalid value for password. It cannot be 'neo4j'`

**解决方案**:
- 在 `.env` 文件中设置非默认密码
- 更新 `docker-compose.yml` 中的 `NEO4J_AUTH` 环境变量
- 重启Neo4j容器

### 3. 数据导入失败

**错误**: `The result is out of scope`

**解决方案**:
- 已修复：使用 `session.execute_write` 并在事务内处理结果
- 确保使用最新版本的导入脚本

### 4. 重复数据

**问题**: 重复运行导入脚本导致重复数据

**解决方案**:
- 脚本已使用 `MERGE` 语句，不会创建重复数据
- 如需清理重复数据，运行以下Cypher查询：

```cypher
// 清理重复关系（保留一条）
MATCH (a)-[r1]->(b), (a)-[r2]->(b)
WHERE id(r1) < id(r2) AND type(r1) = type(r2)
DELETE r2
```

### 5. 导入速度慢

**优化建议**:
- 使用批量导入（脚本已优化）
- 调整Neo4j内存配置
- 关闭不必要的索引（导入时）

---

## 维护操作

### 备份数据

```bash
# 使用Neo4j的导出功能
docker exec -it <neo4j_container_id> neo4j-admin dump --database=neo4j --to=/backups/neo4j.dump
```

### 恢复数据

```bash
# 停止Neo4j
docker-compose stop neo4j

# 恢复数据
docker exec -it <neo4j_container_id> neo4j-admin load --database=neo4j --from=/backups/neo4j.dump --force

# 启动Neo4j
docker-compose start neo4j
```

### 清理数据

**警告**: 以下操作会删除所有数据，请谨慎使用！

```cypher
// 删除所有节点和关系
MATCH (n)
DETACH DELETE n
```

### 更新数据

1. **增量更新**: 使用 `MERGE` 语句更新特定实体
2. **全量更新**: 删除旧数据后重新导入

### 性能优化

1. **创建索引**:
```cypher
// 为实体名称创建索引（已自动创建）
CREATE INDEX disease_name_index IF NOT EXISTS FOR (d:Disease) ON (d.name)
CREATE INDEX symptom_name_index IF NOT EXISTS FOR (s:Symptom) ON (s.name)
CREATE INDEX drug_name_index IF NOT EXISTS FOR (dr:Drug) ON (dr.name)
```

2. **查询优化**:
- 使用 `LIMIT` 限制结果数量
- 使用 `WHERE` 条件过滤
- 避免深度过大的路径查询（`[*1..5]`）

---

## 相关文件

- **导入脚本**: `backend/scripts/import_medical_kg_realtime.py`
- **状态检查**: `backend/scripts/check_import_status.py`
- **检索器**: `backend/app/knowledge/rag/kg_retriever.py`
- **查询模板**: `backend/app/knowledge/graph/queries.py`
- **Neo4j客户端**: `backend/app/knowledge/graph/neo4j_client.py`
- **配置**: `.env`, `docker-compose.yml`

---

## 参考资源

- [Neo4j官方文档](https://neo4j.com/docs/)
- [Cypher查询语言](https://neo4j.com/docs/cypher-manual/)
- [数据源项目](https://github.com/liuhuanyong/QASystemOnMedicalKG)

---

## 更新日志

- **2026-01-07**: 
  - 初始数据导入（18,212节点，110,909关系）
  - 实现MERGE去重机制
  - 优化导入进度显示
  - 修复Neo4j事务处理问题

