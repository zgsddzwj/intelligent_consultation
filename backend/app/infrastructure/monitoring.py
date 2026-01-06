"""监控和指标收集"""
import time
from typing import Dict, Any, Optional
from functools import wraps
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
from app.utils.logger import app_logger

# Prometheus指标
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


def metrics_middleware(app):
    """Prometheus指标中间件"""
    @app.middleware("http")
    async def metrics_handler(request, call_next):
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time
        
        # 记录指标
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


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.metrics: Dict[str, Any] = {}
    
    def record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """记录指标"""
        if name not in self.metrics:
            self.metrics[name] = []
        self.metrics[name].append({
            "value": value,
            "tags": tags or {},
            "timestamp": time.time()
        })
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """获取指标摘要"""
        summary = {}
        for name, values in self.metrics.items():
            if values:
                summary[name] = {
                    "count": len(values),
                    "avg": sum(v["value"] for v in values) / len(values),
                    "min": min(v["value"] for v in values),
                    "max": max(v["value"] for v in values),
                    "latest": values[-1]["value"]
                }
        return summary


# 全局性能监控器
performance_monitor = PerformanceMonitor()

