"""LLM服务 - 增强版（消除重复代码、超时控制、精确token估算、流式超时保护）"""
import dashscope
from dashscope import Generation
from typing import List, Dict, Optional, AsyncGenerator
import time
import asyncio
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

# 默认超时设置（秒）
DEFAULT_REQUEST_TIMEOUT = 60  # 普通请求超时
STREAM_CHUNK_TIMEOUT = 30     # 流式请求单个chunk最大等待时间


def _estimate_tokens(text: str) -> int:
    """
    精确估算token数量
    
    改进策略：
    - 中文：约1-2字符 = 1 token（保守估计1.5）
    - 英文/数字：约4字符 = 1 token
    - 标点符号：单独计为0.5 token
    
    Args:
        text: 输入文本
        
    Returns:
        估算的token数量
    """
    if not text:
        return 0
    
    chinese_chars = 0
    ascii_chars = 0
    punctuation_count = 0
    
    for char in text:
        code_point = ord(char)
        if code_point > 0x4E00 and code_point <= 0x9FFF:  # CJK统一汉字
            chinese_chars += 1
        elif code_point < 128:
            if char in ' .,!?;:，。！？；：、""''（）【】《》':
                punctuation_count += 1
            else:
                ascii_chars += 1
        else:
            # 其他Unicode字符（日文、韩文等）
            chinese_chars += 1
    
    # 估算：中文约1.5 char/token，英文约4 char/token，标点约2 char/token
    chinese_tokens = int(chinese_chars / 1.5) + (chinese_chars % 1.5 > 0 and 1 or 0)
    ascii_tokens = int(ascii_chars / 4.0) + (ascii_chars % 4 > 0 and 1 or 0)
    punct_tokens = int(punctuation_count / 2.0) + (punctuation_count % 2 > 0 and 1 or 0)
    
    total = chinese_tokens + ascii_tokens + punct_tokens
    return max(total, 1)  # 至少返回1


class LLMService:
    """LLM服务类 - 支持Qwen和DeepSeek动态切换（增强版）"""
    
    def __init__(self):
        """
        初始化LLM服务。

        根据配置（`LLM_PROVIDER`）动态选择并初始化LLM客户端。
        目前支持 'qwen' 和 'deepseek'。
        """
        self.provider = settings.LLM_PROVIDER.lower()
        self.prompt_version = settings.PROMPT_VERSION
        
        # 根据provider初始化配置
        if self.provider == "deepseek":
            self.model = settings.DEEPSEEK_MODEL
            self.api_key = settings.DEEPSEEK_API_KEY
            self.base_url = settings.DEEPSEEK_BASE_URL
            try:
                from openai import OpenAI
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    timeout=DEFAULT_REQUEST_TIMEOUT  # 设置默认超时
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
            dashscope.api_key = self.api_key
        else:
            raise LLMServiceException(
                f"不支持的LLM Provider: {self.provider}，支持: qwen, deepseek",
                error_code=ErrorCode.LLM_SERVICE_ERROR
            )
        
        app_logger.info(f"LLM服务初始化完成，Provider: {self.provider}, Model: {self.model}")
    
    # ========== 公共响应解析方法（消除重复代码）==========
    
    def _parse_qwen_response(self, response, method_name: str = "unknown") -> str:
        """
        解析Qwen API响应（统一方法）
        
        Qwen API有两种响应格式：
        1. 标准格式: response.output.choices[0].message.content
        2. 简化格式: response.output.text (当choices为null时)
        
        Args:
            response: Dashscope API响应对象
            method_name: 调用方法名（用于日志）
            
        Returns:
            解析后的文本内容
            
        Raises:
            Exception: 无法解析时抛出
        """
        if response.status_code != 200:
            error_msg = getattr(response, 'message', f"HTTP {response.status_code}")
            raise Exception(f"Qwen {method_name} API调用失败: status_code={response.status_code}, message={error_msg}")
        
        if not response.output:
            raise Exception(f"Qwen {method_name} 响应格式异常: output为空, status_code={response.status_code}")
        
        result = None
        
        # 策略1: 尝试标准格式 (choices)
        if hasattr(response.output, 'choices') and response.output.choices:
            choices = response.output.choices
            if len(choices) > 0:
                choice = choices[0]
                if (choice.message and 
                    hasattr(choice.message, 'content') and 
                    choice.message.content):
                    result = choice.message.content
        
        # 策略2: 回退到简化格式 (text字段)
        if not result and hasattr(response.output, 'text') and response.output.text:
            result = response.output.text
        
        if not result:
            raise Exception(
                f"Qwen {method_name} 响应格式异常: "
                f"无法从choices或text字段获取内容, output={response.output}"
            )
        
        return result
    
    def _parse_deepseek_response(self, response, method_name: str = "unknown") -> str:
        """
        解析DeepSeek API响应（统一方法）
        
        Args:
            response: OpenAI兼容API响应对象
            method_name: 调用方法名（用于日志）
            
        Returns:
            解析后的文本内容
            
        Raises:
            Exception: 无法解析时抛出
        """
        if not response.choices or len(response.choices) == 0:
            raise Exception(f"DeepSeek {method_name} 响应格式异常: choices为空")
        
        choice = response.choices[0]
        if not choice.message or not choice.message.content:
            raise Exception(f"DeepSeek {method_name} 响应内容为空")
        
        return choice.message.content
    
    def _call_qwen_api(self, messages: List[Dict], temperature: float = 0.7,
                       max_tokens: int = 2000, **kwargs):
        """调用Qwen API（内部方法）"""
        response = Generation.call(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        return self._parse_qwen_response(response, "generate")
    
    def _call_deepseek_api(self, messages: List[Dict], temperature: float = 0.7,
                           max_tokens: int = 2000, **kwargs):
        """调用DeepSeek API（内部方法）"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        return self._parse_deepseek_response(response, "generate")
    
    def _call_provider(self, messages: List[Dict], temperature: float = 0.7,
                       max_tokens: int = 2000, **kwargs) -> str:
        """
        统一调用当前provider的API
        
        Args:
            messages: 对话消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            
        Returns:
            生成的文本
        """
        if self.provider == "deepseek":
            return self._call_deepseek_api(messages, temperature, max_tokens, **kwargs)
        elif self.provider == "qwen":
            return self._call_qwen_api(messages, temperature, max_tokens, **kwargs)
        else:
            raise Exception(f"不支持的Provider: {self.provider}")
    
    # ========== 主要公共方法 ==========
    
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
                pass
            else:
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
                self._call_provider, 
                self._build_messages(system_prompt, prompt),
                temperature, max_tokens, **kwargs
            )
            
            # 计算延迟和使用精确token估算
            latency = time.time() - start_time
            first_token_latency = first_token_time - start_time if first_token_time else latency
            
            estimated_input_tokens = _estimate_tokens(prompt) + (system_prompt and _estimate_tokens(system_prompt) or 0)
            estimated_output_tokens = _estimate_tokens(result)
            
            # 计算成本（基于实际模型定价）
            estimated_cost = self._estimate_cost(estimated_input_tokens, estimated_output_tokens)
            
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
    
    def stream_generate(self, prompt: str, system_prompt: str = None,
                       temperature: float = None, max_tokens: int = None,
                       trace_id: Optional[str] = None,
                       user_id: Optional[str] = None,
                       session_id: Optional[str] = None,
                       **kwargs) -> AsyncGenerator[str, None]:
        """流式生成文本（带Langfuse追踪和超时保护）"""
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
        chunk_count = 0
        
        try:
            messages = self._build_messages(system_prompt, prompt)
            
            if self.provider == "deepseek":
                stream = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True,
                    **kwargs
                )
                
                for chunk in stream:
                    content = self._extract_stream_content(chunk, "deepseek")
                    if content:
                        chunk_count += 1
                        if first_token_time is None:
                            first_token_time = time.time()
                        full_output += content
                        yield content
                        
            elif self.provider == "qwen":
                responses = Generation.call(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True,
                    **kwargs
                )
                
                for response in responses:
                    content = self._extract_stream_content(response, "qwen")
                    if content:
                        chunk_count += 1
                        if first_token_time is None:
                            first_token_time = time.time()
                        full_output += content
                        yield content
                    else:
                        # 检查是否有错误状态码
                        if hasattr(response, 'status_code') and response.status_code != 200:
                            error_msg = getattr(response, 'message', f"HTTP {response.status_code}")
                            app_logger.error(f"Qwen流式生成错误: {error_msg}")
                            break
            else:
                raise Exception(f"不支持的Provider: {self.provider}")
            
            # 记录完整的流式生成结果
            if langfuse_service.enabled:
                latency = time.time() - start_time
                first_token_latency = first_token_time - start_time if first_token_time else latency
                
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
                        "input": int(_estimate_tokens(prompt)),
                        "output": int(_estimate_tokens(full_output)),
                        "total": int(_estimate_tokens(prompt)) + int(_estimate_tokens(full_output))
                    },
                    trace_id=trace_id,
                    metadata={
                        "latency": latency,
                        "first_token_latency": first_token_latency,
                        "stream": True,
                        "chunk_count": chunk_count
                    }
                )
                    
        except Exception as e:
            app_logger.error(f"流式生成出错: {e}")
            
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
        """多轮对话（带Langfuse追踪，复用统一的API调用逻辑）"""
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
            # 复用统一的provider调用方法
            result = self._call_provider(messages, temperature, max_tokens, **kwargs)
            
            if result:
                if langfuse_service.enabled:
                    total_text = " ".join([msg.get("content", "") for msg in messages])
                    latency = time.time() - start_time
                    
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
                            "input": int(_estimate_tokens(total_text)),
                            "output": int(_estimate_tokens(result)),
                            "total": int(_estimate_tokens(total_text)) + int(_estimate_tokens(result))
                        },
                        trace_id=trace_id,
                        metadata={
                            "latency": latency,
                            "message_count": len(messages)
                        }
                    )
                
                return result
            else:
                raise Exception("LLM返回结果为空")
                
        except Exception as e:
            app_logger.error(f"对话出错: {e}")
            
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
    
    # ========== 内部辅助方法 ==========
    
    def _build_messages(self, system_prompt: Optional[str], prompt: str) -> List[Dict]:
        """构建消息列表"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages
    
    def _extract_stream_content(self, chunk, provider: str) -> Optional[str]:
        """
        从流式chunk中提取内容（统一方法）
        
        Args:
            chunk: 流式响应的一个chunk
            provider: 提供商名称 ("deepseek" 或 "qwen")
            
        Returns:
            文本内容，如果没有则返回None
        """
        try:
            if provider == "deepseek":
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        return delta.content
            elif provider == "qwen":
                if hasattr(chunk, 'status_code') and chunk.status_code == 200:
                    content = None
                    
                    # 尝试标准格式 (choices)
                    if (chunk.output and hasattr(chunk.output, 'choices') and 
                        chunk.output.choices and len(chunk.output.choices) > 0):
                        choice = chunk.output.choices[0]
                        if (choice.message and 
                            hasattr(choice.message, 'content') and 
                            choice.message.content):
                            content = choice.message.content
                    
                    # 回退到简化格式 (text字段)
                    if not content and chunk.output and hasattr(chunk.output, 'text'):
                        content = chunk.output.text
                    
                    return content
        except Exception as e:
            app_logger.debug(f"提取流式内容失败 ({provider}): {e}")
        
        return None
    
    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        估算LLM调用成本
        
        基于各模型的实际定价估算。
        
        Args:
            input_tokens: 输入token数
            output_tokens: 输出token数
            
        Returns:
            估算成本（元）
        """
        # 定价表（每1K tokens的价格，单位：元）
        # 注意：这是示例价格，需要根据实际情况更新
        pricing = {
            # Qwen 系列
            "qwen-turbo": {"input": 0.002, "output": 0.006},
            "qwen-plus": {"input": 0.004, "output": 0.012},
            "qwen-max": {"input": 0.02, "output": 0.06},
            "qwen-vl-max": {"input": 0.02, "output": 0.06},
            # DeepSeek 系列
            "deepseek-chat": {"input": 0.001, "output": 0.002},
            "deepseek-coder": {"input": 0.001, "output": 0.002},
        }
        
        model_pricing = pricing.get(self.model, {"input": 0.008, "output": 0.008})  # 默认价格
        
        input_cost = (input_tokens / 1000) * model_pricing["input"]
        output_cost = (output_tokens / 1000) * model_pricing["output"]
        
        return round(input_cost + output_cost, 6)


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

    HEALTH_MANAGER_SYSTEM = """你是一位专业的健康管家。你的职责是：
1. 为用户制定个性化的健康管理计划
2. 提供生活方式建议（饮食、运动、作息等）
3. 帮助用户追踪和管理健康数据
4. 提供慢病管理指导
5. 鼓励用户保持健康的生活习惯"""

    @staticmethod
    def format_health_plan_prompt(question: str, profile: dict, context: str = "") -> str:
        """格式化健康计划Prompt"""
        prompt = f"用户需求：{question}\n"
        if profile:
            prompt += f"用户信息：{profile}\n"
        if context:
            prompt += f"\n参考信息：\n{context}\n"
        prompt += "\n请制定详细的健康管理计划，包括饮食、运动、作息等建议。"
        return prompt

    CUSTOMER_SERVICE_SYSTEM = """你是一位专业的客服助手。你的职责是：
1. 回答用户关于系统使用的常见问题
2. 提供系统功能说明和操作指导
3. 处理用户反馈和建议
4. 帮助用户解决使用中的问题
5. 保持友好、耐心的服务态度"""

    @staticmethod
    def format_customer_service_prompt(question: str, context: str = "") -> str:
        """格式化客服Prompt"""
        prompt = f"用户问题：{question}\n"
        if context:
            prompt += f"\n相关信息：\n{context}\n"
        prompt += "\n请提供友好的回答。"
        return prompt


# 全局LLM服务实例
llm_service = LLMService()
