import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.logging.logger import get_logger

logger = get_logger("performance_profiler")

PROFILES_PATHS = [
    "/api/v1/upload",
    "/api/v1/dashboard",
    "/api/v1/scenario",
    "/api/v1/analytics/scenario",
    "/api/v1/ml/forecast",
    "/api/v1/reports",
    "/api/v1/strategy",
    "/api/v1/copilot",
    "/api/v1/ai",
    "/api/v1/audit",
]

class HighResolutionPerformanceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if not any(path.startswith(prefix) for prefix in PROFILES_PATHS):
            return await call_next(request)

        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        start_time = time.perf_counter()

        response = await call_next(request)

        total_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Retrieve thread-local timing metrics if set by engines
        duckdb_time_ms = getattr(request.state, "duckdb_time_ms", 0.0)
        mongo_time_ms = getattr(request.state, "mongo_time_ms", 0.0)
        llm_time_ms = getattr(request.state, "llm_time_ms", 0.0)
        serialization_time_ms = getattr(request.state, "serialization_time_ms", 0.0)

        logger.info(
            f"[API Profile] {request.method} {path} - {response.status_code} | "
            f"Total: {total_time_ms}ms | DuckDB: {duckdb_time_ms}ms | Mongo: {mongo_time_ms}ms | "
            f"LLM: {llm_time_ms}ms | Serialization: {serialization_time_ms}ms",
            extra={
                "request_id": request_id,
                "path": path,
                "status_code": response.status_code,
                "total_request_time_ms": total_time_ms,
                "duckdb_time_ms": duckdb_time_ms,
                "mongo_time_ms": mongo_time_ms,
                "llm_time_ms": llm_time_ms,
                "serialization_time_ms": serialization_time_ms,
            }
        )

        response.headers["X-Response-Time-Ms"] = str(total_time_ms)
        return response
