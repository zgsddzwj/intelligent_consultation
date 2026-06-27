"""诊断辅助Prompt模板 - v1.0 遗留版本（向后兼容）

系统 Prompt 引用 app.prompts.ConsultationPrompts 公共库。
"""
from app.services.prompt_engineer import PromptTemplate, prompt_engineer
from app.prompts import ConsultationPrompts

DIAGNOSIS_ASSISTANT_SYSTEM_V1 = ConsultationPrompts.DIAGNOSIS_ASSISTANT_SYSTEM

DIAGNOSIS_ASSISTANT_USER_V1 = """患者症状描述：{symptoms}

{context}

请提供：
1. 可能的诊断方向（按可能性排序）
2. 建议的检查项目
3. 是否需要立即就医
4. 注意事项

请明确说明这仅是辅助参考，最终诊断需要医生确认。"""

diagnosis_template_v1 = PromptTemplate(
    name="diagnosis_assistant",
    version="v1.0",
    system_prompt=DIAGNOSIS_ASSISTANT_SYSTEM_V1,
    user_prompt_template=DIAGNOSIS_ASSISTANT_USER_V1,
    output_format="结构化回答：可能诊断、检查建议、就医建议、注意事项",
    metadata={"category": "diagnosis", "risk_level": "high", "legacy": True}
)

prompt_engineer.register_template(diagnosis_template_v1)
