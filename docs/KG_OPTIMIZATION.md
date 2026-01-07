# 知识图谱优化说明

## 优化内容

本次优化对知识图谱检索系统进行了三个方面的改进：

### 1. 实体识别优化（NER模型）

**文件**: `backend/app/knowledge/ml/entity_recognizer.py`

**改进内容**:
- ✅ 使用LLM进行医疗实体识别，替代简单的字符串匹配
- ✅ 支持提取疾病、症状、药物、检查、科室等实体类型
- ✅ 支持知识图谱验证，确保提取的实体在知识图谱中存在
- ✅ 提供回退策略，当LLM失败时使用关键词匹配

**优势**:
- 更准确的实体识别
- 支持复杂查询中的实体提取
- 自动验证实体有效性

**使用示例**:
```python
from app.knowledge.ml.entity_recognizer import MedicalEntityRecognizer

recognizer = MedicalEntityRecognizer()
entities = recognizer.extract_entities("我最近头痛发热，可能是感冒吗？")
# 返回: {"diseases": ["感冒"], "symptoms": ["头痛", "发热"], ...}
```

### 2. 查询策略优化

**文件**: `backend/app/knowledge/ml/query_strategy.py`

**改进内容**:
- ✅ 自动识别问题类型（疾病信息、症状诊断、药物信息等）
- ✅ 根据问题类型自动选择最优查询策略
- ✅ 支持7种问题类型和对应的查询策略
- ✅ 计算分类置信度

**问题类型**:
- `disease_info`: 疾病信息查询
- `symptom_diagnosis`: 症状诊断
- `drug_info`: 药物信息查询
- `drug_interaction`: 药物相互作用
- `examination_advice`: 检查建议
- `treatment_plan`: 治疗方案
- `general_consultation`: 一般咨询

**查询策略**:
- `disease_centric`: 以疾病为中心的查询
- `symptom_centric`: 以症状为中心的查询
- `drug_centric`: 以药物为中心的查询
- `drug_interaction`: 药物相互作用查询
- `examination_centric`: 以检查为中心的查询
- `multi_entity`: 多实体关联查询
- `general`: 通用查询

**使用示例**:
```python
from app.knowledge.ml.query_strategy import QueryStrategySelector

selector = QueryStrategySelector()
analysis = selector.classify_question("高血压有什么症状？", entities)
# 返回: {"question_type": "disease_info", "strategy": "disease_centric", ...}
```

### 3. 结果排序优化

**文件**: `backend/app/knowledge/ml/relevance_scorer.py`

**改进内容**:
- ✅ 多维度相关性评分
- ✅ 基于实体匹配度、查询相似度、关系强度、结果完整性评分
- ✅ 自动排序，返回最相关的结果
- ✅ 支持按问题类型调整权重

**评分维度**:
1. **实体匹配度** (40%): 结果中包含的实体与查询实体的匹配程度
2. **查询相似度** (30%): 结果文本与查询的语义相似度
3. **关系强度** (20%): 知识图谱中关系的丰富程度
4. **结果完整性** (10%): 结果信息的完整程度

**使用示例**:
```python
from app.knowledge.ml.relevance_scorer import RelevanceScorer

scorer = RelevanceScorer()
scored_results = scorer.score_and_sort(results, query, entities, question_type)
# 返回按相关性排序的结果列表
```

## 集成到知识图谱检索器

**文件**: `backend/app/knowledge/rag/kg_retriever.py`

**改进内容**:
- ✅ 集成NER实体识别器
- ✅ 集成查询策略选择器
- ✅ 集成相关性评分器
- ✅ 优化查询流程，按策略执行查询
- ✅ 自动去重和排序

**新的检索流程**:
1. 使用NER模型提取实体
2. 分析问题类型并选择查询策略
3. 根据策略执行查询
4. 对结果进行相关性评分和排序
5. 返回top_k个最相关的结果

## 性能优化

1. **缓存机制**: 实体识别结果缓存，避免重复调用LLM
2. **查询限制**: 根据策略限制查询深度和结果数量
3. **并行查询**: 支持多实体并行查询（未来可扩展）

## 使用效果

### 优化前
- 实体识别：简单字符串匹配，准确率低
- 查询策略：固定策略，无法适应不同问题类型
- 结果排序：无排序，按查询顺序返回

### 优化后
- 实体识别：LLM识别，准确率显著提升
- 查询策略：自动选择最优策略，查询更精准
- 结果排序：多维度评分，最相关结果优先

## 配置说明

所有优化功能已自动集成到 `KnowledgeGraphRetriever` 中，无需额外配置。

如需调整权重或策略，可以修改：
- `relevance_scorer.py` 中的 `weights` 字典
- `query_strategy.py` 中的 `STRATEGY_MAP` 和策略配置

## 测试建议

1. 测试不同问题类型的识别准确率
2. 测试实体识别的准确性和召回率
3. 测试结果排序的相关性
4. 测试查询性能（响应时间）

## 未来优化方向

1. 使用专门的医疗NER模型（如BERT-based模型）
2. 支持更复杂的多跳查询
3. 添加查询结果的可解释性
4. 支持用户反馈学习，持续优化排序

