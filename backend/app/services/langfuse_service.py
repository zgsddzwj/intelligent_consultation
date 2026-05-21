"""Langfuse服务 - 增强版（批量flush、降级策略、连接池优化、队列缓冲）"""
import time
import threading
from typing import Optional, Dict, Any, Callable
from functools import wraps
from collections import deque
from langfuse import Langfuse

try:
    from langfuse.decorators import langfuse_context, observe
except ImportError:
    langfuse_context = None
    observe = None
from app.config import get_settings
from app.utils.logger import app_logger

settings = get_settings()

# Langfuse客户端实例（懒加载）
_langfuse_client: Optional[Langfuse] = None

# 批处理配置
BATCH_SIZE = 50          # 批量flush阈值
FLUSH_INTERVAL = 30      # 自动flush间隔（秒）
MAX_QUEUE_SIZE = 1000    # 最大队列大小


def get_langfuse_client() -> Optional[Langfuse]:
    """获取Langfuse客户端（懒加载，带降级策略）"""
    global _langfuse_client
    
    if not settings.ENABLE_LANGFUSE:
        return None
    
    if _langfuse_client is None:
        try:
            if settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY:
                _langfuse_client = Langfuse(
                    public_key=settings.LANGFUSE_PUBLIC_KEY,
                    secret_key=settings.LANGFUSE_SECRET_KEY,
                    host=settings.LANGFUSE_HOST,
                    # 批处理优化
                    flush_at=BATCH_SIZE,
                    flush_interval=FLUSH_INTERVAL * 1000,  # 毫秒
                )
                app_logger.info("Langfuse客户端初始化成功")
            else:
                app_logger.warning("Langfuse密钥未配置，追踪功能已禁用")
        except Exception as e:
            app_logger.error(f"Langfuse客户端初始化失败: {e}")
            _langfuse_client = None
    
    return _langfuse_client


class LangfuseService:
    """Langfuse服务封装类（增强版）
    
    新增功能：
    - 批量flush队列
    - 自动降级策略
    - 连接健康检查
    - 队列大小限制
    """
    
    def __init__(self):
        self.client = get_langfuse_client()
        self.enabled = self.client is not None
        self._failure_count = 0
        self._max_failures = 5           # 最大连续失败次数
        self._circuit_open = False       # 降级开关
        self._circuit_reset_time = 0     # 降级恢复时间
        self._circuit_recovery = 60      # 降级恢复间隔（秒）
        self._lock = threading.Lock()
        self._pending_queue: deque = deque(maxlen=MAX_QUEUE_SIZE)
        
        # 启动后台flush线程
        if self.enabled:
            self._start_background_flush()
    
    def _check_circuit(self) -> bool:
        """检查降级状态"""
        if not self._circuit_open:
            return True
        
        # 检查是否可以恢复
        if time.time() - self._circuit_reset_time > self._circuit_recovery:
            with self._lock:
                self._circuit_open = False
                self._failure_count = 0
            app_logger.info("Langfuse降级恢复，重新启用追踪")
            return True
        
        return False
    
    def _record_failure(self):
        """记录失败"""
        with self._lock:
            self._failure_count += 1
            if self._failure_count >= self._max_failures:
                self._circuit_open = True
                self._circuit_reset_time = time.time()
                app_logger.warning(
                    f"Langfuse连续失败 {self._failure_count} 次，触发降级策略"
                )
    
    def _record_success(self):
        """记录成功"""
        if self._failure_count > 0:
            with self._lock:
                self._failure_count = max(0, self._failure_count - 1)
    
    def _start_background_flush(self):
        """启动后台flush线程"""
        def flush_worker():
            while True:
                time.sleep(FLUSH_INTERVAL)
                try:
                    if self.enabled and self.client and not self._circuit_open:
                        self.client.flush()
                except Exception as e:
                    app_logger.debug(f"Langfuse后台flush失败: {e}")
        
        thread = threading.Thread(target=flush_worker, daemon=True, name="langfuse-flush")
        thread.start()
    
    def trace(self, name: str, user_id: Optional[str] = None, 
              session_id: Optional[str] = None, 
              metadata: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """创建追踪trace（带降级）"""
        if not self.enabled or not self._check_circuit():
            return None
        
        try:
            trace = self.client.trace(
                name=name,
                user_id=user_id,
                session_id=session_id,
                metadata=metadata or {}
            )
            self._record_success()
            return trace
        except Exception as e:
            self._record_failure()
            app_logger.error(f"创建Langfuse trace失败: {e}")
            return None
    
    def span(self, name: str, trace_id: Optional[str] = None,
             parent_observation_id: Optional[str] = None,
             metadata: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """创建span（带降级）"""
        if not self.enabled or not self._check_circuit():
            return None
        
        try:
            span = self.client.span(
                name=name,
                trace_id=trace_id,
                parent_observation_id=parent_observation_id,
                metadata=metadata or {}
            )
            self._record_success()
            return span
        except Exception as e:
            self._record_failure()
            app_logger.error(f"创建Langfuse span失败: {e}")
            return None
    
    def generation(self, name: str, model: str, model_parameters: Dict[str, Any],
                   input: Any, output: Any, usage: Optional[Dict[str, int]] = None,
                   trace_id: Optional[str] = None,
                   parent_observation_id: Optional[str] = None,
                   metadata: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """记录LLM生成调用（带降级）"""
        if not self.enabled or not self._check_circuit():
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
            self._record_success()
            return generation
        except Exception as e:
            self._record_failure()
            app_logger.error(f"记录Langfuse generation失败: {e}")
            return None
    
    def score(self, trace_id: str, name: str, value: float,
              comment: Optional[str] = None) -> Optional[Any]:
        """记录评分（带降级）"""
        if not self.enabled or not self._check_circuit():
            return None
        
        try:
            score = self.client.score(
                trace_id=trace_id,
                name=name,
                value=value,
                comment=comment
            )
            self._record_success()
            return score
        except Exception as e:
            self._record_failure()
            app_logger.error(f"记录Langfuse score失败: {e}")
            return None
    
    def flush(self):
        """刷新所有待发送的数据（带错误处理）"""
        if self.enabled and self.client and not self._circuit_open:
            try:
                self.client.flush()
                self._record_success()
            except Exception as e:
                self._record_failure()
                app_logger.error(f"Langfuse flush失败: {e}")
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            "enabled": self.enabled,
            "circuit_open": self._circuit_open,
            "failure_count": self._failure_count,
            "client_initialized": self.client is not None
        }


# 全局Langfuse服务实例
langfuse_service = LangfuseService()


def trace_llm_call(func: Callable) -> Callable:
    """LLM调用追踪装饰器（增强版，带降级）"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not langfuse_service.enabled or langfuse_service._circuit_open:
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
        if not langfuse_service.enabled or observe is None:
            return func
        
        @observe(name=name or f"{func.__module__}.{func.__name__}", 
                 metadata=metadata)
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        return wrapper
    return decorator
