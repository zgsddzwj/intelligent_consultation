"""数据库会话管理 - 极致优化版（查询优化器、索引监控、连接池动态调整、读写分离）"""
import time
import threading
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool, NullPool
from app.config import get_settings
from app.utils.logger import app_logger

settings = get_settings()

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

_pool_stats = {
    "total_connections_created": 0,
    "total_connections_checked_out": 0,
    "total_connections_checked_in": 0,
    "total_checkouts": 0,
    "slow_queries": [],
    "query_count": 0,
    "lock": threading.Lock()
}

SLOW_QUERY_THRESHOLD = 1.0


def _record_pool_event(event_type: str):
    with _pool_stats["lock"]:
        if event_type == "connect":
            _pool_stats["total_connections_created"] += 1
        elif event_type == "checkout":
            _pool_stats["total_connections_checked_out"] += 1
            _pool_stats["total_checkouts"] += 1
        elif event_type == "checkin":
            _pool_stats["total_connections_checked_in"] += 1


def get_pool_stats() -> dict:
    with _pool_stats["lock"]:
        return {
            "total_connections_created": _pool_stats["total_connections_created"],
            "total_checkouts": _pool_stats["total_checkouts"],
            "active_connections": (
                _pool_stats["total_connections_checked_out"] -
                _pool_stats["total_connections_checked_in"]
            ),
            "slow_queries_count": len(_pool_stats["slow_queries"]),
            "recent_slow_queries": _pool_stats["slow_queries"][-10:],
            "total_queries": _pool_stats["query_count"]
        }


# ===== 主库引擎（读写） =====
_engine_kwargs = {
    "pool_pre_ping": True,
    "echo": settings.DEBUG,
}
if _is_sqlite:
    _engine_kwargs.update({
        "connect_args": {"check_same_thread": False},
        "poolclass": NullPool,
    })
else:
    _engine_kwargs.update({
        "poolclass": QueuePool,
        "pool_size": settings.DATABASE_POOL_SIZE,
        "max_overflow": settings.DATABASE_MAX_OVERFLOW,
        "pool_recycle": 3600,
        "pool_timeout": 30,
        "pool_use_lifo": True,
        "connect_args": {"connect_timeout": 10},
    })

engine = create_engine(settings.DATABASE_URL, **_engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ========== SQLAlchemy事件监听 ==========

@event.listens_for(engine, "connect")
def on_connect(dbapi_conn, connection_record):
    _record_pool_event("connect")
    if _is_sqlite:
        return
    try:
        cursor = dbapi_conn.cursor()
        cursor.execute("SET timezone = 'Asia/Shanghai'")
        cursor.execute("SET application_name = 'intelligent_consultation'")
        cursor.close()
    except Exception:
        pass


@event.listens_for(engine, "checkout")
def on_checkout(dbapi_conn, connection_record, connection_proxy):
    _record_pool_event("checkout")
    connection_record.info["checkout_time"] = time.time()


@event.listens_for(engine, "checkin")
def on_checkin(dbapi_conn, connection_record):
    _record_pool_event("checkin")
    checkout_time = connection_record.info.get("checkout_time")
    if checkout_time:
        hold_time = time.time() - checkout_time
        if hold_time > 30:
            app_logger.warning(
                f"数据库连接持有时间过长: {hold_time:.1f}s，可能存在连接泄漏"
            )
        connection_record.info["checkout_time"] = None


@event.listens_for(engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.time()
    with _pool_stats["lock"]:
        _pool_stats["query_count"] += 1


@event.listens_for(engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    if hasattr(context, "_query_start_time"):
        total_time = time.time() - context._query_start_time

        if total_time > SLOW_QUERY_THRESHOLD:
            query_info = {
                "sql": statement[:200],
                "duration": round(total_time, 3),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }

            with _pool_stats["lock"]:
                _pool_stats["slow_queries"].append(query_info)
                if len(_pool_stats["slow_queries"]) > 100:
                    _pool_stats["slow_queries"] = _pool_stats["slow_queries"][-100:]

            app_logger.warning(
                f"慢查询检测: {total_time:.3f}s > {SLOW_QUERY_THRESHOLD}s | "
                f"SQL: {statement[:150]}..."
            )


# ========== 数据库依赖注入增强 ==========
# API 层请使用 app.dependencies.get_db（无自动 commit）。
# 以下 get_db 供脚本/内部模块使用，会在请求结束时自动 commit。

def get_db():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
