# 知识图谱操作与优化指南

本指南详细介绍智能医疗管家平台的知识图谱（基于 Neo4j）的操作管理、查询策略及优化方案。

## 目录

1. [快速开始](#快速开始)
2. [数据管理](#数据管理)
3. [查询与检索](#查询与检索)
4. [优化策略](#优化策略)

---

## 快速开始

### 1. 环境准备

确保 Docker 服务已安装，并启动 Neo4j 容器：

```bash
# 启动 Neo4j
docker-compose up -d neo4j

# 检查状态
docker-compose ps neo4j
```

Neo4j 管理界面：`http://localhost:7474`
- 默认用户: `neo4j`
- 默认密码: `medical123` (或见 `.env` 配置)

### 2. 数据初始化

首次使用必须导入医疗知识数据：

```bash
# 运行实时导入脚本 (推荐)
python backend/scripts/import_medical_kg_realtime.py
```

### 3. 数据验证

在 Neo4j Browser 中执行 Cypher 查询验证数据：

```cypher
// 统计节点数量
MATCH (n) RETURN count(n);

// 查看疾病与症状关系
MATCH (d:Disease)-[r:HAS_SYMPTOM]->(s:Symptom) RETURN d,r,s LIMIT 10;
```

---

## 数据管理

### 数据来源

项目使用开源医疗知识图谱数据 (QASystemOnMedicalKG)，包含：
- **实体**: 疾病 (Disease), 症状 (Symptom), 检查 (Examination), 药物 (Drug), 科室 (Department)
- **关系**: `HAS_SYMPTOM`, `TREATED_BY`, `REQUIRES_EXAM`, `BELONGS_TO`, `ACCOMPANIES`

### 数据导入流程

1. **下载数据**: 脚本会自动从源或本地 `medical.json` 读取。
2. **清洗数据**: 去除重复项，规范化实体名称。
3. **批量插入**: 使用 Neo4j Python Driver 批量创建节点和关系。

---

## 查询与检索

### 基础查询

使用 `KnowledgeGraphRetriever` 进行检索：

```python
from app.knowledge.rag.kg_retriever import KnowledgeGraphRetriever

retriever = KnowledgeGraphRetriever()
results = retriever.retrieve("高血压")
```

### 智能查询策略

系统内置 `QueryStrategySelector`，根据问题类型自动选择最优查询策略：

| 问题类型 | 策略 | 说明 |
|---------|------|------|
| `disease_info` | `disease_centric` | 查询疾病的定义、病因、并发症 |
| `symptom_diagnosis` | `symptom_centric` | 根据症状反查可能的疾病 |
| `drug_info` | `drug_centric` | 查询药物适应症、用法 |
| `treatment_plan` | `multi_entity` | 综合查询疾病治疗方案 |

---

## 优化策略

为了提升图谱检索的准确率和相关性，系统实施了以下优化：

### 1. 实体识别优化 (NER)

- **模块**: `backend/app/knowledge/ml/entity_recognizer.py`
- **机制**:
  - 优先使用 LLM 进行上下文敏感的实体提取。
  - 支持多类型实体（疾病、症状、药物等）同时识别。
  - 自动校验提取的实体是否存在于图谱中。
  - **Fallback**: LLM 失败时降级为关键词匹配。

### 2. 相关性评分 (Relevance Scoring)

- **模块**: `backend/app/knowledge/ml/relevance_scorer.py`
- **评分维度**:
  1. **实体匹配度 (40%)**: 结果实体与查询实体的重合度。
  2. **查询相似度 (30%)**: 文本语义相似度。
  3. **关系强度 (20%)**: 图谱路径的丰富程度。
  4. **完整性 (10%)**: 属性字段的覆盖率。

### 3. 查询意图理解

- **模块**: `backend/app/knowledge/ml/query_strategy.py`
- **机制**: 自动分类用户问题意图（如“询问症状” vs “询问治疗”），从而只查询图谱的特定子图，减少噪声。

### 4. 常见问题与排查

- **Neo4j 连接失败**: 检查 `NEO4J_URI` 配置及 Docker 容器状态。
- **检索结果为空**:
  - 确认 `init_knowledge_graph.py` 是否执行成功。
  - 检查实体识别是否准确（可开启 DEBUG 日志）。
- **查询慢**: 检查 Neo4j 索引是否创建 (`CREATE INDEX FOR (n:Disease) ON (n.name)`).
