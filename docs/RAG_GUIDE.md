# 高级RAG系统指南

本指南详细介绍了智能医疗管家平台的高级RAG（检索增强生成）系统的使用方法、配置选项及技术实现细节。

## 目录

1. [快速开始](#快速开始)
2. [使用方式](#使用方式)
3. [系统架构与实现](#系统架构与实现)
4. [配置选项](#配置选项)

---

## 快速开始

### 1. 环境准备

确保已安装依赖：

```bash
cd backend
pip install -r requirements.txt
```

**注意**: 
- `PaddleOCR` 可能需要额外系统依赖（如 `libopencv`）。
- `FlagEmbedding` (BGE-Reranker) 首次运行时会自动下载模型，请保持网络通畅。

### 2. 环境变量

在 `.env` 文件中配置：

```env
QWEN_API_KEY=sk-xxxxxx
# 向量数据库与知识图谱配置...
```

### 3. 模型训练（可选）

如果需要使用机器学习重排序（ML Rerank）功能，需先训练模型：

```bash
# 1. 准备训练数据
python scripts/prepare_training_data.py

# 2. 训练模型
python scripts/train_ml_models.py
```

---

## 使用方式

### 方式1: 在 Agent 中使用（推荐）

这是最常用的方式，通过 `RAGTool` 自动处理检索和上下文格式化。

```python
from app.agents.tools.rag_tool import RAGTool

# 初始化 RAG 工具 (默认启用高级特性)
rag_tool = RAGTool(use_advanced=True)

# 执行检索
result = rag_tool.execute("高血压的症状有哪些？", top_k=5)

# 格式化为 LLM 上下文
context = rag_tool.format_context(result)
```

### 方式2: 直接调用 AdvancedRAG

适用于需要精细控制检索过程的场景。

```python
from app.knowledge.rag.advanced_rag import AdvancedRAG

# 初始化
rag = AdvancedRAG(
    enable_multi_retrieval=True,  # 启用多路召回
    enable_rerank=True,           # 启用 BGE 重排序
    enable_ml_rerank=True         # 启用 ML 排序优化
)

# 检索
result = rag.retrieve("高血压的早期表现", top_k=5)

# 解析结果
print(f"意图分类: {result.get('intent', {}).get('intent_name')}")
for doc in result['documents']:
    print(f"相关度: {doc['score']} - {doc['text'][:50]}...")
```

### 方式3: 独立使用组件

```python
# 1. 多路召回
from app.knowledge.rag.multi_retrieval import MultiRetrieval
retriever = MultiRetrieval()
candidates = retriever.retrieve("查询词", top_k=20)

# 2. 重排序
from app.knowledge.rag.reranker import Reranker
reranker = Reranker()
reranked_docs = reranker.rerank("查询词", candidates, top_k=5)

# 3. 意图识别
from app.knowledge.ml.intent_classifier import IntentClassifier
classifier = IntentClassifier()
intent = classifier.classify("我头痛该吃什么药？")
```

---

## 系统架构与实现

高级RAG系统通过多阶段处理管道提升检索准确率和相关性。

### 1. 多路召回系统 (Multi-Retrieval)

结合多种检索算法的优势，提高召回率。

- **BM25检索器** (`bm25_retriever.py`): 基于关键词匹配，使用 `rank-bm25` 和 `jieba` 分词。对精确匹配效果好。
- **语义检索器** (`semantic_retriever.py`): 基于向量相似度，利用 Qwen 进行查询扩展和重写，解决语义匹配问题。
- **知识图谱检索器** (`kg_retriever.py`): 从 Neo4j 检索实体及其关系，提供结构化知识补充。
- **融合算法** (`multi_retrieval.py`): 使用 RRF (Reciprocal Rank Fusion) 算法融合各路结果。
  - 权重配置：向量(0.4) + BM25(0.3) + 语义(0.2) + 图谱(0.1)

### 2. 文档解析增强 (Document Processing)

提升非结构化文档的解析质量。

- **PDF处理** (`document_processor.py`, `pdfplumber`): 提取文本布局。
- **多模态解析** (`image_processor.py`):
  - 使用 **PaddleOCR** 识别图片文字。
  - 使用 **Qwen-VL** 理解图片内容并生成描述。
  - 图片和文本关联存储，支持跨模态检索。

### 3. 专业重排序 (Reranking)

对召回结果进行精细排序。

- **BGE-Reranker** (`reranker.py`): 使用 `FlagEmbedding` 加载 BGE 模型，计算 Query-Document 相关性得分。
- **ML重排序器** (`ml_reranker.py`):
  - 基于 SVM 和 决策树 的轻量级排序模型。
  - 特征工程：文本特征、统计特征、语义特征。

### 4. 机器学习辅助 (ML Integration)

利用传统 ML 算法辅助决策。

- **意图分类器** (`intent_classifier.py`): 识别查询意图（诊断、用药、检查、健康管理）。
- **相关性评分器** (`relevance_scorer.py`): 二分类模型判断结果是否相关。
- **查询理解** (`query_understanding.py`): 提取实体关键词，分析查询类型。

---

## 配置选项

### 代码配置

```python
rag = AdvancedRAG(
    enable_multi_retrieval=True,
    enable_rerank=True,
    enable_ml_rerank=True,
    weights={
        "vector": 0.4,
        "bm25": 0.3,
        "semantic": 0.2,
        "kg": 0.1
    }
)
```

### 性能优化建议

1. **预加载模型**: BGE 模型和 ML 模型加载较慢，建议在服务启动时预加载。
2. **异步处理**: 对于图片解析等耗时操作，建议使用后台任务。
3. **缓存**: `MultiRetrieval` 和 `Reranker` 内部实现了简单的缓存机制，生产环境建议对接 Redis。
