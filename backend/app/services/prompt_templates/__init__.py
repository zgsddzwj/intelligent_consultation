"""Prompt模板库 - v2.0

包含工程化优化的Prompt模板：
- medical_consultation: 医疗咨询（结构化角色/JSON输出/Few-shot/CoT）
- diagnosis_assistant: 诊断辅助（风险分级/鉴别诊断/检查建议）
- drug_consultation: 用药咨询（安全分级/相互作用/特殊人群）

版本管理：
- v2.0: 当前默认版本（工程化优化）
- v1.0: 遗留版本（向后兼容）
"""
from app.services.prompt_engineer import PromptTemplate, prompt_engineer

# 导入所有模板（会自动注册）
from .medical_consultation import medical_consultation_template_v2
from .diagnosis_assistant import diagnosis_template_v2
from .drug_consultation import drug_consultation_template_v2

# 遗留版本（向后兼容）
from .medical_consultation_legacy import medical_consultation_template_v1
from .diagnosis_assistant_legacy import diagnosis_template_v1
from .drug_consultation_legacy import drug_consultation_template_v1

__all__ = [
    "PromptTemplate",
    "prompt_engineer",
    # v2.0 模板
    "medical_consultation_template_v2",
    "diagnosis_template_v2",
    "drug_consultation_template_v2",
    # v1.0 遗留模板
    "medical_consultation_template_v1",
    "diagnosis_template_v1",
    "drug_consultation_template_v1",
]
