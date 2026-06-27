"""Langfuse服务 - 适配 Langfuse SDK v4+（OpenTelemetry-based API）

v4 变更摘要：
- client.trace() / client.generation() / client.span() / client.score() 已移除
- 统一使用 client.start_observation(as_type=...) 创建观测
- trace_context={"trace_id": ...} 替代旧 trace_id 参数关联观测
- usage → usage_details
- client.score() → client.create_score()
- observe 装饰器从 langfuse.decorators 迁移至 langfuse 顶层
"""
import time
import threading
from dataclasses import dataclass
from typing import Optional, Dict, Any, Callable
from functools import wraps
from collections import deque
from langfuse import Langfuse

try:
    from langfuse import observe as _observe
except ImportError:
    _observe = None

from app.config import get_settings
from app.utils.logger import app_logger

settings = get_settings()

# Langfuse客户端实例（懒加载）
_langfuse_client: Optional[Langfuse] = None

# 批处理配置
BATCH_SIZE = 50          # 批量flush阈值
FLUSH_INTERVAL = 30      # 自动flush间隔（秒）
MAX_QUEUE_SIZE = 1000    # 最大队列大小


@dataclass
class _TraceWrapper:
    """兼容旧 API 的 trace 返回值包装

    旧代码通过 trace.id 获取 trace_id 传入后续 generation() 调用，
    v4 中 observation.id 是 span_id，observation.trace_id 才是 trace_id，
    因此用此包装确保 .id 返回 trace_id。
    """
    id: str
    _observation: Any


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
                app_logger.info("Langfuse客户端初始化成功 (v4 OTel API)")
            else:
                app_logger.warning("Langfuse密钥未配置，追踪功能已禁用")
        except Exception as e:
            app_logger.error(f"Langfuse客户端初始化失败: {e}")
            _langfuse_client = None

    return _langfuse_client


class LangfuseService:
    """Langfuse服务封装类（v4 适配版）

    功能：
    - 批量flush队列
    - 自动降级策略（熔断器）
    - 连接健康检查
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

    def _build_trace_context(self, trace_id: Optional[str]) -> Optional[Dict[str, str]]:
        """构建 v4 trace_context 参数"""
        if trace_id:
            return {"trace_id": trace_id}
        return None

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

    # ------------------------------------------------------------------
    #  v4 适配的核心方法
    # ------------------------------------------------------------------

    def trace(self, name: str, user_id: Optional[str] = None,
              session_id: Optional[str] = None,
              metadata: Optional[Dict[str, Any]] = None) -> Optional[_TraceWrapper]:
        """创建追踪trace（带降级）

        v4: 使用 start_observation(as_type="span") 创建根观测，
        user_id / session_id 放入 metadata（v4 不再直接支持这两个参数）。
        """
        if not self.enabled or not self._check_circuit():
            return None

        try:
            enriched_meta = dict(metadata or {})
            if user_id:
                enriched_meta["user_id"] = user_id
            if session_id:
                enriched_meta["session_id"] = session_id

            observation = self.client.start_observation(
                name=name,
                as_type="span",
                metadata=enriched_meta or None,
            )
            self._record_success()
            # 包装返回值：.id 返回 trace_id 以兼容旧调用方
            return _TraceWrapper(id=observation.trace_id, _observation=observation)
        except Exception as e:
            self._record_failure()
            app_logger.error(f"创建Langfuse trace失败: {e}")
            return None

    def span(self, name: str, trace_id: Optional[str] = None,
             parent_observation_id: Optional[str] = None,
             metadata: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """创建span（带降级）

        v4: 使用 start_observation(as_type="span") + trace_context 关联。
        """
        if not self.enabled or not self._check_circuit():
            return None

        try:
            trace_ctx = self._build_trace_context(trace_id)
            span = self.client.start_observation(
                name=name,
                as_type="span",
                trace_context=trace_ctx,
                metadata=metadata or None,
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
        """记录LLM生成调用（带降级）

        v4 变更：
        - usage → usage_details
        - trace_id → trace_context
        """
        if not self.enabled or not self._check_circuit():
            return None

        try:
            trace_ctx = self._build_trace_context(trace_id)
            kwargs: Dict[str, Any] = dict(
                name=name,
                as_type="generation",
                model=model,
                model_parameters=model_parameters,
                input=input,
                output=output,
                metadata=metadata or None,
                trace_context=trace_ctx,
            )
            if usage:
                kwargs["usage_details"] = usage

            generation = self.client.start_observation(**kwargs)
            self._record_success()
            return generation
        except Exception as e:
            self._record_failure()
            app_logger.error(f"记录Langfuse generation失败: {e}")
            return None

    def score(self, trace_id: str, name: str, value: float,
              comment: Optional[str] = None) -> Optional[Any]:
        """记录评分（带降级）

        v4: client.score() → client.create_score()
        """
        if not self.enabled or not self._check_circuit():
            return None

        try:
            self.client.create_score(
                trace_id=trace_id,
                name=name,
                value=value,
                comment=comment,
            )
            self._record_success()
            return True
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
    """Span观察装饰器（使用Langfuse v4的observe装饰器）"""
    def decorator(func: Callable) -> Callable:
        if not langfuse_service.enabled or _observe is None:
            return func

        @_observe(name=name or f"{func.__module__}.{func.__name__}")
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper
    return decorator
