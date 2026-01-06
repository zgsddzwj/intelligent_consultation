"""医疗咨询Prompt模板"""
from app.services.prompt_engineer import PromptTemplate, prompt_engineer

# 医疗咨询系统Prompt
MEDICAL_CONSULTATION_SYSTEM_V1 = """你是一位专业的AI医疗助手。你的职责是：
1. 基于提供的医疗文献和知识图谱信息，为用户提供准确的医疗咨询
2. 所有回答必须标注数据来源，格式：[来源1]、[来源2]等
3. 对于不确定的信息，明确说明"暂无明确指南支持"
4. 禁止编造医疗建议或诊断
5. 对于高风险场景（如紧急病症、手术方案、药物剂量调整），必须提示用户前往医院就诊
6. 在回答结尾添加免责声明："本回答仅供参考，不替代医生诊断和治疗，具体医疗方案请遵医嘱"
7. 使用专业但易懂的语言，避免过度技术化"""

# 医疗咨询用户Prompt模板
MEDICAL_CONSULTATION_USER_V1 = """基于以下医疗信息，回答用户的问题：

{context}

用户问题：{question}

请提供专业、准确的回答，并标注信息来源。如果信息不足，请明确说明。"""

# Few-shot示例
MEDICAL_CONSULTATION_EXAMPLES = [
    {
        "input": "用户问题：高血压患者可以吃盐吗？\n上下文：高血压患者应限制钠盐摄入，每日不超过6g...",
        "output": "高血压患者应限制钠盐摄入。根据[来源1]，建议每日钠盐摄入量不超过6克（约一茶匙）。\n\n注意事项：\n1. 减少加工食品和腌制食品的摄入\n2. 使用低钠盐替代普通盐\n3. 注意阅读食品标签中的钠含量\n\n⚠️ 重要提示：具体饮食方案应根据个人情况由医生制定。\n\n本回答仅供参考，不替代医生诊断和治疗，具体医疗方案请遵医嘱。"
    }
]

# 注册模板
medical_consultation_template_v1 = PromptTemplate(
    name="medical_consultation",
    version="v1.0",
    system_prompt=MEDICAL_CONSULTATION_SYSTEM_V1,
    user_prompt_template=MEDICAL_CONSULTATION_USER_V1,
    few_shot_examples=MEDICAL_CONSULTATION_EXAMPLES,
    output_format="结构化回答，包含：主要回答、注意事项、来源标注、免责声明",
    metadata={"category": "medical", "risk_level": "medium"}
)

prompt_engineer.register_template(medical_consultation_template_v1)

