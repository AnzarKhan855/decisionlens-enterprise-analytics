import time
import threading
from typing import Any, Dict, Optional, Callable
from collections import OrderedDict


class TTLCache:
    _instances: Dict[str, "TTLCache"] = {}
    _lock = threading.Lock()

    def __init__(self, maxsize: int = 1024, ttl: float = 300.0):
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._maxsize = maxsize
        self._ttl = ttl
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    @classmethod
    def get_instance(cls, name: str = "default", maxsize: int = 1024, ttl: float = 300.0) -> "TTLCache":
        with cls._lock:
            if name not in cls._instances:
                cls._instances[name] = cls(maxsize=maxsize, ttl=ttl)
            return cls._instances[name]

    def _cleanup_expired(self) -> None:
        now = time.time()
        expired_keys = [k for k, v in self._cache.items() if now > v["expires_at"]]
        for k in expired_keys:
            del self._cache[k]
            self._evictions += 1

    def _workspace_key(self, key: str, workspace_id: Optional[str] = None) -> str:
        if workspace_id:
            return f"{workspace_id}:{key}"
        return key

    def get(self, key: str, workspace_id: Optional[str] = None) -> Optional[Any]:
        with self._lock:
            self._cleanup_expired()
            full_key = self._workspace_key(key, workspace_id)
            entry = self._cache.get(full_key)
            if entry is None:
                self._misses += 1
                return None
            if time.time() > entry["expires_at"]:
                del self._cache[full_key]
                self._misses += 1
                return None
            self._cache.move_to_end(full_key)
            self._hits += 1
            return entry["value"]

    def set(self, key: str, value: Any, ttl: Optional[float] = None, workspace_id: Optional[str] = None) -> None:
        with self._lock:
            self._cleanup_expired()
            full_key = self._workspace_key(key, workspace_id)
            if full_key in self._cache:
                del self._cache[full_key]
            elif len(self._cache) >= self._maxsize:
                self._cache.popitem(last=False)
                self._evictions += 1
            expires_at = time.time() + (ttl if ttl is not None else self._ttl)
            self._cache[full_key] = {"value": value, "expires_at": expires_at}

    def delete(self, key: str, workspace_id: Optional[str] = None) -> bool:
        with self._lock:
            full_key = self._workspace_key(key, workspace_id)
            if full_key in self._cache:
                del self._cache[full_key]
                return True
            return False

    def clear_workspace(self, workspace_id: str) -> int:
        with self._lock:
            prefix = f"{workspace_id}:"
            to_delete = [k for k in self._cache if k.startswith(prefix)]
            for k in to_delete:
                del self._cache[k]
            return len(to_delete)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def keys(self, workspace_id: Optional[str] = None) -> list:
        with self._lock:
            self._cleanup_expired()
            if workspace_id:
                prefix = f"{workspace_id}:"
                return [k for k in self._cache if k.startswith(prefix)]
            return list(self._cache.keys())

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0.0
            return {
                "entries": len(self._cache),
                "maxsize": self._maxsize,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate, 4),
                "evictions": self._evictions,
                "ttl_seconds": self._ttl,
            }

    def get_many(self, keys: list, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        result = {}
        for k in keys:
            v = self.get(k, workspace_id=workspace_id)
            if v is not None:
                result[k] = v
        return result

    def set_many(self, mapping: Dict[str, Any], ttl: Optional[float] = None, workspace_id: Optional[str] = None) -> None:
        for k, v in mapping.items():
            self.set(k, v, ttl=ttl, workspace_id=workspace_id)

    def compute_if_absent(self, key: str, factory: Callable[[], Any], ttl: Optional[float] = None, workspace_id: Optional[str] = None) -> Any:
        result = self.get(key, workspace_id=workspace_id)
        if result is not None:
            return result
        result = factory()
        self.set(key, result, ttl=ttl, workspace_id=workspace_id)
        return result


class QueryResultCache:
    _cache: Dict[str, Dict[str, Any]] = {}
    _lock = threading.Lock()

    @staticmethod
    def get(key: str) -> Optional[Any]:
        entry = QueryResultCache._cache.get(key)
        if entry is None:
            return None
        if entry["expires_at"] > time.time():
            return entry["value"]
        del QueryResultCache._cache[key]
        return None

    @staticmethod
    def set(key: str, value: Any, ttl_seconds: int = 300) -> None:
        QueryResultCache._cache[key] = {
            "value": value,
            "expires_at": time.time() + ttl_seconds,
        }

    @staticmethod
    def clear() -> None:
        QueryResultCache._cache.clear()

    @staticmethod
    def stats() -> Dict[str, Any]:
        now = time.time()
        expired = sum(1 for v in QueryResultCache._cache.values() if v["expires_at"] <= now)
        return {
            "entries": len(QueryResultCache._cache),
            "expired_entries": expired,
        }
