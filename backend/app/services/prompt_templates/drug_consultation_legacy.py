"""用药咨询Prompt模板 - v1.0 遗留版本（向后兼容）

系统 Prompt 引用 app.prompts.ConsultationPrompts 公共库。
"""
from app.services.prompt_engineer import PromptTemplate, prompt_engineer
from app.prompts import ConsultationPrompts

DRUG_CONSULTATION_SYSTEM_V1 = ConsultationPrompts.DRUG_CONSULTATION_SYSTEM

DRUG_CONSULTATION_USER_V1 = """用药咨询问题：{question}

药物信息：
{drug_info}

相关医疗信息：
{context}

请提供专业的用药建议，包括适应症、禁忌症、注意事项等。"""

drug_consultation_template_v1 = PromptTemplate(
    name="drug_consultation",
    version="v1.0",
    system_prompt=DRUG_CONSULTATION_SYSTEM_V1,
    user_prompt_template=DRUG_CONSULTATION_USER_V1,
    output_format="结构化回答：药物信息、适应症、禁忌症、注意事项、用药建议",
    metadata={"category": "medication", "risk_level": "high", "legacy": True}
)

prompt_engineer.register_template(drug_consultation_template_v1)
