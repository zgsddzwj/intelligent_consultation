"""重试机制和断路器 - 增强版（线程安全断路器、半开状态探测、状态监控）"""
import time
import asyncio
import threading
from functools import wraps
from typing import Callable, Type, Tuple, Optional, Any
from enum import Enum
from app.utils.logger import app_logger


class CircuitState(Enum):
    """断路器状态"""
    CLOSED = "closed"  # 正常状态（允许请求通过）
    OPEN = "open"  # 打开状态（拒绝请求）
    HALF_OPEN = "half_open"  # 半开状态（允许探测请求）


class CircuitBreaker:
    """
    断路器（线程安全版）
    
    状态转换：
    CLOSED -> OPEN: 失败次数达到阈值
    OPEN -> HALF_OPEN: 经过恢复超时时间
    HALF_OPEN -> CLOSED: 探测请求成功
    HALF_OPEN -> OPEN: 探测请求失败
    
    改进点：
    - 使用 threading.Lock 保证线程安全
    - 半开状态只允许一个探测请求通过
    - 记录最后失败时间和错误信息
    - 提供状态查询接口用于监控
    """
    
    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 1,
        expected_exception: Type[Exception] = Exception
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.expected_exception = expected_exception
        
        # 内部状态（使用锁保护）
        self._lock = threading.RLock()
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._state = CircuitState.CLOSED
        self._half_open_calls = 0
        
        # 监控信息
        self._total_calls = 0
        self._total_successes = 0
        self._total_failures = 0
        self._last_error: Optional[str] = None
    
    @property
    def state(self) -> CircuitState:
        """获取当前状态（线程安全）"""
        with self._lock:
            return self._state
    
    @property
    def failure_count(self) -> int:
        """获取当前失败计数"""
        with self._lock:
            return self._failure_count
    
    def get_stats(self) -> dict:
        """获取断路器统计信息（用于监控）"""
        with self._lock:
            return {
                "name": self.name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "failure_threshold": self.failure_threshold,
                "recovery_timeout": self.recovery_timeout,
                "last_failure_time": self._last_failure_time,
                "last_error": self._last_error,
                "total_calls": self._total_calls,
                "total_successes": self._total_successes,
                "total_failures": self._total_failures,
                "success_rate": (
                    f"{self._total_successes / max(self._total_calls, 1) * 100:.1f}%"
                    if self._total_calls > 0 else "N/A"
                )
            }
    
    def _should_allow_request(self) -> bool:
        """检查是否应该允许请求通过（内部方法，需要持有锁）"""
        if self._state == CircuitState.CLOSED:
            return True
        
        if self._state == CircuitState.OPEN:
            # 检查是否可以进入半开状态
            if (self._last_failure_time and 
                time.time() - self._last_failure_time > self.recovery_timeout):
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                app_logger.info(f"断路器 [{self.name}] 进入半开状态，尝试恢复")
                return True
            return False
        
        if self._state == CircuitState.HALF_OPEN:
            # 半开状态只允许有限数量的探测请求
            if self._half_open_calls < self.half_open_max_calls:
                self._half_open_calls += 1
                return True
            return False
        
        return False
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """同步调用（带断路器保护）"""
        with self._lock:
            self._total_calls += 1
            
            if not self._should_allow_request():
                raise CircuitOpenException(
                    f"断路器 [{self.name}] 打开，请求被拒绝",
                    service_name=self.name,
                    state=self._state.value
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure(str(e))
            raise
    
    async def async_call(self, func: Callable, *args, **kwargs) -> Any:
        """异步调用（带断路器保护）"""
        with self._lock:
            self._total_calls += 1
            
            if not self._should_allow_request():
                raise CircuitOpenException(
                    f"断路器 [{self.name}] 打开，请求被拒绝",
                    service_name=self.name,
                    state=self._state.value
                )
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure(str(e))
            raise
    
    def _on_success(self):
        """成功回调（线程安全）"""
        with self._lock:
            self._total_successes += 1
            
            if self._state == CircuitState.HALF_OPEN:
                # 探测成功，关闭断路器
                self._state = CircuitState.CLOSED
                app_logger.info(f"断路器 [{self.name}] 恢复，进入关闭状态")
            
            # 重置失败计数
            self._failure_count = 0
            self._last_error = None
    
    def _on_failure(self, error_msg: str = ""):
        """失败回调（线程安全）"""
        with self._lock:
            self._total_failures += 1
            self._failure_count += 1
            self._last_failure_time = time.time()
            self._last_error = error_msg[:200]  # 限制长度
            
            if self._failure_count >= self.failure_threshold:
                if self._state != CircuitState.OPEN:
                    old_state = self._state
                    self._state = CircuitState.OPEN
                    app_logger.warning(
                        f"断路器 [{self.name}] 打开 ({old_state.value} -> open)，"
                        f"失败次数: {self._failure_count}, 错误: {error_msg[:100]}"
                    )
    
    def reset(self):
        """手动重置断路器状态"""
        with self._lock:
            old_state = self._state
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._last_failure_time = None
            self._half_open_calls = 0
            self._last_error = None
            app_logger.info(f"断路器 [{self.name}] 已手动重置 ({old_state.value} -> closed)")


class CircuitOpenException(Exception):
    """断路器打开时抛出的异常"""
    
    def __init__(self, message: str, service_name: str = "", state: str = "open"):
        super().__init__(message)
        self.service_name = service_name
        self.state = state


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable] = None,
    jitter: bool = True
):
    """
    重试装饰器（指数退避 + 随机抖动）
    
    Args:
        max_attempts: 最大尝试次数
        delay: 初始延迟（秒）
        backoff: 退避倍数
        exceptions: 需要重试的异常类型
        on_retry: 重试回调函数
        jitter: 是否添加随机抖动（避免惊群效应）
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts:
                        # 添加随机抖动（±25%）
                        actual_delay = current_delay
                        if jitter:
                            import random
                            jitter_range = current_delay * 0.25
                            actual_delay = current_delay + random.uniform(-jitter_range, jitter_range)
                        
                        app_logger.warning(
                            f"重试 {attempt}/{max_attempts}: {func.__name__}, "
                            f"延迟 {actual_delay:.2f}秒, 错误: {str(e)}"
                        )
                        if on_retry:
                            on_retry(attempt, e)
                        await asyncio.sleep(actual_delay)
                        current_delay *= backoff
                    else:
                        app_logger.error(f"重试失败: {func.__name__}, 已尝试 {max_attempts} 次")
            
            raise last_exception
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts:
                        actual_delay = current_delay
                        if jitter:
                            import random
                            jitter_range = current_delay * 0.25
                            actual_delay = current_delay + random.uniform(-jitter_range, jitter_range)
                        
                        app_logger.warning(
                            f"重试 {attempt}/{max_attempts}: {func.__name__}, "
                            f"延迟 {actual_delay:.2f}秒, 错误: {str(e)}"
                        )
                        if on_retry:
                            on_retry(attempt, e)
                        time.sleep(actual_delay)
                        current_delay *= backoff
                    else:
                        app_logger.error(f"重试失败: {func.__name__}, 已尝试 {max_attempts} 次")
            
            raise last_exception
        
        # 判断是否为异步函数
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# 全局断路器实例（可按服务分类）
_circuit_breakers: Dict[str, CircuitBreaker] = {}
_circuit_breakers_lock = threading.Lock()


def get_circuit_breaker(
    service_name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60
) -> CircuitBreaker:
    """获取或创建线程安全的断路器实例"""
    global _circuit_breakers
    
    with _circuit_breakers_lock:
        if service_name not in _circuit_breakers:
            _circuit_breakers[service_name] = CircuitBreaker(
                name=service_name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout
            )
        return _circuit_breakers[service_name]


def reset_circuit_breaker(service_name: str):
    """重置指定断路器的状态"""
    cb = get_circuit_breaker(service_name)
    cb.reset()


def get_all_circuit_breaker_stats() -> Dict[str, dict]:
    """获取所有断路器的统计信息（用于监控端点）"""
    stats = {}
    for name, cb in _circuit_breakers.items():
        try:
            stats[name] = cb.get_stats()
        except Exception:
            pass
    return stats
