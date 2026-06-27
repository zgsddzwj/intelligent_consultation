# 问题排查与性能优化记录

> 本文档记录项目开发过程中遇到的典型问题、根因分析与解决方案，供后续维护参考。

---

## 目录

- [一、问诊无响应（请求超时 >60s）](#一问诊无响应请求超时-60s)
- [二、KG 检索慢导致请求 >10s](#二kg-检索慢导致请求-10s)
- [三、优化效果对比](#三优化效果对比)
- [四、修改文件清单](#四修改文件清单)

---

## 一、问诊无响应（请求超时 >60s）

### 现象

用户发送消息后，后端超过 60 秒无响应，前端显示超时。

### 根因分析

| # | 瓶颈 | 耗时 | 原因 |
|---|------|------|------|
| 1 | **模型重复加载** | 8×10s = 80s | `BGEReranker` 每次实例化都重新加载 1.5GB 模型，单次请求中被加载 8+ 次 |
| 2 | **语义缓存维度不匹配** | 报错降级 | `embed` 被误用为 `embed_query`，导致向量维度不匹配，缓存无法命中 |
| 3 | **无效 API 重试** | 7s | Embedding API Key 无效时仍重试 3 次，每次等待 ~2s |
| 4 | **ServiceFactory 非线程安全** | 竞争初始化 | 并发请求导致 `AgentOrchestrator` 被重复创建 |
| 5 | **语义缓存强依赖 Milvus** | 阻塞主流程 | Milvus 不可用时语义缓存直接报错，而非降级 |

### 解决方案

#### 1. Reranker 单例化 — `backend/app/knowledge/rag/reranker.py`

```python
class BGEReranker:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, model_name="BAAI/bge-reranker-base"):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                # 初始化逻辑（仅执行一次）
            return cls._instance
```

**效果**：模型仅加载一次，后续调用直接复用，省去 8×10s = 80s 重复加载。

#### 2. 修复语义缓存 — `backend/app/services/semantic_cache.py`

- 将 `embed` 改为 `embed_query`，修复维度不匹配
- 添加 `flatten()` 检查，确保向量为一维
- 增加 `use_milvus` 降级开关，Milvus 不可用时回退到 Redis

#### 3. Embedder API 预检 — `backend/app/knowledge/rag/embedder.py`

```python
if not self._api_available:
    app_logger.warning("Embedding API 不可用，跳过向量化")
    return []
```

API Key 无效时直接标记 `_api_available = False`，跳过后续重试。

#### 4. ServiceFactory 线程安全 — `backend/app/dependencies.py`

```python
class ServiceFactory:
    _lock = threading.Lock()

    @classmethod
    def get_orchestrator(cls):
        with cls._lock:
            # Double-Checked Locking
            if cls._orchestrator is None:
                cls._orchestrator = AgentOrchestrator()
        return cls._orchestrator
```

#### 5. Milvus 可选化降级

将 Milvus 标记为可选服务，连接失败时不阻塞主流程，通过 LLM 通用知识兜底。

---

## 二、KG 检索慢导致请求 >10s

### 现象

问诊接口恢复后，单次请求耗时 28-50 秒。用户希望控制在 10 秒内，并增加 thinking 过程提示。

### 根因分析

| # | 瓶颈 | 耗时 | 原因 |
|---|------|------|------|
| 1 | **KG 重复查询** | ~15-18s | `doctor_agent` 并行调了 `execute_kg()` 和 `execute_rag()`，而 RAG 内部 `MultiRetrieval` 又调了一次 KG |
| 2 | **LLM-based NER** | ~5-8s/次 | `MedicalEntityRecognizer.extract_entities()` 每次调 DeepSeek 做实体识别，被调 2 次 |
| 3 | **N+1 Neo4j 查询** | ~3-5s | `extract_with_kg_validation()` 对每个实体做单独验证查询；`retrieve_by_entity()` 对每个疾病做 4 次查询 |
| 4 | **串行多路检索** | ~6s | `MultiRetrieval` 串行执行向量/BM25/KG 检索，不可用服务各阻塞 3s |
| 5 | **Neo4j 重试退避** | ~3s | 连接失败后重试 3 次，每次 sleep 0.5s+ |
| 6 | **流式接口重复 LLM** | ~15s | 先调 `orchestrator.process()`（内含 LLM 生成），再单独做 `stream_generate()` |

### 解决方案

#### 1. 去除重复 KG 查询 — `backend/app/agents/doctor_agent.py`

**修改前**：`ThreadPoolExecutor` 并行执行 `execute_rag()` + `execute_kg()`，KG 被查询 2 次。

**修改后**：仅执行一次 RAG 检索，从 RAG 结果中提取 KG 上下文：

```python
rag_result = self.rag_tool.execute(question, top_k=5)
if rag_result.get("results"):
    rag_context = self.rag_tool.format_context(rag_result)
    # 从 RAG 结果中提取 KG 结果（MultiRetrieval 已包含 KG 检索）
    kg_from_rag = [
        r for r in rag_result.get("results", [])
        if r.get("retrieval_method") == "knowledge_graph"
    ]
```

#### 2. Regex NER 替代 LLM NER — `backend/app/knowledge/rag/kg_retriever.py`

```python
def extract_entities(self, query, use_kg_validation=False):
    # 默认使用 regex 快速提取（即时完成，不调 LLM）
    entities = self.entity_recognizer._fallback_extraction(query)
```

**效果**：省去 LLM 调用 5-8s，regex 匹配 <1ms。

#### 3. 批量化 Neo4j 查询 — `backend/app/knowledge/rag/kg_retriever.py`

**修改前**：对每个疾病执行 4 次查询（疾病信息 + 症状 + 药物 + 检查）。

**修改后**：单次 Cypher 查询获取全部关联信息：

```cypher
MATCH (d:Disease {name: $name})
OPTIONAL MATCH (d)-[:HAS_SYMPTOM]->(s:Symptom)
OPTIONAL MATCH (d)-[:TREATED_BY]->(dr:Drug)
OPTIONAL MATCH (d)-[:REQUIRES_EXAM]->(e:Examination)
RETURN d.name as disease,
       collect(DISTINCT s.name) as symptoms,
       collect(DISTINCT dr.name) as drugs,
       collect(DISTINCT e.name) as exams
```

**效果**：4 次查询 → 1 次查询。

#### 4. 多路检索并行化 — `backend/app/knowledge/rag/multi_retrieval.py`

```python
with ThreadPoolExecutor(max_workers=3) as executor:
    futures = {
        executor.submit(_do_vector): "vector",
        executor.submit(_do_bm25): "bm25",
        executor.submit(_do_kg): "kg",
    }
```

**效果**：串行 ~6s → 并行 ~3s（取最慢一路的耗时）。

#### 5. 失败缓存机制 — `backend/app/knowledge/graph/neo4j_client.py` + `backend/app/services/milvus_service.py`

```python
# Neo4j / Milvus 连接失败后，30 秒内不再重试
if self._last_fail_time and (time.time() - self._last_fail_time < self._fail_cache_ttl):
    raise ConnectionError("连接不可用（失败缓存中）")
```

同时将 Neo4j 连接超时从 10s 降至 3s，重试次数从 3 次降至 1 次。

**效果**：首次连接失败 ~3s → 后续请求 <1ms（缓存命中直接跳过）。

#### 6. 流式接口重构 — `backend/app/api/v1/consultation.py`

**修改前**：流式接口先调 `orchestrator.process()`（内含一次完整 LLM 生成），再调 `stream_generate()`，等于做了 2 次 LLM 调用。

**修改后**：
- 直接使用 `RAGTool` 检索（不经 orchestrator）
- 发送 `thinking` 事件，前端实时展示处理进度
- RAG 检索超时 30s → 6s

```python
# thinking 事件
yield f"data: {json.dumps({'type': 'thinking', 'content': '正在检索医学知识库...'})}\n\n"

# RAG 检索（6s 超时）
result = await asyncio.wait_for(
    asyncio.to_thread(rag_tool.execute, sanitized_message, 5),
    timeout=6.0
)
```

#### 7. 前端流式改造 — `frontend/src/pages/PatientPortal.tsx`

- 从非流式 `POST /chat` 切换为流式 `POST /chat/stream`
- 使用 `fetch + ReadableStream` 解析 SSE（支持 POST body 和 thinking 事件）
- 实时展示 thinking 进度（加载动画 + 状态文字）

```typescript
await consultationApi.chatStream(buildChatRequest(msg), {
  onThinking: (content) => setThinkingText(content),
  onFirstToken: () => setThinkingText(''),
  onMessage: (chunk) => setStreamingContent(prev => prev + chunk),
  // ...
})
```

---

## 三、优化效果对比

### 流式接口（首 token 时间）

| 场景 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 首次请求（冷启动） | 49s+ | ~5s | **10x** |
| 二次请求（缓存生效） | 49s+ | ~1.7s | **29x** |
| 完整回答输出 | 49s+ | ~8s | **6x** |

### 非流式接口

| 场景 | 优化前 | 优化后 |
|------|--------|--------|
| 完整回答 | 49s+ | ~28s（含 LLM 生成 2456 字符） |

### 用户体验

用户发送消息后看到的处理流程：

```
🤔 正在分析您的问题...          (即时)
📚 正在检索医学知识库...        (即时)
✍️ 基于医学知识生成回答...      (~2s)
💬 首 token 开始流式输出        (~2s)
✅ 完整回答 + 免责声明           (~8s)
```

---

## 四、修改文件清单

### 第一轮：问诊无响应修复

| 文件 | 修改内容 |
|------|----------|
| `backend/app/knowledge/rag/reranker.py` | `BGEReranker` 单例化，避免模型重复加载 |
| `backend/app/dependencies.py` | `ServiceFactory` 增加 `threading.Lock`，防止并发重复创建 |
| `backend/app/services/semantic_cache.py` | 修复 `embed` → `embed_query` 维度不匹配；增加 Milvus 降级 |
| `backend/app/knowledge/rag/embedder.py` | 增加 `_api_available` 预检，跳过无效 API |

### 第二轮：KG 慢优化 + 流式 thinking

| 文件 | 修改内容 |
|------|----------|
| `backend/app/agents/doctor_agent.py` | 去除重复 KG 查询，从 RAG 结果中提取 KG 上下文 |
| `backend/app/knowledge/rag/kg_retriever.py` | 默认 regex NER；批量 Cypher 查询；查询结果缓存；无实体跳过 |
| `backend/app/knowledge/rag/multi_retrieval.py` | 向量/BM25/KG 三路检索并行执行 |
| `backend/app/knowledge/graph/neo4j_client.py` | 连接超时 10s→3s；重试 3→1 次；30s 失败缓存 |
| `backend/app/services/milvus_service.py` | 重试 2→1 次；30s 失败缓存 |
| `backend/app/api/v1/consultation.py` | 流式接口重构：thinking 事件 + 直接 RAGTool + 6s 超时 |
| `frontend/src/services/consultation.ts` | fetch + ReadableStream 实现 SSE POST |
| `frontend/src/pages/PatientPortal.tsx` | 切换流式调用；thinking 进度展示 |
| `frontend/src/types/chat.ts` | `ChatStreamEvent` 增加 `thinking` 事件类型 |

---

## 关键经验总结

1. **可选服务必须降级**：Milvus、Neo4j 等非核心服务不可用时，应快速失败并降级，而非阻塞主流程。
2. **避免重复计算**：同一请求中，KG 被 RAG 和 Agent 各调一次是常见陷阱，需统一检索入口。
3. **LLM 调用是最贵的操作**：能用 regex/规则解决的任务（如 NER），不要用 LLM。
4. **失败缓存比重试更有效**：连接失败后短时间内不可能恢复，30 秒失败缓存比 3 次重试更高效。
5. **流式优于非流式**：用户感知的"首 token 时间"远比"完整响应时间"重要，流式输出能极大改善体验。
6. **N+1 查询是性能杀手**：将多个单条 Cypher 查询合并为一条 `OPTIONAL MATCH + collect` 批量查询。
7. **并行优于串行**：多个独立的检索操作应并行执行，总耗时取决于最慢的一路而非各路之和。
