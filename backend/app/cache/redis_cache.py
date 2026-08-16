import json
import time
import threading
from typing import Any, Dict, Optional


class RedisCacheManager:
    """
    High-Throughput Query Result Caching Manager.
    Supports both persistent Redis backend and in-memory fallback.
    Provides query result caching for DuckDB metric results and dataset profiles,
    with TTL expiration and graceful fallback.
    """

    _memory_cache: Dict[str, Dict[str, Any]] = {}
    _redis_client: Optional[Any] = None
    _initialized = False
    _lock = threading.Lock()
    _hits = 0
    _misses = 0
    _set_count = 0

    @classmethod
    def initialize(cls, redis_url: Optional[str] = None, ttl_seconds: int = 300) -> None:
        with cls._lock:
            if cls._initialized:
                return
            cls._ttl = ttl_seconds
            if redis_url:
                try:
                    import redis
                    cls._redis_client = redis.from_url(
                        redis_url,
                        socket_connect_timeout=2,
                        socket_timeout=2,
                        decode_responses=True,
                        max_connections=10,
                    )
                    cls._redis_client.ping()
                    cls._get_backend = "redis"
                except Exception:
                    cls._redis_client = None
                    cls._get_backend = "memory"
            else:
                cls._get_backend = "memory"
            cls._initialized = True

    @classmethod
    def _get_backend(cls) -> str:
        # Read directly from class __dict__ to avoid classmethod shadowing
        return cls.__dict__.get("_backend", "memory")

    @classmethod
    def get(cls, key: str) -> Optional[Any]:
        now = time.time()
        if cls._get_backend() == "redis" and cls._redis_client is not None:
            try:
                raw = cls._redis_client.get(key)
                if raw is not None:
                    cls._hits += 1
                    return json.loads(raw)
                cls._misses += 1
                return None
            except Exception:
                cls._misses += 1
                return None

        with cls._lock:
            entry = cls._memory_cache.get(key)
            if entry is None:
                cls._misses += 1
                return None
            if entry["expires_at"] > now:
                cls._hits += 1
                return entry["value"]
            del cls._memory_cache[key]
            cls._misses += 1
            return None

    @classmethod
    def set(cls, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else getattr(cls, "_ttl", 300)
        expires_at = time.time() + ttl

        if getattr(cls, "_backend", "memory") == "redis" and cls._redis_client is not None:
            try:
                cls._redis_client.setex(key, ttl, json.dumps(value, default=str))
                cls._set_count += 1
                return
            except Exception:
                pass

        with cls._lock:
            cls._memory_cache[key] = {
                "value": value,
                "expires_at": expires_at,
            }
            cls._set_count += 1

    @classmethod
    def delete(cls, key: str) -> bool:
        if cls._get_backend() == "redis" and cls._redis_client is not None:
            try:
                cls._redis_client.delete(key)
                return True
            except Exception:
                return False
        with cls._lock:
            if key in cls._memory_cache:
                del cls._memory_cache[key]
                return True
            return False

    @classmethod
    def clear(cls) -> None:
        if cls._get_backend() == "redis" and cls._redis_client is not None:
            try:
                cls._redis_client.flushdb()
            except Exception:
                pass
        with cls._lock:
            cls._memory_cache.clear()

    @classmethod
    def get_many(cls, keys: list) -> Dict[str, Any]:
        return {k: v for k in keys if (v := cls.get(k)) is not None}

    @classmethod
    def set_many(cls, mapping: Dict[str, Any], ttl_seconds: Optional[int] = None) -> None:
        for k, v in mapping.items():
            cls.set(k, v, ttl_seconds=ttl_seconds)

    @classmethod
    def stats(cls) -> Dict[str, Any]:
        now = time.time()
        with cls._lock:
            expired = sum(1 for v in cls._memory_cache.values() if v["expires_at"] <= now)
            active = sum(1 for v in cls._memory_cache.values() if v["expires_at"] > now)
            total = cls._hits + cls._misses
            hit_rate = cls._hits / total if total > 0 else 0.0
            return {
                "backend": cls._get_backend(),
                "active_entries": active,
                "expired_entries": expired,
                "hits": cls._hits,
                "misses": cls._misses,
                "hit_rate": round(hit_rate, 4),
                "sets": cls._set_count,
                "ttl_seconds": getattr(cls, "_ttl", 300),
            }