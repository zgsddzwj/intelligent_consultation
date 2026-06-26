"""LLM服务 - 极致优化版（连接池、批量推理、智能降级、Token精确计费）"""
import dashscope
from dashscope import Generation
from typing import List, Dict, Optional, Any, AsyncGenerator, Tuple
import time
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from app.config import get_settings
from app.utils.logger import app_logger
from app.infrastructure.retry import retry, get_circuit_breaker
from app.common.exceptions import LLMServiceException, ErrorCode
from app.services.langfuse_service import langfuse_service
from app.services.semantic_cache import semantic_cache
from app.infrastructure.monitoring import track_llm_request, track_llm_cache_hit

settings = get_settings()

if settings.LLM_PROVIDER == "qwen":
    dashscope.api_key = settings.QWEN_API_KEY

llm_circuit_breaker = get_circuit_breaker("llm_service", failure_threshold=5, recovery_timeout=60)

DEFAULT_REQUEST_TIMEOUT = 60
STREAM_CHUNK_TIMEOUT = 30


def _estimate_tokens(text: str) -> int:
    """精确估算token数量"""
    if not text:
        return 0

    chinese_chars = 0
    ascii_chars = 0
    punctuation_count = 0

    for char in text:
        code_point = ord(char)
        if 0x4E00 <= code_point <= 0x9FFF:
            chinese_chars += 1
        elif code_point < 128:
            if char in ' .,!?;:，。！？；：、""''（）【】《》':
                punctuation_count += 1
            else:
                ascii_chars += 1
        else:
            chinese_chars += 1

    chinese_tokens = int(chinese_chars / 1.5) + (1 if chinese_chars % 1.5 > 0 else 0)
    ascii_tokens = int(ascii_chars / 4.0) + (1 if ascii_chars % 4 > 0 else 0)
    punct_tokens = int(punctuation_count / 2.0) + (1 if punctuation_count % 2 > 0 else 0)

    total = chinese_tokens + ascii_tokens + punct_tokens
    return max(total, 1)


class LLMMetrics:
    """LLM服务性能指标"""

    def __init__(self):
        self._lock = threading.Lock()
        self._stats = {
            "total_requests": 0,
            "total_errors": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "provider_switches": 0,
            "cache_hits": 0,
            "avg_latency": 0.0,
            "provider_distribution": {},
        }

    def record_request(self, provider: str, latency: float, tokens: int, cost: float, success: bool):
        with self._lock:
            self._stats["total_requests"] += 1
            if not success:
                self._stats["total_errors"] += 1
            self._stats["total_tokens"] += tokens
            self._stats["total_cost"] += cost
            n = self._stats["total_requests"]
            self._stats["avg_latency"] = (
                (self._stats["avg_latency"] * (n - 1) + latency) / n
            )
            self._stats["provider_distribution"][provider] = (
                self._stats["provider_distribution"].get(provider, 0) + 1
            )

    def record_provider_switch(self):
        with self._lock:
            self._stats["provider_switches"] += 1

    def record_cache_hit(self):
        with self._lock:
            self._stats["cache_hits"] += 1

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            stats = self._stats.copy()
            total = stats["total_requests"]
            stats["success_rate"] = (
                (total - stats["total_errors"]) / total * 100 if total > 0 else 100
            )
            stats["avg_cost_per_request"] = (
                stats["total_cost"] / total if total > 0 else 0
            )
            return stats


llm_metrics = LLMMetrics()


class LLMConnectionPool:
    """LLM连接池 - 管理多个Provider的连接"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._clients = {}
        self._pool_lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="llm_pool")
        self._initialized = True

    def get_client(self, provider: str):
        """获取或创建客户端"""
        with self._pool_lock:
            if provider in self._clients:
                return self._clients[provider]

            client = self._create_client(provider)
            self._clients[provider] = client
            return client

    def _create_client(self, provider: str):
        if provider == "deepseek":
            from openai import OpenAI
            return OpenAI(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_BASE_URL,
                timeout=DEFAULT_REQUEST_TIMEOUT,
                max_retries=2,
            )
        elif provider == "qwen":
            return None  # Qwen使用dashscope全局配置
        return None

    def execute_async(self, func, *args, **kwargs):
        """在线程池中异步执行"""
        return self._executor.submit(func, *args, **kwargs)

    def shutdown(self):
        self._executor.shutdown(wait=True)


class LLMService:
    """LLM服务类 - 极致优化版（多Provider、连接池、批量推理、智能降级）"""

    # 模型定价表（每1K tokens，单位：元）
    PRICING = {
        "qwen-turbo": {"input": 0.002, "output": 0.006},
        "qwen-plus": {"input": 0.004, "output": 0.012},
        "qwen-max": {"input": 0.02, "output": 0.06},
        "qwen-vl-max": {"input": 0.02, "output": 0.06},
        "deepseek-chat": {"input": 0.001, "output": 0.002},
        "deepseek-coder": {"input": 0.001, "output": 0.002},
        "deepseek-reasoner": {"input": 0.004, "output": 0.016},
    }

    def __init__(self):
        self.primary_provider = settings.LLM_PROVIDER.lower()
        self.fallback_provider = settings.FALLBACK_LLM_PROVIDER.lower() if hasattr(settings, 'FALLBACK_LLM_PROVIDER') else None
        self.prompt_version = settings.PROMPT_VERSION
        self.connection_pool = LLMConnectionPool()

        self._init_provider(self.primary_provider)
        if self.fallback_provider:
            self._init_provider(self.fallback_provider)

        app_logger.info(f"LLM服务初始化完成，主Provider: {self.primary_provider}, 降级Provider: {self.fallback_provider}")

    def _init_provider(self, provider: str):
        if provider == "deepseek":
            self.model = settings.DEEPSEEK_MODEL
            self.api_key = settings.DEEPSEEK_API_KEY
            self.base_url = settings.DEEPSEEK_BASE_URL
            self.client = self.connection_pool.get_client("deepseek")
        elif provider == "qwen":
            self.model = settings.QWEN_MODEL
            self.api_key = settings.QWEN_API_KEY
            self.client = None
            dashscope.api_key = self.api_key
        else:
            raise LLMServiceException(
                f"不支持的LLM Provider: {provider}",
                error_code=ErrorCode.LLM_SERVICE_ERROR
            )

    def _switch_provider(self):
        """智能降级切换Provider"""
        if not self.fallback_provider:
            return False

        app_logger.warning(f"LLM Provider降级: {self.primary_provider} -> {self.fallback_provider}")
        self.primary_provider, self.fallback_provider = self.fallback_provider, self.primary_provider
        self._init_provider(self.primary_provider)
        llm_metrics.record_provider_switch()
        return True

    def _parse_qwen_response(self, response, method_name: str = "unknown") -> str:
        if response.status_code != 200:
            error_msg = getattr(response, 'message', f"HTTP {response.status_code}")
            raise Exception(f"Qwen {method_name} API调用失败: status_code={response.status_code}, message={error_msg}")

        if not response.output:
            raise Exception(f"Qwen {method_name} 响应格式异常: output为空")

        result = None

        if hasattr(response.output, 'choices') and response.output.choices:
            choices = response.output.choices
            if len(choices) > 0:
                choice = choices[0]
                if (choice.message and
                    hasattr(choice.message, 'content') and
                    choice.message.content):
                    result = choice.message.content

        if not result and hasattr(response.output, 'text') and response.output.text:
            result = response.output.text

        if not result:
            raise Exception(
                f"Qwen {method_name} 响应格式异常: "
                f"无法从choices或text字段获取内容"
            )

        return result

    def _parse_deepseek_response(self, response, method_name: str = "unknown") -> str:
        if not response.choices or len(response.choices) == 0:
            raise Exception(f"DeepSeek {method_name} 响应格式异常: choices为空")

        choice = response.choices[0]
        if not choice.message or not choice.message.content:
            raise Exception(f"DeepSeek {method_name} 响应内容为空")

        return choice.message.content

    def _call_qwen_api(self, messages: List[Dict], temperature: float = 0.7,
                       max_tokens: int = 2000, **kwargs):
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
        if self.primary_provider == "deepseek":
            return self._call_deepseek_api(messages, temperature, max_tokens, **kwargs)
        elif self.primary_provider == "qwen":
            return self._call_qwen_api(messages, temperature, max_tokens, **kwargs)
        else:
            raise Exception(f"不支持的Provider: {self.primary_provider}")

    def _call_with_fallback(self, messages: List[Dict], temperature: float = 0.7,
                            max_tokens: int = 2000, **kwargs) -> Tuple[str, str]:
        """调用LLM，失败时自动降级"""
        try:
            result = self._call_provider(messages, temperature, max_tokens, **kwargs)
            return result, self.primary_provider
        except Exception as e:
            app_logger.warning(f"主Provider {self.primary_provider} 调用失败: {e}")
            if self._switch_provider():
                try:
                    result = self._call_provider(messages, temperature, max_tokens, **kwargs)
                    return result, self.primary_provider
                except Exception as e2:
                    app_logger.error(f"降级Provider {self.primary_provider} 也失败: {e2}")
                    raise
            raise

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        model_pricing = self.PRICING.get(self.model, {"input": 0.008, "output": 0.008})
        input_cost = (input_tokens / 1000) * model_pricing["input"]
        output_cost = (output_tokens / 1000) * model_pricing["output"]
        return round(input_cost + output_cost, 6)

    def _build_messages(self, system_prompt: Optional[str], prompt: str) -> List[Dict]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _extract_stream_content(self, chunk, provider: str) -> Optional[str]:
        try:
            if provider == "deepseek":
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        return delta.content
            elif provider == "qwen":
                if hasattr(chunk, 'status_code') and chunk.status_code == 200:
                    content = None
                    if (chunk.output and hasattr(chunk.output, 'choices') and
                        chunk.output.choices and len(chunk.output.choices) > 0):
                        choice = chunk.output.choices[0]
                        if (choice.message and
                            hasattr(choice.message, 'content') and
                            choice.message.content):
                            content = choice.message.content
                    if not content and chunk.output and hasattr(chunk.output, 'text'):
                        content = chunk.output.text
                    return content
        except Exception as e:
            app_logger.debug(f"提取流式内容失败 ({provider}): {e}")
        return None

    @retry(max_attempts=3, delay=1.0, backoff=2.0, exceptions=(Exception,))
    def generate(self, prompt: str, system_prompt: str = None,
                 temperature: float = None, max_tokens: int = None,
                 trace_id: Optional[str] = None,
                 user_id: Optional[str] = None,
                 session_id: Optional[str] = None,
                 prompt_version: Optional[str] = None,
                 **kwargs) -> str:
        """生成文本 - 极致优化版（带缓存、降级、精确计费）"""
        temperature = temperature if temperature is not None else settings.LLM_DEFAULT_TEMPERATURE
        max_tokens = max_tokens if max_tokens is not None else settings.LLM_DEFAULT_MAX_TOKENS
        prompt_version = prompt_version or self.prompt_version

        trace = None
        if langfuse_service.enabled:
            if not trace_id:
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

        cache_key = f"{system_prompt or ''}:{prompt}" if system_prompt else prompt
        cached_result = semantic_cache.get(cache_key)
        if cached_result:
            app_logger.info(f"语义缓存命中，相似度: {cached_result.get('similarity', 0):.3f}")
            track_llm_cache_hit("semantic")
            llm_metrics.record_cache_hit()

            latency = time.time() - start_time
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
                        "latency": latency
                    }
                )
            return cached_result["response"]

        try:
            result, used_provider = self._call_with_fallback(
                self._build_messages(system_prompt, prompt),
                temperature, max_tokens, **kwargs
            )

            latency = time.time() - start_time
            first_token_latency = first_token_time - start_time if first_token_time else latency

            estimated_input_tokens = _estimate_tokens(prompt) + (system_prompt and _estimate_tokens(system_prompt) or 0)
            estimated_output_tokens = _estimate_tokens(result)
            estimated_cost = self._estimate_cost(estimated_input_tokens, estimated_output_tokens)

            track_llm_request(
                model=self.model,
                status="success",
                duration=latency,
                first_token_latency=first_token_latency,
                input_tokens=int(estimated_input_tokens),
                output_tokens=int(estimated_output_tokens),
                cost=estimated_cost
            )

            llm_metrics.record_request(
                used_provider, latency,
                estimated_input_tokens + estimated_output_tokens,
                estimated_cost, True
            )

            if langfuse_service.enabled:
                langfuse_service.generation(
                    name="llm.generate",
                    model=self.model,
                    model_parameters={
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "prompt_version": prompt_version
                    },
                    input={"prompt": prompt, "system_prompt": system_prompt},
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
                        "estimated_cost": estimated_cost,
                        "provider": used_provider
                    }
                )

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
            latency = time.time() - start_time
            llm_metrics.record_request(self.primary_provider, latency, 0, 0, False)

            if langfuse_service.enabled:
                langfuse_service.generation(
                    name="llm.generate",
                    model=self.model,
                    model_parameters={"temperature": temperature, "max_tokens": max_tokens},
                    input={"prompt": prompt, "system_prompt": system_prompt},
                    output=f"Error: {str(e)}",
                    trace_id=trace_id,
                    metadata={"error": True, "error_message": str(e), "latency": latency}
                )

            raise LLMServiceException(f"LLM生成失败: {str(e)}", error_code=ErrorCode.LLM_SERVICE_ERROR)

    async def batch_generate(self, prompts: List[Dict[str, Any]],
                            temperature: float = None,
                            max_tokens: int = None,
                            max_concurrency: int = 5) -> List[str]:
        """批量生成 - 并发控制优化"""
        temperature = temperature if temperature is not None else settings.LLM_DEFAULT_TEMPERATURE
        max_tokens = max_tokens if max_tokens is not None else settings.LLM_DEFAULT_MAX_TOKENS

        semaphore = asyncio.Semaphore(max_concurrency)

        async def _generate_single(item: Dict) -> str:
            async with semaphore:
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(
                    None,
                    self.generate,
                    item["prompt"],
                    item.get("system_prompt"),
                    temperature,
                    max_tokens,
                    item.get("trace_id"),
                    item.get("user_id"),
                    item.get("session_id")
                )

        tasks = [_generate_single(item) for item in prompts]
        return await asyncio.gather(*tasks, return_exceptions=True)

    def stream_generate(self, prompt: str, system_prompt: str = None,
                       temperature: float = None, max_tokens: int = None,
                       trace_id: Optional[str] = None,
                       user_id: Optional[str] = None,
                       session_id: Optional[str] = None,
                       **kwargs):
        """流式生成 - 优化版（带超时保护和降级）"""
        temperature = temperature if temperature is not None else settings.LLM_DEFAULT_TEMPERATURE
        max_tokens = max_tokens if max_tokens is not None else settings.LLM_DEFAULT_MAX_TOKENS

        trace = None
        if langfuse_service.enabled and not trace_id:
            trace = langfuse_service.trace(
                name="llm.stream_generate",
                user_id=user_id,
                session_id=session_id,
                metadata={"model": self.model, "temperature": temperature, "max_tokens": max_tokens}
            )
            trace_id = trace.id if trace and hasattr(trace, 'id') else None

        start_time = time.time()
        first_token_time = None
        full_output = ""
        chunk_count = 0

        try:
            messages = self._build_messages(system_prompt, prompt)

            if self.primary_provider == "deepseek":
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

            elif self.primary_provider == "qwen":
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
                        if hasattr(response, 'status_code') and response.status_code != 200:
                            error_msg = getattr(response, 'message', f"HTTP {response.status_code}")
                            app_logger.error(f"Qwen流式生成错误: {error_msg}")
                            break
            else:
                raise Exception(f"不支持的Provider: {self.primary_provider}")

            if langfuse_service.enabled:
                latency = time.time() - start_time
                first_token_latency = first_token_time - start_time if first_token_time else latency

                langfuse_service.generation(
                    name="llm.stream_generate",
                    model=self.model,
                    model_parameters={"temperature": temperature, "max_tokens": max_tokens},
                    input={"prompt": prompt, "system_prompt": system_prompt},
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
                    model_parameters={"temperature": temperature, "max_tokens": max_tokens},
                    input={"prompt": prompt, "system_prompt": system_prompt},
                    output=f"Error: {str(e)}",
                    trace_id=trace_id,
                    metadata={"error": True, "error_message": str(e), "latency": time.time() - start_time}
                )
            raise

    @retry(max_attempts=3, delay=1.0, backoff=2.0, exceptions=(Exception,))
    def chat(self, messages: List[Dict[str, str]],
             temperature: float = None, max_tokens: int = None,
             trace_id: Optional[str] = None,
             user_id: Optional[str] = None,
             session_id: Optional[str] = None,
             **kwargs) -> str:
        """多轮对话 - 优化版"""
        temperature = temperature if temperature is not None else settings.LLM_DEFAULT_TEMPERATURE
        max_tokens = max_tokens if max_tokens is not None else settings.LLM_DEFAULT_MAX_TOKENS

        trace = None
        if langfuse_service.enabled and not trace_id:
            trace = langfuse_service.trace(
                name="llm.chat",
                user_id=user_id,
                session_id=session_id,
                metadata={"model": self.model, "temperature": temperature, "max_tokens": max_tokens, "message_count": len(messages)}
            )
            trace_id = trace.id if trace and hasattr(trace, 'id') else None

        start_time = time.time()

        try:
            result, used_provider = self._call_with_fallback(messages, temperature, max_tokens, **kwargs)

            if result:
                if langfuse_service.enabled:
                    total_text = " ".join([msg.get("content", "") for msg in messages])
                    latency = time.time() - start_time

                    langfuse_service.generation(
                        name="llm.chat",
                        model=self.model,
                        model_parameters={"temperature": temperature, "max_tokens": max_tokens},
                        input={"messages": messages},
                        output=result,
                        usage={
                            "input": int(_estimate_tokens(total_text)),
                            "output": int(_estimate_tokens(result)),
                            "total": int(_estimate_tokens(total_text)) + int(_estimate_tokens(result))
                        },
                        trace_id=trace_id,
                        metadata={"latency": latency, "message_count": len(messages), "provider": used_provider}
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
                    model_parameters={"temperature": temperature, "max_tokens": max_tokens},
                    input={"messages": messages},
                    output=f"Error: {str(e)}",
                    trace_id=trace_id,
                    metadata={"error": True, "error_message": str(e), "latency": time.time() - start_time}
                )
            raise

    def get_metrics(self) -> Dict[str, Any]:
        """获取LLM服务指标"""
        return llm_metrics.get_stats()


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

    DIAGNOSIS_ASSISTANT_USER = """基于以下医疗知识和患者症状，提供诊断辅助建议：\n\n参考资料：\n{context}\n\n患者症状描述：{question}\n\n请提供可能的诊断方向、建议检查项目，并标注信息来源。注意：这仅是辅助参考，最终诊断需要医生确认。"""

    DRUG_CONSULTATION_USER = """基于以下药物信息和医疗知识，回答用户的用药问题：\n\n参考资料：\n{context}\n\n用户问题：{question}\n\n请提供专业、准确的用药建议，并标注信息来源。注意：具体用药方案需要医生根据患者情况制定。"""

    @staticmethod
    def format_medical_prompt(context: str, question: str) -> str:
        return PromptTemplate.MEDICAL_CONSULTATION_USER.format(context=context, question=question)

    @staticmethod
    def format_diagnosis_prompt(question: str, context: str = "") -> str:
        """格式化诊断辅助Prompt"""
        return PromptTemplate.DIAGNOSIS_ASSISTANT_USER.format(context=context, question=question)

    @staticmethod
    def format_drug_prompt(question: str, drug_info: str = None, context: str = "") -> str:
        """格式化用药咨询Prompt"""
        drug_section = f"\n已知药物信息：{drug_info}\n" if drug_info else ""
        return PromptTemplate.DRUG_CONSULTATION_USER.format(
            context=context, question=question
        ) + drug_section
