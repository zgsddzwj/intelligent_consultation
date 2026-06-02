"""监控和指标收集 - 极致优化版（分布式追踪、性能剖析、业务指标、告警规则）"""
import time
import os
import threading
import functools
from typing import Dict, Any, Optional, Callable, List
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST, Info
from starlette.responses import Response
from app.utils.logger import app_logger

# ========== Prometheus指标定义 ==========

http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

active_connections = Gauge(
    'active_connections',
    'Number of active connections'
)

database_queries_total = Counter(
    'database_queries_total',
    'Total database queries',
    ['operation', 'table']
)

database_query_duration_seconds = Histogram(
    'database_query_duration_seconds',
    'Database query duration in seconds',
    ['operation', 'table']
)

llm_requests_total = Counter(
    'llm_requests_total',
    'Total LLM requests',
    ['model', 'status']
)

llm_request_duration_seconds = Histogram(
    'llm_request_duration_seconds',
    'LLM request duration in seconds',
    ['model']
)

llm_first_token_latency_seconds = Histogram(
    'llm_first_token_latency_seconds',
    'LLM first token latency in seconds',
    ['model']
)

llm_tokens_total = Counter(
    'llm_tokens_total',
    'Total LLM tokens used',
    ['model', 'type']
)

llm_cost_total = Counter(
    'llm_cost_total',
    'Total LLM cost in currency units',
    ['model', 'currency']
)

llm_cache_hits_total = Counter(
    'llm_cache_hits_total',
    'Total LLM cache hits',
    ['cache_type']
)

cache_hits_total = Counter(
    'cache_hits_total',
    'Total cache hits',
    ['cache_type']
)

cache_misses_total = Counter(
    'cache_misses_total',
    'Total cache misses',
    ['cache_type']
)

system_memory_usage_bytes = Gauge(
    'system_memory_usage_bytes',
    'Current memory usage in bytes',
    ['type']
)

system_cpu_usage_percent = Gauge(
    'system_cpu_usage_percent',
    'Current CPU usage percentage'
)

system_open_files = Gauge(
    'system_open_files',
    'Number of open file descriptors'
)

consultation_requests_total = Counter(
    'consultation_requests_total',
    'Total consultation requests',
    ['agent_type', 'status']
)

consultation_duration_seconds = Histogram(
    'consultation_duration_seconds',
    'Consultation processing duration',
    ['agent_type']
)

image_analysis_requests_total = Counter(
    'image_analysis_requests_total',
    'Total image analysis requests',
    ['status']
)

knowledge_graph_queries_total = Counter(
    'knowledge_graph_queries_total',
    'Total knowledge graph queries',
    ['query_type', 'status']
)

# 新增：告警指标
alert_firing_total = Counter(
    'alert_firing_total',
    'Total alert firings',
    ['alert_name', 'severity']
)

# 应用信息
app_info = Info(
    'application',
    'Application information'
)

# ========== 指标追踪函数 ==========

def track_http_request(method: str, endpoint: str, status_code: int, duration: float):
    http_requests_total.labels(method=method, endpoint=endpoint, status=status_code).inc()
    http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)


def track_database_query(operation: str, table: str, duration: float):
    database_queries_total.labels(operation=operation, table=table).inc()
    database_query_duration_seconds.labels(operation=operation, table=table).observe(duration)


def track_llm_request(model: str, status: str, duration: float,
                     first_token_latency: Optional[float] = None,
                     input_tokens: Optional[int] = None,
                     output_tokens: Optional[int] = None,
                     cost: Optional[float] = None,
                     currency: str = "CNY"):
    llm_requests_total.labels(model=model, status=status).inc()
    llm_request_duration_seconds.labels(model=model).observe(duration)

    if first_token_latency is not None:
        llm_first_token_latency_seconds.labels(model=model).observe(first_token_latency)

    if input_tokens is not None:
        llm_tokens_total.labels(model=model, type="input").inc(input_tokens)
    if output_tokens is not None:
        llm_tokens_total.labels(model=model, type="output").inc(output_tokens)
    if input_tokens is not None and output_tokens is not None:
        llm_tokens_total.labels(model=model, type="total").inc(input_tokens + output_tokens)

    if cost is not None:
        llm_cost_total.labels(model=model, currency=currency).inc(cost)


def track_cache_hit(cache_type: str):
    cache_hits_total.labels(cache_type=cache_type).inc()


def track_cache_miss(cache_type: str):
    cache_misses_total.labels(cache_type=cache_type).inc()


def track_llm_cache_hit(cache_type: str = "semantic"):
    llm_cache_hits_total.labels(cache_type=cache_type).inc()


def track_consultation(agent_type: str, status: str, duration: float):
    consultation_requests_total.labels(agent_type=agent_type, status=status).inc()
    consultation_duration_seconds.labels(agent_type=agent_type).observe(duration)


def track_image_analysis(status: str):
    image_analysis_requests_total.labels(status=status).inc()


def track_knowledge_graph_query(query_type: str, status: str):
    knowledge_graph_queries_total.labels(query_type=query_type, status=status).inc()


# ========== 中间件和工具函数 ==========

def metrics_middleware(app):
    @app.middleware("http")
    async def metrics_handler(request, call_next):
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time

        endpoint = request.url.path
        method = request.method
        status_code = response.status_code

        track_http_request(method, endpoint, status_code, duration)

        return response

    return app


def get_metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


# ========== 增强性能监控器 ==========

class PerformanceMonitor:
    """增强性能监控器（支持告警阈值和规则）"""

    def __init__(self):
        self.metrics: Dict[str, Any] = {}
        self.thresholds: Dict[str, float] = {}
        self.alert_rules: Dict[str, Dict] = {}
        self._lock = threading.Lock()
        self._alert_callbacks: List[Callable] = []

    def set_threshold(self, metric_name: str, threshold: float):
        self.thresholds[metric_name] = threshold

    def add_alert_rule(self, name: str, metric: str, threshold: float,
                       severity: str = "warning", duration: int = 60):
        """添加告警规则"""
        with self._lock:
            self.alert_rules[name] = {
                "metric": metric,
                "threshold": threshold,
                "severity": severity,
                "duration": duration,
                "firing_since": None,
                "state": "normal"  # normal, pending, firing
            }

    def register_alert_callback(self, callback: Callable):
        """注册告警回调"""
        self._alert_callbacks.append(callback)

    def record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        with self._lock:
            if name not in self.metrics:
                self.metrics[name] = []

            self.metrics[name].append({
                "value": value,
                "tags": tags or {},
                "timestamp": time.time()
            })

            # 检查阈值告警
            threshold = self.thresholds.get(name)
            if threshold and value > threshold:
                app_logger.warning(
                    f"指标告警: {name} = {value:.2f} (阈值: {threshold})"
                )

            # 检查规则告警
            self._evaluate_alert_rules(name, value)

    def _evaluate_alert_rules(self, metric_name: str, value: float):
        """评估告警规则"""
        now = time.time()
        for rule_name, rule in self.alert_rules.items():
            if rule["metric"] != metric_name:
                continue

            if value > rule["threshold"]:
                if rule["state"] == "normal":
                    rule["firing_since"] = now
                    rule["state"] = "pending"
                elif rule["state"] == "pending":
                    if now - rule["firing_since"] >= rule["duration"]:
                        rule["state"] = "firing"
                        alert_firing_total.labels(
                            alert_name=rule_name,
                            severity=rule["severity"]
                        ).inc()
                        app_logger.error(
                            f"告警触发: {rule_name} | {metric_name}={value:.2f} > {rule['threshold']}"
                        )
                        # 触发回调
                        for callback in self._alert_callbacks:
                            try:
                                callback(rule_name, rule, value)
                            except Exception:
                                pass
            else:
                if rule["state"] in ["pending", "firing"]:
                    app_logger.info(f"告警恢复: {rule_name}")
                rule["state"] = "normal"
                rule["firing_since"] = None

    def get_metrics_summary(self) -> Dict[str, Any]:
        with self._lock:
            summary = {}
            for name, values in self.metrics.items():
                if values:
                    recent_values = [v["value"] for v in values[-100:]]
                    summary[name] = {
                        "count": len(values),
                        "avg": sum(recent_values) / len(recent_values),
                        "min": min(recent_values),
                        "max": max(recent_values),
                        "latest": recent_values[-1],
                        "p95": sorted(recent_values)[int(len(recent_values) * 0.95)] if len(recent_values) > 1 else recent_values[0]
                    }
            return summary

    def get_alerting_metrics(self) -> Dict[str, Any]:
        alerts = {}
        with self._lock:
            for name, threshold in self.thresholds.items():
                if name in self.metrics and self.metrics[name]:
                    latest = self.metrics[name][-1]["value"]
                    if latest > threshold:
                        alerts[name] = {
                            "value": latest,
                            "threshold": threshold,
                            "severity": "warning" if latest < threshold * 1.5 else "critical"
                        }
            # 规则告警
            for rule_name, rule in self.alert_rules.items():
                if rule["state"] == "firing":
                    alerts[rule_name] = {
                        "metric": rule["metric"],
                        "threshold": rule["threshold"],
                        "severity": rule["severity"],
                        "state": "firing"
                    }
        return alerts

    def get_alert_rules(self) -> Dict[str, Any]:
        with self._lock:
            return {k: {**v, "firing_since": v["firing_since"]} for k, v in self.alert_rules.items()}


performance_monitor = PerformanceMonitor()


# ========== 系统资源监控 ==========

def update_system_metrics():
    try:
        import psutil

        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        system_memory_usage_bytes.labels(type="rss").set(mem_info.rss)
        system_memory_usage_bytes.labels(type="vms").set(mem_info.vms)

        cpu_percent = process.cpu_percent(interval=None)
        system_cpu_usage_percent.set(cpu_percent)

        try:
            open_files = len(process.open_files())
            system_open_files.set(open_files)
        except (psutil.AccessDenied, OSError):
            pass

    except ImportError:
        pass


def init_app_info(version: str = "1.0.0", environment: str = "production"):
    app_info.info({
        "version": version,
        "environment": environment,
        "python_version": os.sys.version.split()[0]
    })


# ========== 性能追踪装饰器 ==========

def track_performance(metric_name: str, tags: Optional[Dict[str, str]] = None):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.time() - start
                performance_monitor.record_metric(metric_name, duration, tags)
        return wrapper
    return decorator


def track_async_performance(metric_name: str, tags: Optional[Dict[str, str]] = None):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            try:
                return await func(*args, **kwargs)
            finally:
                duration = time.time() - start
                performance_monitor.record_metric(metric_name, duration, tags)
        return wrapper
    return decorator


# ========== 分布式追踪上下文 ==========

class TracingContext:
    """分布式追踪上下文管理"""

    _local = threading.local()

    @classmethod
    def get_trace_id(cls) -> Optional[str]:
        return getattr(cls._local, 'trace_id', None)

    @classmethod
    def set_trace_id(cls, trace_id: str):
        cls._local.trace_id = trace_id

    @classmethod
    def get_span_id(cls) -> Optional[str]:
        return getattr(cls._local, 'span_id', None)

    @classmethod
    def set_span_id(cls, span_id: str):
        cls._local.span_id = span_id

    @classmethod
    def clear(cls):
        cls._local.trace_id = None
        cls._local.span_id = None


# ========== 性能剖析工具 ==========

class Profiler:
    """简单性能剖析器"""

    def __init__(self):
        self.profiles = {}
        self._lock = threading.Lock()

    def profile(self, name: str):
        """上下文管理器用于性能剖析"""
        return _ProfileContext(self, name)

    def record(self, name: str, duration: float):
        with self._lock:
            if name not in self.profiles:
                self.profiles[name] = []
            self.profiles[name].append(duration)
            # 只保留最近1000次
            if len(self.profiles[name]) > 1000:
                self.profiles[name] = self.profiles[name][-1000:]

    def get_summary(self) -> Dict[str, Any]:
        with self._lock:
            summary = {}
            for name, durations in self.profiles.items():
                if durations:
                    sorted_d = sorted(durations)
                    summary[name] = {
                        "count": len(durations),
                        "avg": sum(durations) / len(durations),
                        "min": min(durations),
                        "max": max(durations),
                        "p50": sorted_d[int(len(sorted_d) * 0.5)],
                        "p95": sorted_d[int(len(sorted_d) * 0.95)],
                        "p99": sorted_d[int(len(sorted_d) * 0.99)] if len(sorted_d) > 100 else sorted_d[-1]
                    }
            return summary


class _ProfileContext:
    def __init__(self, profiler: Profiler, name: str):
        self.profiler = profiler
        self.name = name
        self.start = None

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start
        self.profiler.record(self.name, duration)


profiler = Profiler()
