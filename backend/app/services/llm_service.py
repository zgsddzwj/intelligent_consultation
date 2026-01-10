"""LLM服务 - 支持Qwen和DeepSeek动态切换"""
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

# 初始化Qwen API Key（如果使用Qwen）
if settings.LLM_PROVIDER == "qwen":
    dashscope.api_key = settings.QWEN_API_KEY

# LLM服务断路器
llm_circuit_breaker = get_circuit_breaker("llm_service", failure_threshold=5, recovery_timeout=60)


class LLMService:
    """LLM服务类 - 支持Qwen和DeepSeek动态切换"""
    
    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower()
        self.prompt_version = settings.PROMPT_VERSION
        
        # 根据provider初始化配置
        if self.provider == "deepseek":
            self.model = settings.DEEPSEEK_MODEL
            self.api_key = settings.DEEPSEEK_API_KEY
            self.base_url = settings.DEEPSEEK_BASE_URL
            # 初始化OpenAI客户端（DeepSeek兼容OpenAI API）
            try:
                from openai import OpenAI
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
            except ImportError:
                app_logger.error("OpenAI库未安装，无法使用DeepSeek。请运行: pip install openai")
                raise LLMServiceException(
                    "OpenAI库未安装，无法使用DeepSeek",
                    error_code=ErrorCode.LLM_SERVICE_ERROR
                )
        elif self.provider == "qwen":
            self.model = settings.QWEN_MODEL
            self.api_key = settings.QWEN_API_KEY
            self.client = None
            # 确保dashscope已配置
            dashscope.api_key = self.api_key
        else:
            raise LLMServiceException(
                f"不支持的LLM Provider: {self.provider}，支持: qwen, deepseek",
                error_code=ErrorCode.LLM_SERVICE_ERROR
            )
        
        app_logger.info(f"LLM服务初始化完成，Provider: {self.provider}, Model: {self.model}")
    
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
            
            if self.provider == "deepseek":
                # 使用OpenAI兼容API调用DeepSeek
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                # 添加空值检查
                if not response.choices or len(response.choices) == 0:
                    error_msg = f"DeepSeek响应格式异常: choices为空, response={response}"
                    app_logger.error(error_msg)
                    raise Exception(error_msg)
                if not response.choices[0].message or not response.choices[0].message.content:
                    error_msg = "DeepSeek响应内容为空"
                    app_logger.error(error_msg)
                    raise Exception(error_msg)
                return response.choices[0].message.content
            elif self.provider == "qwen":
                # 使用Dashscope调用Qwen
                response = Generation.call(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                if response.status_code == 200:
                    # Qwen API有两种响应格式：
                    # 1. 标准格式: response.output.choices[0].message.content
                    # 2. 简化格式: response.output.text (当choices为null时)
                    if not response.output:
                        error_msg = f"Qwen响应格式异常: output为空, status_code={response.status_code}"
                        app_logger.error(error_msg)
                        raise Exception(error_msg)
                    
                    # 优先尝试标准格式 (choices)
                    if hasattr(response.output, 'choices') and response.output.choices:
                        if len(response.output.choices) > 0:
                            if (response.output.choices[0].message and 
                                hasattr(response.output.choices[0].message, 'content') and 
                                response.output.choices[0].message.content):
                                return response.output.choices[0].message.content
                    
                    # 回退到简化格式 (text字段)
                    if hasattr(response.output, 'text') and response.output.text:
                        return response.output.text
                    
                    # 如果两种格式都不可用，抛出错误
                    error_msg = f"Qwen响应格式异常: 无法从choices或text字段获取内容, output={response.output}"
                    app_logger.error(error_msg)
                    raise Exception(error_msg)
                else:
                    error_msg = f"Qwen API调用失败: status_code={response.status_code}, message={getattr(response, 'message', '未知错误')}"
                    app_logger.error(error_msg)
                    raise Exception(error_msg)
            else:
                raise Exception(f"不支持的Provider: {self.provider}")
                
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
            
            if self.provider == "deepseek":
                # 使用OpenAI兼容API流式调用DeepSeek
                stream = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True,
                    **kwargs
                )
                for chunk in stream:
                    # 添加更严格的空值检查
                    if chunk.choices and len(chunk.choices) > 0:
                        if chunk.choices[0].delta and chunk.choices[0].delta.content:
                            content = chunk.choices[0].delta.content
                            # 记录首token时间
                            if first_token_time is None:
                                first_token_time = time.time()
                            full_output += content
                            yield content
            elif self.provider == "qwen":
                # 使用Dashscope流式调用Qwen
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
                        content = None
                        # 优先尝试标准格式 (choices)
                        if (response.output and hasattr(response.output, 'choices') and 
                            response.output.choices and len(response.output.choices) > 0):
                            if (response.output.choices[0].message and 
                                hasattr(response.output.choices[0].message, 'content') and 
                                response.output.choices[0].message.content):
                                content = response.output.choices[0].message.content
                        
                        # 回退到简化格式 (text字段)
                        if not content and response.output and hasattr(response.output, 'text'):
                            content = response.output.text
                        
                        # 如果获取到内容，yield它
                        if content:
                            # 记录首token时间
                            if first_token_time is None:
                                first_token_time = time.time()
                            full_output += content
                            yield content
                    else:
                        error_msg = f"Qwen流式生成失败: status_code={response.status_code}, message={getattr(response, 'message', '未知错误')}"
                        app_logger.error(error_msg)
                        break
            else:
                raise Exception(f"不支持的Provider: {self.provider}")
            
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
            if self.provider == "deepseek":
                # 使用OpenAI兼容API调用DeepSeek
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                # 添加空值检查
                if not response.choices or len(response.choices) == 0:
                    error_msg = f"DeepSeek对话响应格式异常: choices为空, response={response}"
                    app_logger.error(error_msg)
                    raise Exception(error_msg)
                if not response.choices[0].message or not response.choices[0].message.content:
                    error_msg = "DeepSeek对话响应内容为空"
                    app_logger.error(error_msg)
                    raise Exception(error_msg)
                result = response.choices[0].message.content
            elif self.provider == "qwen":
                # 使用Dashscope调用Qwen
                response = Generation.call(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                if response.status_code == 200:
                    # Qwen API有两种响应格式：
                    # 1. 标准格式: response.output.choices[0].message.content
                    # 2. 简化格式: response.output.text (当choices为null时)
                    if not response.output:
                        error_msg = f"Qwen对话响应格式异常: output为空, status_code={response.status_code}"
                        app_logger.error(error_msg)
                        raise Exception(error_msg)
                    
                    result = None
                    # 优先尝试标准格式 (choices)
                    if hasattr(response.output, 'choices') and response.output.choices:
                        if len(response.output.choices) > 0:
                            if (response.output.choices[0].message and 
                                hasattr(response.output.choices[0].message, 'content') and 
                                response.output.choices[0].message.content):
                                result = response.output.choices[0].message.content
                    
                    # 如果标准格式不可用，尝试简化格式 (text字段)
                    if not result and hasattr(response.output, 'text') and response.output.text:
                        result = response.output.text
                    
                    # 如果两种格式都不可用，抛出错误
                    if not result:
                        error_msg = f"Qwen对话响应格式异常: 无法从choices或text字段获取内容, output={response.output}"
                        app_logger.error(error_msg)
                        raise Exception(error_msg)
                else:
                    error_msg = f"Qwen对话API调用失败: status_code={response.status_code}, message={getattr(response, 'message', '未知错误')}"
                    app_logger.error(error_msg)
                    raise Exception(error_msg)
            else:
                raise Exception(f"不支持的Provider: {self.provider}")
            
            if result:
                
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
                raise Exception("LLM返回结果为空")
                
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

