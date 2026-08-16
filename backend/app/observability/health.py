import time
import os
from typing import Any, Dict, Optional
from datetime import datetime, timezone

from app.logging.logger import get_logger

logger = get_logger(__name__)

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False

_start_time = time.time()


def get_platform_health() -> Dict[str, Any]:
    health = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": round(time.time() - _start_time, 2),
    }
    return health


def check_mongodb() -> Dict[str, Any]:
    try:
        from app.database.mongodb import ping_mongodb
        start = time.perf_counter()
        ping_mongodb()
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {"status": "connected", "latency_ms": round(elapsed_ms, 2)}
    except Exception as exc:
        logger.error("[Health] MongoDB check failed: %s", exc)
        return {"status": "disconnected", "error": str(exc)}


def check_duckdb() -> Dict[str, Any]:
    try:
        from app.database.duckdb_engine import DuckDBEngine
        start = time.perf_counter()
        conn = DuckDBEngine.get_connection()
        conn.execute("SELECT 1")
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {
            "status": "connected",
            "latency_ms": round(elapsed_ms, 2),
            "stats": DuckDBEngine.get_stats(),
        }
    except Exception as exc:
        logger.error("[Health] DuckDB check failed: %s", exc)
        return {"status": "disconnected", "error": str(exc)}


def check_groq() -> Dict[str, Any]:
    try:
        from app.ai.groq_client import GroqClient
        client = GroqClient()
        if client.is_configured():
            return {"status": "configured", "model": "llama-3.3-70b-versatile"}
        return {"status": "unconfigured", "reason": "GROQ_API_KEY not set"}
    except Exception as exc:
        logger.error("[Health] Groq check failed: %s", exc)
        return {"status": "error", "error": str(exc)}


def check_cache() -> Dict[str, Any]:
    cache_status = {}
    try:
        from app.cache.memory_cache import TTLCache, QueryResultCache
        cache_status["memory"] = {
            "ttl_cache": TTLCache.get_instance("health_check", maxsize=1, ttl=1).stats(),
            "query_result": QueryResultCache.stats(),
        }
    except Exception as exc:
        cache_status["memory"] = {"status": "error", "error": str(exc)}

    try:
        from app.cache.redis_cache import RedisCacheManager
        cache_status["redis"] = RedisCacheManager.stats()
    except Exception as exc:
        cache_status["redis"] = {"status": "unavailable", "error": str(exc)}

    return cache_status


def check_storage() -> Dict[str, Any]:
    if not _PSUTIL_AVAILABLE:
        return {"status": "unavailable", "reason": "psutil not installed"}
    try:
        from app.database.storage import STORAGE_DIR
        disk = psutil.disk_usage(str(STORAGE_DIR))
        return {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "percent_used": disk.percent,
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def check_resources() -> Dict[str, Any]:
    if not _PSUTIL_AVAILABLE:
        return {"status": "unavailable", "reason": "psutil not installed"}
    try:
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        return {
            "memory_mb": round(mem_info.rss / (1024**2), 2),
            "cpu_percent": process.cpu_percent(interval=0.1),
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def get_system_metrics() -> Dict[str, Any]:
    try:
        from app.main import _app_metrics
        with _app_metrics["_lock"]:
            total = _app_metrics["total_requests"]
            avg_ms = _app_metrics["total_latency_ms"] / total if total > 0 else 0.0
            return {
                "total_requests": total,
                "total_errors": _app_metrics["total_errors"],
                "avg_latency_ms": round(avg_ms, 2),
                "error_rate": round(_app_metrics["total_errors"] / total, 4) if total > 0 else 0.0,
                "endpoints": dict(_app_metrics["endpoint_times"]),
            }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def get_full_health() -> Dict[str, Any]:
    overall = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": round(time.time() - _start_time, 2),
    }

    mongo = check_mongodb()
    duckdb = check_duckdb()
    groq = check_groq()
    cache = check_cache()
    storage = check_storage()
    resources = check_resources()
    metrics = get_system_metrics()

    overall["services"] = {
        "mongodb": mongo,
        "duckdb": duckdb,
        "groq": groq,
        "cache": cache,
        "storage": storage,
    }
    overall["resources"] = resources
    overall["metrics"] = metrics

    if mongo.get("status") != "connected" or duckdb.get("status") != "connected":
        overall["status"] = "degraded"

    if storage.get("percent_used", 0) > 90:
        overall["status"] = "degraded"
        overall["warnings"] = overall.get("warnings", [])
        overall["warnings"].append("Storage usage above 90%")

    return overall
