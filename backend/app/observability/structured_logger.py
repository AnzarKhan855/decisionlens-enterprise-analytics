import json
import logging
import sys
import os
import time
import uuid
import traceback
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, Optional


class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        if hasattr(record, "workspace_id"):
            log_entry["workspace_id"] = record.workspace_id
        if hasattr(record, "dataset_id"):
            log_entry["dataset_id"] = record.dataset_id
        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms
        if hasattr(record, "engine"):
            log_entry["engine"] = record.engine
        if hasattr(record, "cache_hit"):
            log_entry["cache_hit"] = record.cache_hit
        if hasattr(record, "llm_latency_ms"):
            log_entry["llm_latency_ms"] = record.llm_latency_ms
        if hasattr(record, "token_usage"):
            log_entry["token_usage"] = record.token_usage
        if hasattr(record, "mongo_query_ms"):
            log_entry["mongo_query_ms"] = record.mongo_query_ms
        if hasattr(record, "duckdb_query_ms"):
            log_entry["duckdb_query_ms"] = record.duckdb_query_ms
        if hasattr(record, "memory_mb"):
            log_entry["memory_mb"] = record.memory_mb
        if hasattr(record, "cpu_percent"):
            log_entry["cpu_percent"] = record.cpu_percent

        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        return json.dumps(log_entry, default=str)


_global_logger: Optional[logging.Logger] = None
_request_id_var = {}


def _get_request_id() -> str:
    import threading
    tid = threading.current_thread().ident
    if tid not in _request_id_var:
        _request_id_var[tid] = str(uuid.uuid4())
    return _request_id_var[tid]


def set_request_id(request_id: str) -> None:
    import threading
    _request_id_var[threading.current_thread().ident] = request_id


def get_request_id() -> str:
    return _get_request_id()


def get_logger(name: str) -> logging.Logger:
    global _global_logger
    if _global_logger is not None:
        return logging.getLogger(name)

    logger = logging.getLogger("decisionlens")
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    formatter = StructuredFormatter()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    os.makedirs(log_dir, exist_ok=True)
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "decisionlens.json.log"),
        maxBytes=20 * 1024 * 1024,
        backupCount=10,
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    _global_logger = logger
    return logger


def log_with_context(
    level: int,
    message: str,
    *,
    request_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    dataset_id: Optional[str] = None,
    duration_ms: Optional[float] = None,
    engine: Optional[str] = None,
    cache_hit: Optional[bool] = None,
    llm_latency_ms: Optional[float] = None,
    token_usage: Optional[Dict[str, Any]] = None,
    mongo_query_ms: Optional[float] = None,
    duckdb_query_ms: Optional[float] = None,
    memory_mb: Optional[float] = None,
    cpu_percent: Optional[float] = None,
    exc_info: bool = False,
) -> None:
    logger = get_logger("decisionlens")
    extra = {
        "request_id": request_id or _get_request_id(),
        "workspace_id": workspace_id,
        "dataset_id": dataset_id,
        "duration_ms": duration_ms,
        "engine": engine,
        "cache_hit": cache_hit,
        "llm_latency_ms": llm_latency_ms,
        "token_usage": token_usage,
        "mongo_query_ms": mongo_query_ms,
        "duckdb_query_ms": duckdb_query_ms,
        "memory_mb": memory_mb,
        "cpu_percent": cpu_percent,
    }
    logger.log(level, message, extra=extra, exc_info=exc_info)


def log_request_start(request_id: str, method: str, path: str, workspace_id: Optional[str] = None) -> None:
    log_with_context(
        logging.INFO,
        f"REQUEST_START method={method} path={path}",
        request_id=request_id,
        workspace_id=workspace_id,
    )


def log_request_end(
    request_id: str,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    workspace_id: Optional[str] = None,
) -> None:
    log_with_context(
        logging.INFO,
        f"REQUEST_END method={method} path={path} status={status_code} duration_ms={duration_ms:.2f}",
        request_id=request_id,
        workspace_id=workspace_id,
        duration_ms=duration_ms,
    )
