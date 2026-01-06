"""Langfuse服务 - LLM可观测性追踪"""
from typing import Optional, Dict, Any, Callable
from functools import wraps
import time
from langfuse import Langfuse
from langfuse.decorators import langfuse_context, observe
from app.config import get_settings
from app.utils.logger import app_logger

settings = get_settings()

# Langfuse客户端实例（懒加载）
_langfuse_client: Optional[Langfuse] = None


def get_langfuse_client() -> Optional[Langfuse]:
    """获取Langfuse客户端（懒加载）"""
    global _langfuse_client
    
    if not settings.ENABLE_LANGFUSE:
        return None
    
    if _langfuse_client is None:
        try:
            if settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY:
                _langfuse_client = Langfuse(
                    public_key=settings.LANGFUSE_PUBLIC_KEY,
                    secret_key=settings.LANGFUSE_SECRET_KEY,
                    host=settings.LANGFUSE_HOST
                )
                app_logger.info("Langfuse客户端初始化成功")
            else:
                app_logger.warning("Langfuse密钥未配置，追踪功能已禁用")
        except Exception as e:
            app_logger.error(f"Langfuse客户端初始化失败: {e}")
            _langfuse_client = None
    
    return _langfuse_client


class LangfuseService:
    """Langfuse服务封装类"""
    
    def __init__(self):
        self.client = get_langfuse_client()
        self.enabled = self.client is not None
    
    def trace(self, name: str, user_id: Optional[str] = None, 
              session_id: Optional[str] = None, 
              metadata: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """创建追踪trace"""
        if not self.enabled:
            return None
        
        try:
            trace = self.client.trace(
                name=name,
                user_id=user_id,
                session_id=session_id,
                metadata=metadata or {}
            )
            return trace
        except Exception as e:
            app_logger.error(f"创建Langfuse trace失败: {e}")
            return None
    
    def span(self, name: str, trace_id: Optional[str] = None,
             parent_observation_id: Optional[str] = None,
             metadata: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """创建span"""
        if not self.enabled:
            return None
        
        try:
            span = self.client.span(
                name=name,
                trace_id=trace_id,
                parent_observation_id=parent_observation_id,
                metadata=metadata or {}
            )
            return span
        except Exception as e:
            app_logger.error(f"创建Langfuse span失败: {e}")
            return None
    
    def generation(self, name: str, model: str, model_parameters: Dict[str, Any],
                   input: Any, output: Any, usage: Optional[Dict[str, int]] = None,
                   trace_id: Optional[str] = None,
                   parent_observation_id: Optional[str] = None,
                   metadata: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """记录LLM生成调用"""
        if not self.enabled:
            return None
        
        try:
            generation = self.client.generation(
                name=name,
                model=model,
                model_parameters=model_parameters,
                input=input,
                output=output,
                usage=usage,
                trace_id=trace_id,
                parent_observation_id=parent_observation_id,
                metadata=metadata or {}
            )
            return generation
        except Exception as e:
            app_logger.error(f"记录Langfuse generation失败: {e}")
            return None
    
    def score(self, trace_id: str, name: str, value: float,
              comment: Optional[str] = None) -> Optional[Any]:
        """记录评分（用于用户反馈）"""
        if not self.enabled:
            return None
        
        try:
            score = self.client.score(
                trace_id=trace_id,
                name=name,
                value=value,
                comment=comment
            )
            return score
        except Exception as e:
            app_logger.error(f"记录Langfuse score失败: {e}")
            return None
    
    def flush(self):
        """刷新所有待发送的数据"""
        if self.enabled:
            try:
                self.client.flush()
            except Exception as e:
                app_logger.error(f"Langfuse flush失败: {e}")


# 全局Langfuse服务实例
langfuse_service = LangfuseService()


def trace_llm_call(func: Callable) -> Callable:
    """LLM调用追踪装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not langfuse_service.enabled:
            return func(*args, **kwargs)
        
        start_time = time.time()
        trace_name = f"{func.__module__}.{func.__name__}"
        
        # 提取参数
        prompt = kwargs.get("prompt") or (args[0] if args else "")
        system_prompt = kwargs.get("system_prompt")
        model = kwargs.get("model") or settings.QWEN_MODEL
        temperature = kwargs.get("temperature", settings.LLM_DEFAULT_TEMPERATURE)
        max_tokens = kwargs.get("max_tokens", settings.LLM_DEFAULT_MAX_TOKENS)
        
        # 创建trace
        trace = langfuse_service.trace(
            name=trace_name,
            metadata={
                "function": func.__name__,
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
        )
        
        try:
            # 执行函数
            result = func(*args, **kwargs)
            
            # 计算延迟
            latency = time.time() - start_time
            
            # 记录generation
            if trace:
                langfuse_service.generation(
                    name=trace_name,
                    model=model,
                    model_parameters={
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    },
                    input={
                        "prompt": prompt,
                        "system_prompt": system_prompt
                    },
                    output=result if isinstance(result, str) else str(result),
                    trace_id=trace.id if hasattr(trace, 'id') else None,
                    metadata={
                        "latency": latency
                    }
                )
            
            return result
            
        except Exception as e:
            # 记录错误
            if trace:
                langfuse_service.generation(
                    name=trace_name,
                    model=model,
                    model_parameters={
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    },
                    input={
                        "prompt": prompt,
                        "system_prompt": system_prompt
                    },
                    output=f"Error: {str(e)}",
                    trace_id=trace.id if hasattr(trace, 'id') else None,
                    metadata={
                        "error": True,
                        "error_message": str(e)
                    }
                )
            raise
    
    return wrapper


def observe_span(name: Optional[str] = None, 
                 metadata: Optional[Dict[str, Any]] = None):
    """Span观察装饰器（使用Langfuse的observe装饰器）"""
    def decorator(func: Callable) -> Callable:
        if not langfuse_service.enabled:
            return func
        
        @observe(name=name or f"{func.__module__}.{func.__name__}", 
                 metadata=metadata)
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

