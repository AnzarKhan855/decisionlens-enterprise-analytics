import time
import functools
import threading
import logging
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime, timezone

from app.observability.structured_logger import get_logger, log_with_context

logger = get_logger(__name__)


class ExecutionTrace:
    _traces: Dict[str, List[Dict[str, Any]]] = {}
    _lock = threading.Lock()

    @classmethod
    def start(cls, trace_id: str) -> str:
        with cls._lock:
            cls._traces[trace_id] = []
        return trace_id

    @classmethod
    def record(cls, trace_id: str, stage: str, duration_ms: float, status: str = "success") -> None:
        with cls._lock:
            if trace_id not in cls._traces:
                cls._traces[trace_id] = []
            cls._traces[trace_id].append({
                "stage": stage,
                "duration_ms": round(duration_ms, 2),
                "status": status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    @classmethod
    def get(cls, trace_id: str) -> List[Dict[str, Any]]:
        with cls._lock:
            return cls._traces.get(trace_id, [])

    @classmethod
    def get_summary(cls, trace_id: str) -> Dict[str, Any]:
        events = cls.get(trace_id)
        total_ms = sum(e["duration_ms"] for e in events)
        return {
            "trace_id": trace_id,
            "total_duration_ms": round(total_ms, 2),
            "stages": events,
            "stage_count": len(events),
        }

    @classmethod
    def clear(cls, trace_id: str) -> None:
        with cls._lock:
            cls._traces.pop(trace_id, None)


def trace(stage_name: str, engine: Optional[str] = None):
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            trace_id = kwargs.pop("_trace_id", None) or getattr(kwargs, "trace_id", None)
            if not trace_id:
                trace_id = datetime.now(timezone.utc).strftime("trace_%Y%m%d_%H%M%S_%f")

            start = time.perf_counter()
            status = "success"
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as exc:
                status = "failed"
                raise
            finally:
                duration_ms = (time.perf_counter() - start) * 1000
                ExecutionTrace.record(trace_id, stage_name, duration_ms, status)
                log_with_context(
                    logging.DEBUG,
                    f"[Trace] {stage_name} completed in {duration_ms:.2f}ms ({status})",
                    engine=engine or stage_name,
                    duration_ms=duration_ms,
                )
        return wrapper
    return decorator
