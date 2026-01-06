# 高级RAG系统使用指南

## 快速开始

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

**注意**: 
- PaddleOCR可能需要额外安装依赖（如opencv-python）
- FlagEmbedding需要下载模型，首次使用会较慢

### 2. 配置环境变量

确保`.env`文件中已配置：
- `QWEN_API_KEY`: Qwen API密钥
- 其他数据库连接配置

### 3. 训练ML模型（可选）

```bash
# 准备训练数据
python scripts/prepare_training_data.py

# 训练模型
python scripts/train_ml_models.py
```

**注意**: 当前使用示例数据，实际应用需要准备真实训练数据。

## 使用方式

### 方式1: 直接使用高级RAG

```python
from app.knowledge.rag.advanced_rag import AdvancedRAG

# 初始化
rag = AdvancedRAG(
    enable_multi_retrieval=True,
    enable_rerank=True,
    enable_ml_rerank=True
)

# 检索
result = rag.retrieve("高血压的症状有哪些？", top_k=5)

# 获取结果
print(f"意图: {result['intent']['intent_name']}")
print(f"文档数: {len(result['documents'])}")
for doc in result['documents']:
    print(f"- {doc['text'][:100]}...")
```

### 方式2: 在Agent中使用（推荐）

```python
from app.agents.tools.rag_tool import RAGTool

# 使用高级RAG（默认启用）
rag_tool = RAGTool(use_advanced=True)

# 检索
result = rag_tool.execute("查询文本", top_k=5)

# 格式化上下文
context = rag_tool.format_context(result)
```

### 方式3: 单独使用组件

```python
# 多路召回
from app.knowledge.rag.multi_retrieval import MultiRetrieval
multi_retrieval = MultiRetrieval()
results = multi_retrieval.retrieve("查询", top_k=10)

# Rerank
from app.knowledge.rag.reranker import Reranker
reranker = Reranker()
reranked = reranker.rerank("查询", results, top_k=5)

# 意图分类
from app.knowledge.ml.intent_classifier import IntentClassifier
classifier = IntentClassifier()
intent = classifier.classify("我最近头痛，可能是什么病？")
```

## 配置选项

### 在代码中配置

```python
from app.knowledge.rag.advanced_rag import AdvancedRAG

rag = AdvancedRAG(
    enable_multi_retrieval=True,      # 启用多路召回
    enable_rerank=True,                # 启用BGE-Reranker
    enable_ml_rerank=True,             # 启用ML重排序
    enable_intent_classification=True, # 启用意图分类
    enable_relevance_scoring=True,     # 启用相关性评分
    enable_query_understanding=True,   # 启用查询理解
    enable_ranking_optimization=True   # 启用排序优化
)
```

### 在配置文件中配置

编辑`backend/app/config.py`或`.env`文件：

```python
ENABLE_ADVANCED_RAG=True
ENABLE_MULTI_RETRIEVAL=True
VECTOR_RETRIEVAL_WEIGHT=0.4
BM25_RETRIEVAL_WEIGHT=0.3
SEMANTIC_RETRIEVAL_WEIGHT=0.2
KG_RETRIEVAL_WEIGHT=0.1
```

## PDF图片处理

### 处理包含图片的PDF

```python
from app.knowledge.rag.document_processor import DocumentProcessor

processor = DocumentProcessor(enable_image_processing=True)

# 处理PDF（会自动提取图片并OCR）
chunks = processor.process_document(
    "path/to/document.pdf",
    source="medical_guideline",
    extract_images=True
)
```

### 单独处理图片

```python
from app.knowledge.rag.image_processor import ImageProcessor

processor = ImageProcessor()

# OCR识别
ocr_result = processor.ocr_image("path/to/image.jpg")

# 多模态理解
llm_result = processor.understand_image_with_llm(
    "path/to/image.jpg",
    "请描述图片中的医疗相关内容"
)

# 完整处理
result = processor.process_image("path/to/image.jpg")
```

## 性能优化建议

### 1. 选择性启用功能

根据实际需求选择性启用功能，避免不必要的计算：

```python
# 只启用多路召回和Rerank
rag = AdvancedRAG(
    enable_multi_retrieval=True,
    enable_rerank=True,
    enable_ml_rerank=False,  # 禁用ML重排序以提升速度
    enable_ranking_optimization=False
)
```

### 2. 调整召回权重

根据数据特点调整召回权重：

```python
from app.knowledge.rag.multi_retrieval import MultiRetrieval

# 如果向量检索效果好，增加权重
multi_retrieval = MultiRetrieval(
    vector_weight=0.5,
    bm25_weight=0.3,
    semantic_weight=0.15,
    kg_weight=0.05
)
```

### 3. 批量处理

对于大量查询，考虑批量处理：

```python
queries = ["查询1", "查询2", "查询3"]
results = []

for query in queries:
    result = rag.retrieve(query, top_k=5)
    results.append(result)
```

## 故障排除

### 1. PaddleOCR初始化失败

```bash
# 安装依赖
pip install opencv-python
pip install paddlepaddle
```

### 2. BGE-Reranker模型下载慢

首次使用会自动下载模型，可以：
- 使用国内镜像
- 手动下载模型到本地

### 3. ML模型未找到

运行训练脚本生成模型：
```bash
python scripts/train_ml_models.py
```

### 4. 性能问题

- 检查是否启用了所有功能，可以禁用部分功能
- 检查Milvus和Neo4j连接是否正常
- 考虑添加缓存机制

## 示例代码

### 完整示例

```python
from app.knowledge.rag.advanced_rag import AdvancedRAG

# 初始化
rag = AdvancedRAG()

# 检索
query = "高血压患者应该注意什么？"
result = rag.retrieve(query, top_k=5)

# 查看结果
print(f"查询: {query}")
print(f"意图: {result['intent']['intent_name']}")
print(f"置信度: {result['intent']['confidence']:.2f}")
print(f"\n找到 {len(result['documents'])} 条相关文档:\n")

for i, doc in enumerate(result['documents'], 1):
    print(f"{i}. [来源: {doc['source']}]")
    print(f"   相关性: {doc.get('final_score', 0):.2f}")
    print(f"   内容: {doc['text'][:100]}...")
    print()
```

## 下一步

1. 准备真实训练数据，重新训练ML模型
2. 根据实际效果调整权重和参数
3. 添加性能监控和日志分析
4. 实现A/B测试，对比不同配置的效果

