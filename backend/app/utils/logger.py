"""日志配置 - 增强版（结构化日志、日志聚合、性能追踪）
版本: 2.1.0
更新日期: 2025-01
"""
import sys
import json
import time
import functools
import contextvars
import uuid
from typing import Dict, Any, Optional, Callable
from loguru import logger
from pathlib import Path
from app.config import get_settings

settings = get_settings()

# 请求上下文变量
request_id_var = contextvars.ContextVar('request_id', default=None)
user_id_var = contextvars.ContextVar('user_id', default=None)


def set_request_context(request_id: str = None, user_id: str = None):
    """设置请求上下文"""
    request_id_var.set(request_id or str(uuid.uuid4())[:12])
    if user_id:
        user_id_var.set(user_id)


def get_request_id() -> str:
    """获取当前请求ID"""
    return request_id_var.get() or "unknown"


def get_user_id() -> str:
    """获取当前用户ID"""
    return user_id_var.get() or "anonymous"


class LogAggregator:
    """日志聚合器 - 收集和批量发送日志"""

    def __init__(self, batch_size: int = 100, flush_interval: float = 5.0):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._buffer: list = []
        self._last_flush = time.time()

    def log(self, level: str, message: str, extra: dict = None):
        """添加日志到缓冲区"""
        entry = {
            "timestamp": time.time(),
            "level": level,
            "message": message,
            "extra": extra or {}
        }
        self._buffer.append(entry)

        if len(self._buffer) >= self.batch_size or (time.time() - self._last_flush) >= self.flush_interval:
            self.flush()

    def flush(self):
        """刷新缓冲区"""
        if not self._buffer:
            return

        # 实际项目中可以发送到ELK/Loki等日志系统
        # 这里仅记录到本地日志
        for entry in self._buffer:
            logger.log(entry["level"], f"[AGG] {entry['message']}", extra=entry.get("extra"))

        self._buffer.clear()
        self._last_flush = time.time()


class PerformanceLogger:
    """性能日志装饰器 - 记录函数执行时间"""

    def __init__(self, threshold_ms: float = 100.0):
        self.threshold_ms = threshold_ms

    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                duration_ms = (time.time() - start) * 1000
                if duration_ms > self.threshold_ms:
                    logger.warning(
                        f"慢操作: {func.__module__}.{func.__name__} "
                        f"耗时 {duration_ms:.2f}ms (阈值: {self.threshold_ms}ms)"
                    )
        return wrapper

    def async_wrapper(self, func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            try:
                return await func(*args, **kwargs)
            finally:
                duration_ms = (time.time() - start) * 1000
                if duration_ms > self.threshold_ms:
                    logger.warning(
                        f"慢操作: {func.__module__}.{func.__name__} "
                        f"耗时 {duration_ms:.2f}ms (阈值: {self.threshold_ms}ms)"
                    )
        return wrapper


def log_execution_time(threshold_ms: float = 100.0):
    """记录函数执行时间的装饰器"""
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            return PerformanceLogger(threshold_ms).async_wrapper(func)
        return PerformanceLogger(threshold_ms)(func)
    return decorator


import asyncio


def setup_logger():
    """配置日志系统 - 增强版"""
    logger.remove()

    # 结构化日志格式（JSON）
    def format_record(record):
        log_data = {
            "timestamp": record["time"].isoformat(),
            "level": record["level"].name,
            "message": record["message"],
            "module": record["name"],
            "function": record["function"],
            "line": record["line"],
        }

        # 添加请求ID
        try:
            from app.common.tracing import get_request_id
            request_id = get_request_id()
            if request_id:
                log_data["request_id"] = request_id
        except (ImportError, RuntimeError):
            pass

        # 添加额外字段
        if record["extra"]:
            for key, value in record["extra"].items():
                if key not in log_data:
                    log_data[key] = value

        # 添加异常信息
        if record["exception"]:
            log_data["exception"] = {
                "type": record["exception"].type.__name__,
                "value": str(record["exception"].value),
                "traceback": record["exception"].traceback
            }

        return json.dumps(log_data, ensure_ascii=False) + "\n"

    # 控制台输出
    if settings.ENVIRONMENT == "development":
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level=settings.LOG_LEVEL,
            colorize=True
        )
    else:
        logger.add(
            sys.stdout,
            format=format_record,
            level=settings.LOG_LEVEL,
            serialize=False
        )

    # 文件输出
    log_file = Path(settings.LOG_FILE)
    if not log_file.is_absolute():
        backend_dir = Path(__file__).parent.parent.parent
        log_file = backend_dir / log_file
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger.add(
        str(log_file),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=settings.LOG_LEVEL,
        rotation="50 MB",
        retention="14 days",
        compression="zip",
        encoding="utf-8",
        backtrace=True,
        diagnose=True
    )

    # 单独的错误日志文件
    error_log_file = log_file.parent / "error.log"
    logger.add(
        str(error_log_file),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        rotation="20 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
        filter=lambda record: record["level"].name == "ERROR"
    )

    # 审计日志文件
    audit_log_file = log_file.parent / "audit.log"
    logger.add(
        str(audit_log_file),
        format=format_record,
        level="INFO",
        rotation="100 MB",
        retention="90 days",
        compression="zip",
        encoding="utf-8",
        filter=lambda record: record["extra"].get("log_type") == "audit"
    )

    # 性能日志文件
    perf_log_file = log_file.parent / "performance.log"
    logger.add(
        str(perf_log_file),
        format=format_record,
        level="INFO",
        rotation="50 MB",
        retention="7 days",
        compression="zip",
        encoding="utf-8",
        filter=lambda record: record["extra"].get("log_type") == "performance"
    )

    return logger


# 初始化日志
app_logger = setup_logger()

# 全局日志聚合器
log_aggregator = LogAggregator()
