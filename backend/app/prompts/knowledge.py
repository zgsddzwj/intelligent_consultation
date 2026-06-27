"""知识工程类 Prompt - 实体识别 / 幻觉检测 / RAG 上下文生成

用于知识图谱构建、检索增强生成中的辅助 Prompt。
"""


class KnowledgePrompts:
    """知识工程类 Prompt 集合"""

    # ================================================================
    # 医疗实体识别（NER）
    # ================================================================

    NER_SYSTEM = "你是一个专业的医疗实体识别助手，擅长从医疗相关文本中准确提取实体。"

    NER_USER = """请从以下医疗咨询问题中提取所有医疗相关实体，并按类型分类。

问题：{query}

请以JSON格式返回，格式如下：
{{
    "diseases": ["疾病名称1", "疾病名称2"],
    "symptoms": ["症状名称1", "症状名称2"],
    "drugs": ["药物名称1", "药物名称2"],
    "examinations": ["检查项目1", "检查项目2"],
    "departments": ["科室名称1", "科室名称2"]
}}

要求：
1. 只提取明确提到的实体，不要推测
2. 实体名称要完整准确
3. 如果某个类型没有实体，返回空数组
4. 只返回JSON，不要其他文字

JSON:"""

    # ================================================================
    # 幻觉检测 / 事实一致性验证
    # ================================================================

    HALLUCINATION_VERIFICATION = """请验证以下陈述是否与提供的上下文信息一致。

上下文信息：
{context}

需要验证的陈述：
{claim}

请回答：
1. 该陈述是否与上下文一致？（是/否/不确定）
2. 如果不一致，请指出不一致的地方
3. 该陈述是否有明确的来源支持？（是/否）

请以JSON格式回答：
{{
    "consistent": true/false/null,
    "has_source": true/false,
    "inconsistency": "不一致的地方（如果存在）",
    "confidence": 0.0-1.0
}}"""

    # ================================================================
    # RAG 答案生成
    # ================================================================

    RAG_ANSWER_GENERATION = """基于检索到的信息：

{context}

用户问题：{query}

请提供专业、准确的回答，并标注信息来源。"""

    # ================================================================
    # 图片医疗术语提取（用于知识图谱构建）
    # ================================================================

    IMAGE_MEDICAL_TERMS_EXTRACTION = """请识别图片中的医疗相关术语，包括疾病名称、症状、药物名称、检查项目等，并以列表形式返回。"""

    IMAGE_TERMS_CLASSIFY = """请从以下文本中提取医疗相关术语，并按类型分类：

{analysis_text}

请以JSON格式返回，格式如下：
{{
    "terms": [
        {{"term": "术语名称", "type": "疾病|症状|药物|检查|科室"}},
        ...
    ]
}}

注意：
- 只返回JSON，不要添加其他说明文字
- type字段只能是：疾病、症状、药物、检查、科室 之一
- 如果没有识别到医疗术语，返回空数组"""

    # ================================================================
    # 格式化方法
    # ================================================================

    @staticmethod
    def format_ner_prompt(query: str) -> str:
        """格式化 NER 用户 Prompt"""
        return KnowledgePrompts.NER_USER.format(query=query)

    @staticmethod
    def format_verification_prompt(context: str, claim: str) -> str:
        """格式化幻觉验证 Prompt"""
        return KnowledgePrompts.HALLUCINATION_VERIFICATION.format(
            context=context, claim=claim
        )

    @staticmethod
    def format_rag_answer_prompt(context: str, query: str) -> str:
        """格式化 RAG 答案生成 Prompt"""
        return KnowledgePrompts.RAG_ANSWER_GENERATION.format(
            context=context, query=query
        )

    @staticmethod
    def format_image_terms_classify_prompt(analysis_text: str) -> str:
        """格式化图片术语分类 Prompt"""
        return KnowledgePrompts.IMAGE_TERMS_CLASSIFY.format(
            analysis_text=analysis_text
        )
