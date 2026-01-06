"""LLM服务 - Qwen模型集成"""
import dashscope
from dashscope import Generation
from typing import List, Dict, Optional, AsyncGenerator
from app.config import get_settings
from app.utils.logger import app_logger
from app.infrastructure.retry import retry, get_circuit_breaker
from app.common.exceptions import LLMServiceException, ErrorCode

settings = get_settings()
dashscope.api_key = settings.QWEN_API_KEY

# LLM服务断路器
llm_circuit_breaker = get_circuit_breaker("llm_service", failure_threshold=5, recovery_timeout=60)


class LLMService:
    """LLM服务类"""
    
    def __init__(self):
        self.model = settings.QWEN_MODEL
        self.api_key = settings.QWEN_API_KEY
    
    @retry(max_attempts=3, delay=1.0, backoff=2.0, exceptions=(Exception,))
    def generate(self, prompt: str, system_prompt: str = None, 
                 temperature: float = 0.7, max_tokens: int = 2000,
                 **kwargs) -> str:
        """生成文本（带重试机制）"""
        try:
            # 使用断路器
            return llm_circuit_breaker.call(self._generate_internal, prompt, system_prompt, temperature, max_tokens, **kwargs)
        except Exception as e:
            raise LLMServiceException(
                f"LLM生成失败: {str(e)}",
                error_code=ErrorCode.LLM_SERVICE_ERROR
            )
    
    def _generate_internal(self, prompt: str, system_prompt: str = None,
                          temperature: float = 0.7, max_tokens: int = 2000,
                          **kwargs) -> str:
        """内部生成方法"""
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = Generation.call(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            if response.status_code == 200:
                return response.output.choices[0].message.content
            else:
                app_logger.error(f"LLM生成失败: {response.message}")
                raise Exception(f"LLM生成失败: {response.message}")
                
        except Exception as e:
            app_logger.error(f"LLM调用出错: {e}")
            raise
    
    def stream_generate(self, prompt: str, system_prompt: str = None,
                       temperature: float = 0.7, max_tokens: int = 2000,
                       **kwargs) -> AsyncGenerator[str, None]:
        """流式生成文本"""
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            responses = Generation.call(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs
            )
            
            for response in responses:
                if response.status_code == 200:
                    if response.output.choices:
                        content = response.output.choices[0].message.content
                        if content:
                            yield content
                else:
                    app_logger.error(f"流式生成失败: {response.message}")
                    break
                    
        except Exception as e:
            app_logger.error(f"流式生成出错: {e}")
            raise
    
    def chat(self, messages: List[Dict[str, str]], 
             temperature: float = 0.7, max_tokens: int = 2000,
             **kwargs) -> str:
        """多轮对话"""
        try:
            response = Generation.call(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            if response.status_code == 200:
                return response.output.choices[0].message.content
            else:
                app_logger.error(f"对话失败: {response.message}")
                raise Exception(f"对话失败: {response.message}")
                
        except Exception as e:
            app_logger.error(f"对话出错: {e}")
            raise


class PromptTemplate:
    """Prompt模板"""
    
    MEDICAL_CONSULTATION_SYSTEM = """你是一位专业的AI医疗助手。你的职责是：
1. 基于提供的医疗文献和知识图谱信息，为用户提供准确的医疗咨询
2. 所有回答必须标注数据来源
3. 对于不确定的信息，明确说明"暂无明确指南支持"
4. 禁止编造医疗建议
5. 对于高风险场景（如紧急病症、手术方案、药物剂量调整），必须提示用户前往医院就诊
6. 在回答结尾添加免责声明："本回答仅供参考，不替代医生诊断和治疗，具体医疗方案请遵医嘱"
"""
    
    MEDICAL_CONSULTATION_USER = """基于以下医疗信息，回答用户的问题：

{context}

用户问题：{question}

请提供专业、准确的回答，并标注信息来源。"""
    
    DIAGNOSIS_ASSISTANT_SYSTEM = """你是一位专业的诊断辅助AI。基于患者的症状描述和医疗知识，提供可能的诊断建议。
注意：这仅是辅助参考，最终诊断需要医生确认。"""
    
    DRUG_CONSULTATION_SYSTEM = """你是一位专业的用药咨询AI。基于药物信息和知识图谱，回答用药相关问题。
注意：具体用药方案需要医生根据患者情况制定。"""
    
    @staticmethod
    def format_medical_prompt(context: str, question: str) -> str:
        """格式化医疗咨询Prompt"""
        return PromptTemplate.MEDICAL_CONSULTATION_USER.format(
            context=context,
            question=question
        )
    
    @staticmethod
    def format_diagnosis_prompt(symptoms: str, context: str = "") -> str:
        """格式化诊断辅助Prompt"""
        prompt = f"患者症状描述：{symptoms}\n"
        if context:
            prompt += f"\n相关医疗信息：\n{context}\n"
        prompt += "\n请提供可能的诊断建议和相关检查建议。"
        return prompt
    
    @staticmethod
    def format_drug_prompt(question: str, drug_info: str = "", context: str = "") -> str:
        """格式化用药咨询Prompt"""
        prompt = f"用药咨询问题：{question}\n"
        if drug_info:
            prompt += f"\n药物信息：\n{drug_info}\n"
        if context:
            prompt += f"\n相关医疗信息：\n{context}\n"
        prompt += "\n请提供专业的用药建议。"
        return prompt


# 全局LLM服务实例
llm_service = LLMService()

