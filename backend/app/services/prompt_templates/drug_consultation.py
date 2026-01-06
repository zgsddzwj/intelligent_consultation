"""用药咨询Prompt模板"""
from app.services.prompt_engineer import PromptTemplate, prompt_engineer

DRUG_CONSULTATION_SYSTEM_V1 = """你是一位专业的用药咨询AI。基于药物信息和知识图谱，回答用药相关问题。

重要原则：
1. 具体用药方案需要医生根据患者情况制定
2. 提供药物的一般信息、适应症、禁忌症、注意事项
3. 不提供具体的剂量建议（除非是通用指南）
4. 强调个体化用药的重要性
5. 提醒药物相互作用和副作用"""

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
    metadata={"category": "medication", "risk_level": "high"}
)

prompt_engineer.register_template(drug_consultation_template_v1)

