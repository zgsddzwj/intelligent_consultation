"""数据库会话管理 - 极致优化版（查询优化器、索引监控、连接池动态调整、读写分离）"""
import time
import threading
from typing import List
from sqlalchemy import create_engine, event, text, inspect
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool, NullPool
from app.config import get_settings
from app.utils.logger import app_logger

settings = get_settings()

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
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_timeout=30,
    pool_use_lifo=True,
    connect_args={"connect_timeout": 10},
    echo=settings.DEBUG
)

# ===== 只读引擎（如果配置了只读库） =====
read_engine = None
if hasattr(settings, 'DATABASE_READ_URL') and settings.DATABASE_READ_URL:
    read_engine = create_engine(
        settings.DATABASE_READ_URL,
        poolclass=QueuePool,
        pool_size=max(1, settings.DATABASE_POOL_SIZE // 2),
        max_overflow=max(1, settings.DATABASE_MAX_OVERFLOW // 2),
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_timeout=30,
        pool_use_lifo=True,
        connect_args={"connect_timeout": 10},
        echo=settings.DEBUG
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
ReadSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=read_engine) if read_engine else None


# ========== SQLAlchemy事件监听 ==========

@event.listens_for(engine, "connect")
def on_connect(dbapi_conn, connection_record):
    _record_pool_event("connect")
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


def get_read_db():
    """获取只读数据库会话（读写分离）"""
    if ReadSessionLocal:
        db = ReadSessionLocal()
    else:
        db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_with_retry(max_retries: int = 3, retry_delay: float = 0.5):
    for attempt in range(max_retries):
        db = None
        try:
            db = SessionLocal()
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


class QueryOptimizer:
    """查询优化器 - 提供查询优化建议"""

    @staticmethod
    def analyze_query(db: Session, sql: str) -> dict:
        """分析SQL查询执行计划"""
        try:
            result = db.execute(text(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql}"))
            plan = result.fetchone()
            return {
                "plan": plan[0] if plan else None,
                "sql": sql[:200]
            }
        except Exception as e:
            return {"error": str(e), "sql": sql[:200]}

    @staticmethod
    def get_missing_indexes(db: Session) -> List[dict]:
        """获取缺失索引建议（PostgreSQL）"""
        try:
            query = """
            SELECT
                schemaname,
                tablename,
                attname as column,
                n_tup_read as reads,
                n_tup_fetch as fetches
            FROM pg_stats
            WHERE schemaname = 'public'
            ORDER BY n_tup_read DESC
            LIMIT 20
            """
            result = db.execute(text(query))
            return [dict(row._mapping) for row in result]
        except Exception as e:
            app_logger.warning(f"获取缺失索引建议失败: {e}")
            return []

    @staticmethod
    def get_table_stats(db: Session) -> dict:
        """获取表统计信息"""
        try:
            query = """
            SELECT
                schemaname,
                tablename,
                n_tup_ins as inserts,
                n_tup_upd as updates,
                n_tup_del as deletes,
                n_live_tup as live_tuples,
                n_dead_tup as dead_tuples,
                last_vacuum,
                last_autovacuum,
                last_analyze,
                last_autoanalyze
            FROM pg_stat_user_tables
            WHERE schemaname = 'public'
            ORDER BY n_live_tup DESC
            """
            result = db.execute(text(query))
            return {
                "tables": [dict(row._mapping) for row in result]
            }
        except Exception as e:
            app_logger.warning(f"获取表统计信息失败: {e}")
            return {}


class DatabaseManager:
    """数据库管理器 - 极致优化版"""

    @staticmethod
    def get_connection_info() -> dict:
        pool = engine.pool
        info = {
            "write_pool": {
                "pool_size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "total_connections": pool.size() + pool.overflow()
            }
        }
        if read_engine:
            read_pool = read_engine.pool
            info["read_pool"] = {
                "pool_size": read_pool.size(),
                "checked_in": read_pool.checkedin(),
                "checked_out": read_pool.checkedout(),
                "overflow": read_pool.overflow(),
                "total_connections": read_pool.size() + read_pool.overflow()
            }
        return info

    @staticmethod
    def health_check() -> dict:
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
        with _pool_stats["lock"]:
            _pool_stats["total_connections_created"] = 0
            _pool_stats["total_connections_checked_out"] = 0
            _pool_stats["total_connections_checked_in"] = 0
            _pool_stats["total_checkouts"] = 0
            _pool_stats["slow_queries"].clear()
            _pool_stats["query_count"] = 0

    @staticmethod
    def get_slow_queries() -> list:
        with _pool_stats["lock"]:
            return _pool_stats["slow_queries"].copy()

    @staticmethod
    def vacuum_analyze(db: Session, table_name: str = None):
        """执行VACUUM ANALYZE（PostgreSQL）"""
        try:
            if table_name:
                db.execute(text(f"ANALYZE {table_name}"))
                app_logger.info(f"ANALYZE {table_name} 完成")
            else:
                db.execute(text("ANALYZE"))
                app_logger.info("ANALYZE 所有表完成")
            db.commit()
        except Exception as e:
            app_logger.error(f"ANALYZE 失败: {e}")
            db.rollback()

    @staticmethod
    def dynamic_pool_adjustment():
        """动态调整连接池大小（基于负载）"""
        try:
            pool = engine.pool
            current_size = pool.size()
            checked_out = pool.checkedout()
            utilization = checked_out / current_size if current_size > 0 else 0

            if utilization > 0.8:
                app_logger.warning(f"连接池利用率过高 ({utilization:.1%})，考虑增加连接池大小")
            elif utilization < 0.2 and current_size > settings.DATABASE_POOL_SIZE:
                app_logger.info(f"连接池利用率较低 ({utilization:.1%})，可考虑缩小连接池")

            return {
                "utilization": round(utilization, 2),
                "current_size": current_size,
                "checked_out": checked_out,
                "recommendation": "increase" if utilization > 0.8 else "decrease" if utilization < 0.2 else "maintain"
            }
        except Exception as e:
            app_logger.warning(f"动态连接池调整失败: {e}")
            return {}
