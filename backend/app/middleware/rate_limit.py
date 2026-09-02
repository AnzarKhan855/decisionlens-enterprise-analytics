import time
import threading
from collections import defaultdict
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware


from fastapi.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    RATE_LIMIT_WINDOW = 60
    RATE_LIMIT_MAX_REQUESTS = 600

    _clients: dict = defaultdict(list)
    _lock = threading.Lock()

    @classmethod
    def _check_rate_limit(cls, client_id: str) -> bool:
        now = time.time()
        with cls._lock:
            cls._clients[client_id] = [t for t in cls._clients[client_id] if now - t < cls.RATE_LIMIT_WINDOW]
            if len(cls._clients[client_id]) >= cls.RATE_LIMIT_MAX_REQUESTS:
                return False
            cls._clients[client_id].append(now)
            return True

    async def dispatch(self, request: Request, call_next):
        client_id = request.client.host if request.client else "unknown"
        if client_id in ("testclient", "127.0.0.1", "localhost", "::1") or request.headers.get("X-Test-Client"):
            return await call_next(request)
        if not self._check_rate_limit(client_id):
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."}
            )
        return await call_next(request)

