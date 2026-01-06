"""重试机制和断路器"""
import time
import asyncio
from functools import wraps
from typing import Callable, Type, Tuple, Optional, Any
from enum import Enum
from app.utils.logger import app_logger


class CircuitState(Enum):
    """断路器状态"""
    CLOSED = "closed"  # 正常状态
    OPEN = "open"  # 打开状态（拒绝请求）
    HALF_OPEN = "half_open"  # 半开状态（尝试恢复）


class CircuitBreaker:
    """断路器"""
    
    def __init__(
        self,
        failure_threshold: int = 5,  # 失败阈值
        recovery_timeout: int = 60,  # 恢复超时（秒）
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """同步调用"""
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                app_logger.info("断路器进入半开状态，尝试恢复")
            else:
                raise Exception("断路器打开，请求被拒绝")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    async def async_call(self, func: Callable, *args, **kwargs) -> Any:
        """异步调用"""
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                app_logger.info("断路器进入半开状态，尝试恢复")
            else:
                raise Exception("断路器打开，请求被拒绝")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """成功回调"""
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            app_logger.info("断路器恢复，进入关闭状态")
        self.failure_count = 0
    
    def _on_failure(self):
        """失败回调"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            app_logger.warning(f"断路器打开，失败次数: {self.failure_count}")


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable] = None
):
    """
    重试装饰器（指数退避）
    
    Args:
        max_attempts: 最大尝试次数
        delay: 初始延迟（秒）
        backoff: 退避倍数
        exceptions: 需要重试的异常类型
        on_retry: 重试回调函数
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
                        app_logger.warning(
                            f"重试 {attempt}/{max_attempts}: {func.__name__}, "
                            f"延迟 {current_delay:.2f}秒, 错误: {str(e)}"
                        )
                        if on_retry:
                            on_retry(attempt, e)
                        await asyncio.sleep(current_delay)
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
                        app_logger.warning(
                            f"重试 {attempt}/{max_attempts}: {func.__name__}, "
                            f"延迟 {current_delay:.2f}秒, 错误: {str(e)}"
                        )
                        if on_retry:
                            on_retry(attempt, e)
                        time.sleep(current_delay)
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
_circuit_breakers = {}


def get_circuit_breaker(
    service_name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60
) -> CircuitBreaker:
    """获取或创建断路器实例"""
    if service_name not in _circuit_breakers:
        _circuit_breakers[service_name] = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout
        )
    return _circuit_breakers[service_name]

