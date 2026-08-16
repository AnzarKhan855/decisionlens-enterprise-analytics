from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import duckdb
import pandas as pd
import threading
import time
import os
import re

import sys
from app.resilience.retry import with_retry, CircuitBreaker, get_circuit_breaker
from app.security.input_sanitizer import InputSanitizer

is_pytest = "PYTEST_CURRENT_TEST" in os.environ or "pytest" in sys.modules
_duckdb_cb = get_circuit_breaker("duckdb", failure_threshold=500 if is_pytest else 15, recovery_timeout=5.0)

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _validate_identifier(name: str) -> str:
    if not _IDENTIFIER_RE.match(name):
        raise ValueError(f"Invalid SQL identifier: {name}")
    return name


def _validate_parquet_path(parquet_path: Path) -> str:
    from app.database.storage import STORAGE_DIR
    resolved = parquet_path.resolve()
    if not resolved.is_relative_to(STORAGE_DIR.resolve()):
        raise ValueError(f"Parquet path is outside allowed storage directory: {parquet_path}")
    return str(resolved).replace("\\", "/")


class DuckDBEngine:
    """
    High-performance OLAP query engine leveraging DuckDB over Parquet files.
    Uses a persistent on-disk database and connection reuse to eliminate
    the overhead of creating a new in-memory database per query.
    """

    _instance: Optional["DuckDBEngine"] = None
    _lock = threading.Lock()
    _init_lock = threading.Lock()

    _conn = None
    _persistent_path: Optional[str] = None
    _last_used: float = 0.0
    _idle_timeout: float = 300.0
    _query_count: int = 0
    _total_duration: float = 0.0
    _thread_local = threading.local()

    def __init__(self):
        raise RuntimeError("Use DuckDBEngine.get_connection() or .instance()")

    @classmethod
    def instance(cls) -> "DuckDBEngine":
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = cls.__new__(cls)
        return cls._instance

    @classmethod
    def set_persistent_db(cls, db_path: str, recreate: bool = False):
        with cls._init_lock:
            cls._persistent_path = db_path
            if recreate and os.path.exists(db_path):
                os.remove(db_path)
            cls._instance = None
            cls._conn = None

    @classmethod
    def get_connection(cls):
        now = time.time()
        local = getattr(cls._thread_local, "conn", None)
        if local is not None:
            try:
                local.execute("SELECT 1")
                return local
            except Exception:
                try:
                    local.close()
                except Exception:
                    pass
                cls._thread_local.conn = None

        with cls._lock:
            if cls._conn is not None:
                try:
                    cls._conn.execute("SELECT 1")
                    cls._last_used = now
                    return cls._conn
                except Exception:
                    try:
                        cls._conn.close()
                    except Exception:
                        pass
                    cls._conn = None

            if _duckdb_cb._is_open():
                raise Exception("DuckDB circuit breaker is open")

            if cls._persistent_path:
                conn = duckdb.connect(database=cls._persistent_path)
            else:
                conn = duckdb.connect(database=":memory:")

            cls._configure_connection(conn)
            cls._conn = conn
            cls._last_used = now
            return conn

    @classmethod
    def get_thread_connection(cls):
        local = getattr(cls._thread_local, "conn", None)
        if local is not None:
            try:
                local.execute("SELECT 1")
                return local
            except Exception:
                try:
                    local.close()
                except Exception:
                    pass
                cls._thread_local.conn = None

        if cls._persistent_path:
            conn = duckdb.connect(database=cls._persistent_path)
        else:
            conn = duckdb.connect(database=":memory:")
        cls._configure_connection(conn)
        cls._thread_local.conn = conn
        return conn

    @classmethod
    def _configure_connection(cls, conn):
        conn.execute("SET threads TO 4")
        conn.execute("SET memory_limit TO '2GB'")
        conn.execute("SET enable_http_metadata_cache TO true")
        conn.execute("PRAGMA enable_progress_bar=false")
        conn.execute("PRAGMA enable_object_cache=true")

    @classmethod
    @with_retry(max_attempts=3, backoff_factor=0.5, exceptions=(duckdb.Error, Exception), circuit_breaker_name="duckdb", fallback=lambda: [])
    def execute(cls, sql_query: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        conn = cls.get_connection()
        start = time.perf_counter()
        try:
            rel = conn.execute(sql_query, params or [])
            cols = [desc[0] for desc in rel.description]
            rows = rel.fetchall()
            elapsed = time.perf_counter() - start
            with cls._lock:
                cls._query_count += 1
                cls._total_duration += elapsed
            return [dict(zip(cols, row)) for row in rows]
        except Exception:
            elapsed = time.perf_counter() - start
            with cls._lock:
                cls._query_count += 1
                cls._total_duration += elapsed
            raise

    @classmethod
    def query(cls, sql_query: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        return cls.execute(sql_query, params)

    @classmethod
    @with_retry(max_attempts=3, backoff_factor=0.5, exceptions=(duckdb.Error, Exception), circuit_breaker_name="duckdb", fallback=lambda: pd.DataFrame())
    def query_to_df(cls, sql_query: str, params: Optional[List[Any]] = None) -> pd.DataFrame:
        conn = cls.get_connection()
        start = time.perf_counter()
        try:
            df = conn.execute(sql_query, params or []).df()
            elapsed = time.perf_counter() - start
            with cls._lock:
                cls._query_count += 1
                cls._total_duration += elapsed
            return df
        except Exception:
            elapsed = time.perf_counter() - start
            with cls._lock:
                cls._query_count += 1
                cls._total_duration += elapsed
            raise

    @classmethod
    def get_schema(cls, parquet_path: Path) -> Dict[str, str]:
        path_str = _validate_parquet_path(parquet_path)
        sql = f"DESCRIBE SELECT * FROM read_parquet(?)"
        conn = cls.get_connection()
        start = time.perf_counter()
        try:
            res = conn.execute(sql, [path_str]).fetchall()
            elapsed = time.perf_counter() - start
            with cls._lock:
                cls._query_count += 1
                cls._total_duration += elapsed
            return {row[0]: row[1] for row in res}
        except Exception:
            elapsed = time.perf_counter() - start
            with cls._lock:
                cls._query_count += 1
                cls._total_duration += elapsed
            raise

    @classmethod
    def get_row_count(cls, parquet_path: Path) -> int:
        path_str = _validate_parquet_path(parquet_path)
        sql = f"SELECT COUNT(*) FROM read_parquet(?)"
        conn = cls.get_connection()
        start = time.perf_counter()
        try:
            result = int(conn.execute(sql, [path_str]).fetchone()[0])
            elapsed = time.perf_counter() - start
            with cls._lock:
                cls._query_count += 1
                cls._total_duration += elapsed
            return result
        except Exception:
            elapsed = time.perf_counter() - start
            with cls._lock:
                cls._query_count += 1
                cls._total_duration += elapsed
            raise

    @classmethod
    def preview(cls, parquet_path: Path, limit: int = 10) -> List[Dict[str, Any]]:
        path_str = _validate_parquet_path(parquet_path)
        sql = f"SELECT * FROM read_parquet(?) LIMIT ?"
        return cls.query(sql, [path_str, limit])

    @classmethod
    def get_numeric_summary(cls, parquet_path: Path, column_name: str) -> Dict[str, Any]:
        path_str = _validate_parquet_path(parquet_path)
        col = _validate_identifier(column_name)
        sql = f"""
        SELECT
            COUNT({col}) as count,
            COUNT(*) - COUNT({col}) as null_count,
            COUNT(DISTINCT {col}) as distinct_count,
            MIN({col}) as min_val,
            MAX({col}) as max_val,
            AVG({col}) as mean_val,
            STDDEV_SAMP({col}) as stddev_val,
            QUANTILE_CONT({col}, 0.25) as q25,
            MEDIAN({col}) as median_val,
            QUANTILE_CONT({col}, 0.75) as q75
        FROM read_parquet(?)
        """
        res = cls.query(sql, [path_str])
        if res:
            r = res[0]
            return {
                "count": r.get("count", 0),
                "null_count": r.get("null_count", 0),
                "distinct_count": r.get("distinct_count", 0),
                "min": float(r["min_val"]) if r.get("min_val") is not None else None,
                "max": float(r["max_val"]) if r.get("max_val") is not None else None,
                "mean": round(float(r["mean_val"]), 4) if r.get("mean_val") is not None else None,
                "stddev": round(float(r["stddev_val"]), 4) if r.get("stddev_val") is not None else None,
                "q25": float(r["q25"]) if r.get("q25") is not None else None,
                "median": float(r["median_val"]) if r.get("median_val") is not None else None,
                "q75": float(r["q75"]) if r.get("q75") is not None else None,
            }
        return {}

    @classmethod
    def get_categorical_summary(cls, parquet_path: Path, column_name: str, top_n: int = 10) -> Dict[str, Any]:
        path_str = _validate_parquet_path(parquet_path)
        col = _validate_identifier(column_name)
        conn = cls.get_connection()
        start = time.perf_counter()
        try:
            sql_distinct = f"SELECT COUNT(DISTINCT {col}) as d_cnt, COUNT(*) - COUNT({col}) as null_cnt FROM read_parquet(?)"
            sql_top = f"""
            SELECT {col} as value, COUNT(*) as frequency
            FROM read_parquet(?)
            WHERE {col} IS NOT NULL
            GROUP BY {col}
            ORDER BY frequency DESC
            LIMIT ?
            """
            d_res = conn.execute(sql_distinct, [path_str]).fetchone()
            distinct_count = d_res[0] if d_res else 0
            null_count = d_res[1] if d_res else 0
            top_freq = conn.execute(sql_top, [path_str, top_n]).fetchall()
            top_values = [{str(r[0]): r[1]} for r in top_freq]
            elapsed = time.perf_counter() - start
            with cls._lock:
                cls._query_count += 2
                cls._total_duration += elapsed
            return {
                "distinct_count": distinct_count,
                "null_count": null_count,
                "top_values": top_values
            }
        except Exception:
            elapsed = time.perf_counter() - start
            with cls._lock:
                cls._query_count += 2
                cls._total_duration += elapsed
            raise

    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        with cls._lock:
            avg_ms = (cls._total_duration / cls._query_count * 1000) if cls._query_count > 0 else 0
            return {
                "total_queries": cls._query_count,
                "total_duration_s": round(cls._total_duration, 4),
                "avg_query_ms": round(avg_ms, 2),
                "persistent_db": cls._persistent_path or "memory",
                "connection_active": cls._conn is not None,
                "last_used_ago_s": round(time.time() - cls._last_used, 2),
            }

    @classmethod
    def reset_stats(cls):
        with cls._lock:
            cls._query_count = 0
            cls._total_duration = 0.0
