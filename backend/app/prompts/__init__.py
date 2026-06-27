"""Prompt 公共管理库

将散落在后端各模块（agents / api / services / knowledge）中的 Prompt 统一抽离至此，
便于集中管理、版本迭代与质量优化。

目录结构：
    consultation  - 医疗咨询、诊断辅助、用药咨询
    agents        - 客服、健康管家、运营 Agent
    safety        - 安全守卫、紧急处理、免责声明
    knowledge     - 实体识别、幻觉检测、RAG
    image         - 图片分类、多模态诊断、描述生成
    operations    - 数据分析、系统监控、报告生成

使用方式：
    from app.prompts import ConsultationPrompts, AgentPrompts, SafetyPrompts
    system_prompt = ConsultationPrompts.MEDICAL_CONSULTATION_SYSTEM
    user_prompt = ConsultationPrompts.format_medical_prompt(context, question)
"""
from app.prompts.consultation import ConsultationPrompts
from app.prompts.agents import AgentPrompts
from app.prompts.safety import SafetyPrompts, MedicalDisclaimers
from app.prompts.knowledge import KnowledgePrompts
from app.prompts.image import ImagePrompts
from app.prompts.operations import OperationsPrompts

__all__ = [
    "ConsultationPrompts",
    "AgentPrompts",
    "SafetyPrompts",
    "MedicalDisclaimers",
    "KnowledgePrompts",
    "ImagePrompts",
    "OperationsPrompts",
]
