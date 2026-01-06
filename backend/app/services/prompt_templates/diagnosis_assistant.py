"""诊断辅助Prompt模板"""
from app.services.prompt_engineer import PromptTemplate, prompt_engineer

DIAGNOSIS_ASSISTANT_SYSTEM_V1 = """你是一位专业的诊断辅助AI。基于患者的症状描述和医疗知识，提供可能的诊断建议。

重要原则：
1. 这仅是辅助参考，最终诊断需要医生确认
2. 基于症状提供可能的疾病方向，不要给出确定诊断
3. 建议相关检查项目
4. 对于紧急症状，必须提示立即就医
5. 明确说明这不是最终诊断"""

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
    metadata={"category": "diagnosis", "risk_level": "high"}
)

prompt_engineer.register_template(diagnosis_template_v1)

