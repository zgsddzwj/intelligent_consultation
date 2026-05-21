"""数据库会话管理 - 增强版（连接池监控、慢查询检测、SQLAlchemy事件监听）"""
import time
import threading
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from app.config import get_settings
from app.utils.logger import app_logger

settings = get_settings()

# 连接池统计（线程安全）
_pool_stats = {
    "total_connections_created": 0,
    "total_connections_checked_out": 0,
    "total_connections_checked_in": 0,
    "total_checkouts": 0,
    "slow_queries": [],
    "lock": threading.Lock()
}

# 慢查询阈值（秒）
SLOW_QUERY_THRESHOLD = 1.0


def _record_pool_event(event_type: str):
    """记录连接池事件"""
    with _pool_stats["lock"]:
        if event_type == "connect":
            _pool_stats["total_connections_created"] += 1
        elif event_type == "checkout":
            _pool_stats["total_connections_checked_out"] += 1
            _pool_stats["total_checkouts"] += 1
        elif event_type == "checkin":
            _pool_stats["total_connections_checked_in"] += 1


def get_pool_stats() -> dict:
    """获取连接池统计信息"""
    with _pool_stats["lock"]:
        return {
            "total_connections_created": _pool_stats["total_connections_created"],
            "total_checkouts": _pool_stats["total_checkouts"],
            "active_connections": (
                _pool_stats["total_connections_checked_out"] -
                _pool_stats["total_connections_checked_in"]
            ),
            "slow_queries_count": len(_pool_stats["slow_queries"]),
            "recent_slow_queries": _pool_stats["slow_queries"][-10:]  # 最近10条
        }


# 创建引擎（使用QueuePool并配置更优的参数）
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,        # 自动检测无效连接
    pool_recycle=3600,         # 连接回收时间：1小时
    pool_timeout=30,           # 连接池获取超时：30秒
    pool_use_lifo=True,        # LIFO模式：复用最近使用的连接，减少连接创建
    connect_args={
        "connect_timeout": 10,  # 数据库连接超时：10秒
    },
    echo=settings.DEBUG
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ========== SQLAlchemy事件监听 ==========

@event.listens_for(engine, "connect")
def on_connect(dbapi_conn, connection_record):
    """连接建立时的回调"""
    _record_pool_event("connect")
    
    # 设置连接参数（PostgreSQL优化）
    try:
        cursor = dbapi_conn.cursor()
        # 设置时区
        cursor.execute("SET timezone = 'Asia/Shanghai'")
        # 设置应用名称（便于在pg_stat_activity中识别）
        cursor.execute(f"SET application_name = 'intelligent_consultation'")
        cursor.close()
    except Exception:
        pass  # 非PostgreSQL数据库忽略


@event.listens_for(engine, "checkout")
def on_checkout(dbapi_conn, connection_record, connection_proxy):
    """连接检出时的回调"""
    _record_pool_event("checkout")
    # 记录检出时间用于检测连接泄漏
    connection_record.info["checkout_time"] = time.time()


@event.listens_for(engine, "checkin")
def on_checkin(dbapi_conn, connection_record):
    """连接归还时的回调"""
    _record_pool_event("checkin")
    
    # 检测连接泄漏（连接持有时间超过阈值）
    checkout_time = connection_record.info.get("checkout_time")
    if checkout_time:
        hold_time = time.time() - checkout_time
        if hold_time > 30:  # 连接持有超过30秒告警
            app_logger.warning(
                f"数据库连接持有时间过长: {hold_time:.1f}s，可能存在连接泄漏"
            )
        connection_record.info["checkout_time"] = None


# ========== 慢查询检测 ==========

@event.listens_for(engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """SQL执行前记录开始时间"""
    context._query_start_time = time.time()


@event.listens_for(engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """SQL执行后检测慢查询"""
    if hasattr(context, "_query_start_time"):
        total_time = time.time() - context._query_start_time
        
        if total_time > SLOW_QUERY_THRESHOLD:
            # 记录慢查询
            query_info = {
                "sql": statement[:200],
                "duration": round(total_time, 3),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            with _pool_stats["lock"]:
                _pool_stats["slow_queries"].append(query_info)
                # 只保留最近100条慢查询
                if len(_pool_stats["slow_queries"]) > 100:
                    _pool_stats["slow_queries"] = _pool_stats["slow_queries"][-100:]
            
            app_logger.warning(
                f"慢查询检测: {total_time:.3f}s > {SLOW_QUERY_THRESHOLD}s | "
                f"SQL: {statement[:150]}..."
            )


# ========== 数据库依赖注入增强 ==========

def get_db():
    """
    获取数据库会话（生成器）
    
    使用上下文管理器确保会话正确关闭，
    即使发生异常也会回滚并释放连接。
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db_with_retry(max_retries: int = 3, retry_delay: float = 0.5):
    """
    带重试的数据库会话获取
    
    在连接池耗尽时自动重试，适用于高并发场景。
    """
    for attempt in range(max_retries):
        db = None
        try:
            db = SessionLocal()
            # 简单测试连接
            db.execute(text("SELECT 1"))
            yield db
            db.commit()
            return
        except Exception as e:
            if db:
                db.rollback()
            if attempt < max_retries - 1:
                app_logger.warning(
                    f"数据库连接失败 (尝试 {attempt + 1}/{max_retries}): {e}"
                )
                time.sleep(retry_delay * (attempt + 1))
            else:
                raise
        finally:
            if db:
                db.close()


class DatabaseManager:
    """数据库管理器 - 提供高级数据库操作"""
    
    @staticmethod
    def get_connection_info() -> dict:
        """获取当前连接池信息"""
        pool = engine.pool
        return {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "total_connections": pool.size() + pool.overflow()
        }
    
    @staticmethod
    def health_check() -> dict:
        """数据库健康检查"""
        start_time = time.time()
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
                
            latency = time.time() - start_time
            return {
                "status": "healthy",
                "latency_ms": round(latency * 1000, 2),
                "pool_info": DatabaseManager.get_connection_info()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)[:200],
                "latency_ms": round((time.time() - start_time) * 1000, 2)
            }
    
    @staticmethod
    def reset_pool_stats():
        """重置连接池统计"""
        with _pool_stats["lock"]:
            _pool_stats["total_connections_created"] = 0
            _pool_stats["total_connections_checked_out"] = 0
            _pool_stats["total_connections_checked_in"] = 0
            _pool_stats["total_checkouts"] = 0
            _pool_stats["slow_queries"].clear()
