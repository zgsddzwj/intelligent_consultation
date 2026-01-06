"""Prompt模板库"""
from app.services.prompt_engineer import PromptTemplate, prompt_engineer

# 导入所有模板
from .medical_consultation import *
from .diagnosis_assistant import *
from .drug_consultation import *

__all__ = ["PromptTemplate", "prompt_engineer"]

