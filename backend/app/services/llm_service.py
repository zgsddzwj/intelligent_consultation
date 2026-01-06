"""LLM服务 - Qwen模型集成"""
import dashscope
from dashscope import Generation
from typing import List, Dict, Optional, AsyncGenerator
import time
from app.config import get_settings
from app.utils.logger import app_logger
from app.infrastructure.retry import retry, get_circuit_breaker
from app.common.exceptions import LLMServiceException, ErrorCode
from app.services.langfuse_service import langfuse_service
from app.services.semantic_cache import semantic_cache
from app.infrastructure.monitoring import track_llm_request, track_llm_cache_hit

settings = get_settings()
dashscope.api_key = settings.QWEN_API_KEY

# LLM服务断路器
llm_circuit_breaker = get_circuit_breaker("llm_service", failure_threshold=5, recovery_timeout=60)


class LLMService:
    """LLM服务类"""
    
    def __init__(self):
        self.model = settings.QWEN_MODEL
        self.api_key = settings.QWEN_API_KEY
        self.prompt_version = settings.PROMPT_VERSION
    
    @retry(max_attempts=3, delay=1.0, backoff=2.0, exceptions=(Exception,))
    def generate(self, prompt: str, system_prompt: str = None, 
                 temperature: float = None, max_tokens: int = None,
                 trace_id: Optional[str] = None,
                 user_id: Optional[str] = None,
                 session_id: Optional[str] = None,
                 prompt_version: Optional[str] = None,
                 **kwargs) -> str:
        """生成文本（带重试机制和Langfuse追踪）"""
        temperature = temperature if temperature is not None else settings.LLM_DEFAULT_TEMPERATURE
        max_tokens = max_tokens if max_tokens is not None else settings.LLM_DEFAULT_MAX_TOKENS
        prompt_version = prompt_version or self.prompt_version
        
        # 创建或使用现有的trace
        trace = None
        if langfuse_service.enabled:
            if trace_id:
                # 使用现有trace
                pass
            else:
                # 创建新trace
                trace = langfuse_service.trace(
                    name="llm.generate",
                    user_id=user_id,
                    session_id=session_id,
                    metadata={
                        "prompt_version": prompt_version,
                        "model": self.model,
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    }
                )
                trace_id = trace.id if trace and hasattr(trace, 'id') else None
        
        start_time = time.time()
        first_token_time = None
        
        # 检查语义缓存
        cache_key = f"{system_prompt or ''}:{prompt}" if system_prompt else prompt
        cached_result = semantic_cache.get(cache_key)
        if cached_result:
            app_logger.info(f"语义缓存命中，相似度: {cached_result.get('similarity', 0):.3f}")
            track_llm_cache_hit("semantic")
            # 记录缓存命中到Langfuse
            if langfuse_service.enabled:
                langfuse_service.generation(
                    name="llm.generate",
                    model=self.model,
                    model_parameters={"cached": True},
                    input={"prompt": prompt, "system_prompt": system_prompt},
                    output=cached_result["response"],
                    trace_id=trace_id,
                    metadata={
                        "cache_hit": True,
                        "similarity": cached_result.get("similarity"),
                        "latency": time.time() - start_time
                    }
                )
            return cached_result["response"]
        
        try:
            # 使用断路器
            result = llm_circuit_breaker.call(
                self._generate_internal, 
                prompt, system_prompt, temperature, max_tokens, **kwargs
            )
            
            # 计算延迟
            latency = time.time() - start_time
            first_token_latency = first_token_time - start_time if first_token_time else latency
            
            # 估算token使用（Qwen API可能不返回详细token信息）
            estimated_input_tokens = len(prompt.split()) * 1.3  # 粗略估算
            estimated_output_tokens = len(result.split()) * 1.3
            
            # 估算成本（Qwen定价，需要根据实际调整）
            # 示例：假设输入0.008元/1K tokens，输出0.008元/1K tokens
            estimated_cost = (estimated_input_tokens / 1000 * 0.008) + (estimated_output_tokens / 1000 * 0.008)
            
            # 记录监控指标
            track_llm_request(
                model=self.model,
                status="success",
                duration=latency,
                first_token_latency=first_token_latency,
                input_tokens=int(estimated_input_tokens),
                output_tokens=int(estimated_output_tokens),
                cost=estimated_cost
            )
            
            # 记录到Langfuse
            if langfuse_service.enabled:
                langfuse_service.generation(
                    name="llm.generate",
                    model=self.model,
                    model_parameters={
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "prompt_version": prompt_version
                    },
                    input={
                        "prompt": prompt,
                        "system_prompt": system_prompt
                    },
                    output=result,
                    usage={
                        "input": int(estimated_input_tokens),
                        "output": int(estimated_output_tokens),
                        "total": int(estimated_input_tokens + estimated_output_tokens)
                    },
                    trace_id=trace_id,
                    metadata={
                        "latency": latency,
                        "first_token_latency": first_token_latency,
                        "prompt_version": prompt_version,
                        "estimated_cost": estimated_cost
                    }
                )
            
            # 存储到语义缓存
            semantic_cache.set(
                cache_key,
                result,
                metadata={
                    "model": self.model,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "prompt_version": prompt_version
                }
            )
            
            return result
            
        except Exception as e:
            # 记录错误
            if langfuse_service.enabled:
                langfuse_service.generation(
                    name="llm.generate",
                    model=self.model,
                    model_parameters={
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    },
                    input={
                        "prompt": prompt,
                        "system_prompt": system_prompt
                    },
                    output=f"Error: {str(e)}",
                    trace_id=trace_id,
                    metadata={
                        "error": True,
                        "error_message": str(e),
                        "latency": time.time() - start_time
                    }
                )
            
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
                       temperature: float = None, max_tokens: int = None,
                       trace_id: Optional[str] = None,
                       user_id: Optional[str] = None,
                       session_id: Optional[str] = None,
                       **kwargs) -> AsyncGenerator[str, None]:
        """流式生成文本（带Langfuse追踪）"""
        temperature = temperature if temperature is not None else settings.LLM_DEFAULT_TEMPERATURE
        max_tokens = max_tokens if max_tokens is not None else settings.LLM_DEFAULT_MAX_TOKENS
        
        # 创建trace
        trace = None
        if langfuse_service.enabled and not trace_id:
            trace = langfuse_service.trace(
                name="llm.stream_generate",
                user_id=user_id,
                session_id=session_id,
                metadata={
                    "model": self.model,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
            )
            trace_id = trace.id if trace and hasattr(trace, 'id') else None
        
        start_time = time.time()
        first_token_time = None
        full_output = ""
        
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
                            # 记录首token时间
                            if first_token_time is None:
                                first_token_time = time.time()
                            
                            full_output += content
                            yield content
                else:
                    app_logger.error(f"流式生成失败: {response.message}")
                    break
            
            # 记录完整的流式生成结果
            if langfuse_service.enabled:
                latency = time.time() - start_time
                first_token_latency = first_token_time - start_time if first_token_time else latency
                estimated_input_tokens = len(prompt.split()) * 1.3
                estimated_output_tokens = len(full_output.split()) * 1.3
                
                langfuse_service.generation(
                    name="llm.stream_generate",
                    model=self.model,
                    model_parameters={
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    },
                    input={
                        "prompt": prompt,
                        "system_prompt": system_prompt
                    },
                    output=full_output,
                    usage={
                        "input": int(estimated_input_tokens),
                        "output": int(estimated_output_tokens),
                        "total": int(estimated_input_tokens + estimated_output_tokens)
                    },
                    trace_id=trace_id,
                    metadata={
                        "latency": latency,
                        "first_token_latency": first_token_latency,
                        "stream": True
                    }
                )
                    
        except Exception as e:
            app_logger.error(f"流式生成出错: {e}")
            
            # 记录错误
            if langfuse_service.enabled:
                langfuse_service.generation(
                    name="llm.stream_generate",
                    model=self.model,
                    model_parameters={
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    },
                    input={
                        "prompt": prompt,
                        "system_prompt": system_prompt
                    },
                    output=f"Error: {str(e)}",
                    trace_id=trace_id,
                    metadata={
                        "error": True,
                        "error_message": str(e),
                        "latency": time.time() - start_time
                    }
                )
            
            raise
    
    def chat(self, messages: List[Dict[str, str]], 
             temperature: float = None, max_tokens: int = None,
             trace_id: Optional[str] = None,
             user_id: Optional[str] = None,
             session_id: Optional[str] = None,
             **kwargs) -> str:
        """多轮对话（带Langfuse追踪）"""
        temperature = temperature if temperature is not None else settings.LLM_DEFAULT_TEMPERATURE
        max_tokens = max_tokens if max_tokens is not None else settings.LLM_DEFAULT_MAX_TOKENS
        
        # 创建trace
        trace = None
        if langfuse_service.enabled and not trace_id:
            trace = langfuse_service.trace(
                name="llm.chat",
                user_id=user_id,
                session_id=session_id,
                metadata={
                    "model": self.model,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "message_count": len(messages)
                }
            )
            trace_id = trace.id if trace and hasattr(trace, 'id') else None
        
        start_time = time.time()
        
        try:
            response = Generation.call(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            if response.status_code == 200:
                result = response.output.choices[0].message.content
                
                # 记录到Langfuse
                if langfuse_service.enabled:
                    # 估算token使用
                    total_text = " ".join([msg.get("content", "") for msg in messages])
                    estimated_input_tokens = len(total_text.split()) * 1.3
                    estimated_output_tokens = len(result.split()) * 1.3
                    
                    langfuse_service.generation(
                        name="llm.chat",
                        model=self.model,
                        model_parameters={
                            "temperature": temperature,
                            "max_tokens": max_tokens
                        },
                        input={"messages": messages},
                        output=result,
                        usage={
                            "input": int(estimated_input_tokens),
                            "output": int(estimated_output_tokens),
                            "total": int(estimated_input_tokens + estimated_output_tokens)
                        },
                        trace_id=trace_id,
                        metadata={
                            "latency": time.time() - start_time,
                            "message_count": len(messages)
                        }
                    )
                
                return result
            else:
                app_logger.error(f"对话失败: {response.message}")
                raise Exception(f"对话失败: {response.message}")
                
        except Exception as e:
            app_logger.error(f"对话出错: {e}")
            
            # 记录错误
            if langfuse_service.enabled:
                langfuse_service.generation(
                    name="llm.chat",
                    model=self.model,
                    model_parameters={
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    },
                    input={"messages": messages},
                    output=f"Error: {str(e)}",
                    trace_id=trace_id,
                    metadata={
                        "error": True,
                        "error_message": str(e),
                        "latency": time.time() - start_time
                    }
                )
            
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

