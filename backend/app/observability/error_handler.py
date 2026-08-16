import uuid
import time
import traceback
import threading
from typing import Any, Dict, Optional, Callable
from datetime import datetime, timezone

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.observability.structured_logger import get_logger, log_request_end

logger = get_logger(__name__)


class RequestState:
    _local = threading.local()

    @classmethod
    def set_request_id(cls, request_id: str) -> None:
        cls._local.request_id = request_id

    @classmethod
    def get_request_id(cls) -> str:
        return getattr(cls._local, "request_id", None) or "unknown"

    @classmethod
    def set_workspace_id(cls, workspace_id: Optional[str]) -> None:
        cls._local.workspace_id = workspace_id

    @classmethod
    def get_workspace_id(cls) -> Optional[str]:
        return getattr(cls._local, "workspace_id", None)


class ErrorDetail:
    def __init__(self, error_id: str, status: str, reason: str, recovery_suggestion: str, timestamp: str, severity: str):
        self.error_id = error_id
        self.status = status
        self.reason = reason
        self.recovery_suggestion = recovery_suggestion
        self.timestamp = timestamp
        self.severity = severity

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_id": self.error_id,
            "status": self.status,
            "reason": self.reason,
            "recovery_suggestion": self.recovery_suggestion,
            "timestamp": self.timestamp,
            "severity": self.severity,
        }


def _build_error_response(
    exc: Exception,
    status_code: int = 500,
    stage: str = "unknown",
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    error_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    if isinstance(exc, HTTPException):
        severity = "LOW" if status_code < 500 else "MEDIUM"
        if status_code == 422:
            recovery_suggestion = "Check request payload format and required fields."
        elif status_code == 404:
            recovery_suggestion = "Verify the requested resource exists and try again."
        elif status_code == 413:
            recovery_suggestion = "Reduce file size and retry upload. Maximum size is 500MB."
        elif status_code == 429:
            recovery_suggestion = "Too many requests. Wait before retrying."
        else:
            recovery_suggestion = "Review the request parameters and retry."
        return ErrorDetail(
            error_id=error_id,
            status="error",
            reason=str(exc.detail) if hasattr(exc, "detail") else str(exc),
            recovery_suggestion=recovery_suggestion,
            timestamp=timestamp,
            severity=severity,
        ).to_dict()

    severity = "HIGH" if status_code >= 500 else "MEDIUM"

    reason = str(exc)
    recovery_suggestion = "An unexpected error occurred. Please retry or contact support with the error ID."

    if "forecast" in stage.lower() or "prediction" in stage.lower():
        recovery_suggestion = "Forecast unavailable. Ensure dataset has sufficient temporal and numeric data. Retry after verifying data quality."
    elif "report" in stage.lower():
        recovery_suggestion = "Report generation failed. A partial report may be available. Check dataset quality and retry."
    elif "copilot" in stage.lower() or "ai" in stage.lower():
        recovery_suggestion = "AI analysis unavailable. Retry with a different question or verify dataset integrity."
    elif "upload" in stage.lower():
        recovery_suggestion = "Upload failed. Verify file format (CSV, Excel, Parquet) and try again."
    elif "analytics" in stage.lower():
        recovery_suggestion = "Analytics engine encountered an error. The dashboard will display partial results. Retry analysis after verifying dataset structure."
    elif "mongo" in stage.lower():
        recovery_suggestion = "Database connection issue. The system will retry automatically. Contact support if the issue persists."
    elif "duckdb" in stage.lower():
        recovery_suggestion = "Query engine encountered an error. Retry the operation."

    logger.error(
        f"[GlobalErrorHandler] error_id={error_id} stage={stage} status={status_code} error={reason}",
        exc_info=True,
    )

    return ErrorDetail(
        error_id=error_id,
        status="error",
        reason=reason,
        recovery_suggestion=recovery_suggestion,
        timestamp=timestamp,
        severity=severity,
    ).to_dict()


class GlobalErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        RequestState.set_request_id(request_id)

        start_time = time.perf_counter()
        try:
            response = await call_next(request)
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            log_request_end(
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=elapsed_ms,
                workspace_id=RequestState.get_workspace_id(),
            )
            return response
        except HTTPException as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            error_body = _build_error_response(exc, status_code=exc.status_code, stage="http_exception")
            log_request_end(
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=exc.status_code,
                duration_ms=elapsed_ms,
                workspace_id=RequestState.get_workspace_id(),
            )
            return JSONResponse(status_code=exc.status_code, content=error_body)
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            error_body = _build_error_response(exc, status_code=500, stage="unhandled_exception")
            log_request_end(
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=500,
                duration_ms=elapsed_ms,
                workspace_id=RequestState.get_workspace_id(),
            )
            return JSONResponse(status_code=500, content=error_body)
