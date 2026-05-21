"""监控和指标收集 - 增强版（自定义业务指标、内存/CPU监控、告警阈值）"""
import time
import os
import threading
from typing import Dict, Any, Optional
from functools import wraps
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST, Info
from starlette.responses import Response
from app.utils.logger import app_logger

# ========== Prometheus指标定义 ==========

# HTTP请求指标
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

# 活跃连接数
active_connections = Gauge(
    'active_connections',
    'Number of active connections'
)

# 数据库查询指标
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

# LLM请求指标
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
    ['model', 'type']  # type: input, output, total
)

llm_cost_total = Counter(
    'llm_cost_total',
    'Total LLM cost in currency units',
    ['model', 'currency']
)

llm_cache_hits_total = Counter(
    'llm_cache_hits_total',
    'Total LLM cache hits',
    ['cache_type']  # semantic, regular
)

# 缓存指标
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

# ========== 新增：系统资源指标 ==========

system_memory_usage_bytes = Gauge(
    'system_memory_usage_bytes',
    'Current memory usage in bytes',
    ['type']  # rss, vms
)

system_cpu_usage_percent = Gauge(
    'system_cpu_usage_percent',
    'Current CPU usage percentage'
)

system_open_files = Gauge(
    'system_open_files',
    'Number of open file descriptors'
)

# ========== 新增：业务指标 ==========

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

# 应用信息
app_info = Info(
    'application',
    'Application information'
)

# ========== 指标追踪函数 ==========

def track_http_request(method: str, endpoint: str, status_code: int, duration: float):
    """记录HTTP请求指标"""
    http_requests_total.labels(method=method, endpoint=endpoint, status=status_code).inc()
    http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)


def track_database_query(operation: str, table: str, duration: float):
    """记录数据库查询指标"""
    database_queries_total.labels(operation=operation, table=table).inc()
    database_query_duration_seconds.labels(operation=operation, table=table).observe(duration)


def track_llm_request(model: str, status: str, duration: float,
                     first_token_latency: Optional[float] = None,
                     input_tokens: Optional[int] = None,
                     output_tokens: Optional[int] = None,
                     cost: Optional[float] = None,
                     currency: str = "CNY"):
    """记录LLM请求指标"""
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
    """记录缓存命中"""
    cache_hits_total.labels(cache_type=cache_type).inc()


def track_cache_miss(cache_type: str):
    """记录缓存未命中"""
    cache_misses_total.labels(cache_type=cache_type).inc()


def track_llm_cache_hit(cache_type: str = "semantic"):
    """记录LLM缓存命中"""
    llm_cache_hits_total.labels(cache_type=cache_type).inc()


# ========== 新增：业务指标追踪 ==========

def track_consultation(agent_type: str, status: str, duration: float):
    """记录咨询请求指标"""
    consultation_requests_total.labels(agent_type=agent_type, status=status).inc()
    consultation_duration_seconds.labels(agent_type=agent_type).observe(duration)


def track_image_analysis(status: str):
    """记录图片分析请求指标"""
    image_analysis_requests_total.labels(status=status).inc()


def track_knowledge_graph_query(query_type: str, status: str):
    """记录知识图谱查询指标"""
    knowledge_graph_queries_total.labels(query_type=query_type, status=status).inc()


# ========== 中间件和工具函数 ==========

def metrics_middleware(app):
    """Prometheus指标中间件"""
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
    """获取Prometheus指标"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


# ========== 增强性能监控器 ==========

class PerformanceMonitor:
    """增强性能监控器（支持告警阈值）"""
    
    def __init__(self):
        self.metrics: Dict[str, Any] = {}
        self.thresholds: Dict[str, float] = {}
        self._lock = threading.Lock()
    
    def set_threshold(self, metric_name: str, threshold: float):
        """设置告警阈值"""
        self.thresholds[metric_name] = threshold
    
    def record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """记录指标（带告警检测）"""
        with self._lock:
            if name not in self.metrics:
                self.metrics[name] = []
            
            self.metrics[name].append({
                "value": value,
                "tags": tags or {},
                "timestamp": time.time()
            })
            
            # 检查是否超过阈值
            threshold = self.thresholds.get(name)
            if threshold and value > threshold:
                app_logger.warning(
                    f"指标告警: {name} = {value:.2f} (阈值: {threshold})"
                )
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """获取指标摘要"""
        with self._lock:
            summary = {}
            for name, values in self.metrics.items():
                if values:
                    recent_values = [v["value"] for v in values[-100:]]  # 最近100个值
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
        """获取超过阈值的指标"""
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
        return alerts


# 全局性能监控器
performance_monitor = PerformanceMonitor()


# ========== 系统资源监控 ==========

def update_system_metrics():
    """更新系统资源指标"""
    try:
        import psutil
        
        # 内存使用
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        system_memory_usage_bytes.labels(type="rss").set(mem_info.rss)
        system_memory_usage_bytes.labels(type="vms").set(mem_info.vms)
        
        # CPU使用
        cpu_percent = process.cpu_percent(interval=None)
        system_cpu_usage_percent.set(cpu_percent)
        
        # 打开文件数
        try:
            open_files = len(process.open_files())
            system_open_files.set(open_files)
        except (psutil.AccessDenied, OSError):
            pass
        
    except ImportError:
        pass  # psutil未安装时跳过


def init_app_info(version: str = "1.0.0", environment: str = "production"):
    """初始化应用信息指标"""
    app_info.info({
        "version": version,
        "environment": environment,
        "python_version": os.sys.version.split()[0]
    })


# ========== 性能追踪装饰器 ==========

def track_performance(metric_name: str, tags: Optional[Dict[str, str]] = None):
    """性能追踪装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.time() - start
                performance_monitor.record_metric(metric_name, duration, tags)
        return wrapper
    return decorator
