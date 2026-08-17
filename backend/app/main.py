from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import os
import time
import threading
import uuid

from app.core.config import settings
from app.api.v1.routes import api_router
from app.api.v1.workspace_upload import router as workspace_upload_router
from app.api.v1.copilot_api import router as copilot_router
from app.api.v1.business_memory_api import router as business_memory_router

from app.database.connection import create_tables
from app.database.mongodb import ping_mongodb, ensure_indexes
from app.services.email_service import ResendEmailService
from app.logging.logger import get_logger

logger = get_logger(__name__)

from app.api.v1.endpoints.diagnostics import router as diagnostics_router
from app.middleware.rate_limit import RateLimitMiddleware
from app.observability.error_handler import GlobalErrorHandlerMiddleware, RequestState
from app.observability.health import get_platform_health, get_full_health

_app_metrics = {
    "total_requests": 0,
    "total_errors": 0,
    "total_latency_ms": 0.0,
    "endpoint_times": {},
    "_lock": threading.Lock(),
}


def _record_request(endpoint: str, latency_ms: float, status_code: int):
    with _app_metrics["_lock"]:
        _app_metrics["total_requests"] += 1
        _app_metrics["total_latency_ms"] += latency_ms
        if status_code >= 500:
            _app_metrics["total_errors"] += 1
        if endpoint not in _app_metrics["endpoint_times"]:
            _app_metrics["endpoint_times"][endpoint] = {"count": 0, "total_ms": 0.0, "avg_ms": 0.0}
        ep = _app_metrics["endpoint_times"][endpoint]
        ep["count"] += 1
        ep["total_ms"] += latency_ms
        ep["avg_ms"] = ep["total_ms"] / ep["count"]


app = FastAPI(
    title="DecisionLens Enterprise Decision Intelligence Platform",
    version="2.0.0"
)

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
if settings.FRONTEND_URL and settings.FRONTEND_URL not in origins:
    origins.append(settings.FRONTEND_URL)
extra_origins = os.getenv("ALLOWED_ORIGINS", "")
if extra_origins:
    for o in extra_origins.split(","):
        o_clean = o.strip()
        if o_clean and o_clean not in origins:
            origins.append(o_clean)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Content-Type", "Authorization"],
)

from app.middleware.performance_middleware import HighResolutionPerformanceMiddleware

app.add_middleware(GlobalErrorHandlerMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(HighResolutionPerformanceMiddleware)


@app.middleware("http")
async def workspace_context_middleware(request: Request, call_next):
    request_id = RequestState.get_request_id() or str(uuid.uuid4())
    ws_id = request.query_params.get("workspace_id") or request.headers.get("X-Workspace-Id")
    if ws_id:
        RequestState.set_workspace_id(ws_id)
    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id
    return response


@app.get("/api/v1/metrics")
def get_metrics():
    with _app_metrics["_lock"]:
        total = _app_metrics["total_requests"]
        avg_ms = _app_metrics["total_latency_ms"] / total if total > 0 else 0.0
        return {
            "total_requests": total,
            "total_errors": _app_metrics["total_errors"],
            "avg_latency_ms": round(avg_ms, 2),
            "endpoints": dict(_app_metrics["endpoint_times"]),
        }


@app.get("/api/v1/metrics/duckdb")
def get_duckdb_metrics():
    from app.database.duckdb_engine import DuckDBEngine
    return DuckDBEngine.get_stats()


@app.get("/api/v1/metrics/cache")
def get_cache_metrics():
    from app.cache.memory_cache import TTLCache, QueryResultCache
    from app.cache.redis_cache import RedisCacheManager
    from app.ingestion.semantic_profiler import _profile_cache as profile_cache
    from app.ingestion.workspace_discovery import discovery_cache, file_listing_cache

    return {
        "semantic_profiler": profile_cache.stats(),
        "workspace_discovery": discovery_cache.stats(),
        "file_listing": file_listing_cache.stats(),
        "query_result": QueryResultCache.stats(),
        "redis": RedisCacheManager.stats(),
    }


@app.on_event("startup")
def startup_event():
    import os
    logger.info(
        "DecisionLens Enterprise Platform Started",
        extra={"event": "startup", "version": "2.0.0"}
    )

    missing = settings.validate()
    if missing:
        logger.warning(
            f"[CONFIG WARNING] Missing required environment variables: {', '.join(missing)}",
            extra={"missing_vars": missing}
        )

    if ResendEmailService.is_configured():
        logger.info(
            f"[Email Service] Resend Enabled | Sender: {settings.EMAIL_FROM}",
            extra={"email_sender": settings.EMAIL_FROM}
        )
    else:
        logger.warning("[Email Service Warning] RESEND_API_KEY missing in backend/.env")

    create_tables()
    ping_mongodb()
    ensure_indexes()


@app.api_route(
    "/health",
    methods=["GET", "HEAD"]
)
@app.api_route(
    "/api/v1/health",
    methods=["GET", "HEAD"]
)
def health_check():
    return get_platform_health()


@app.get("/api/v1/status")
def platform_status():
    return get_full_health()


@app.get("/api/v1/system")
def system_info():
    return {
        "status": "operational",
        "version": "2.0.0",
        "environment": getattr(settings, "ENV", "development"),
        "debug": settings.DEBUG,
        "features": {
            "groq_llm": bool(getattr(settings, "GROQ_API_KEY", "")),
            "email_service": ResendEmailService.is_configured(),
            "redis_cache": bool(getattr(settings, "REDIS_URL", "")),
            "mongo_db": True,
            "duckdb": True,
        },
    }

app.include_router(
    workspace_upload_router,
    prefix="/api/v1",
    tags=["Business Workspaces & Multi-Table Ingestion"]
)

app.include_router(
    diagnostics_router,
    prefix="/api/v1/diagnostics",
    tags=["System Diagnostics"]
)

app.include_router(
    api_router,
    prefix="/api/v1"
)

app.include_router(
    copilot_router,
    prefix="/api/v1/copilot",
    tags=["Enterprise AI Copilot"]
)

app.include_router(
    copilot_router,
    prefix="/api/v1/ai/copilot",
    tags=["Enterprise AI Copilot"]
)

app.include_router(
    business_memory_router,
    prefix="/api/v1",
    tags=["Business Memory & Reports"]
)

@app.get("/")
def home():
    return {
        "message":
        "DecisionLens Enterprise Decision Intelligence Platform Operating System"
    }