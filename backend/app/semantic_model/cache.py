import json
import time
import hashlib
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from app.semantic_model.core import SemanticModel


CACHE_DIR = Path("storage/semantic_model_cache")
CACHE_META_FILE = CACHE_DIR / "cache_metadata.json"
CACHE_TTL_SECONDS = 3600
MAX_CACHE_ENTRIES = 50


class SemanticModelCache:
    """
    Persistent file-based cache for semantic models with TTL-based expiration
    and LRU eviction for enterprise-scale datasets.
    """

    def __init__(self):
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._memory_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self._access_order: list = []

    def _get_cache_path(self, cache_key: str) -> Path:
        safe_key = cache_key.replace("/", "_").replace("\\", "_")
        return CACHE_DIR / f"{safe_key}.json"

    def _is_valid(self, cache_key: str, mtime: float) -> bool:
        if cache_key not in self._memory_cache:
            return False
        cached_mtime, _ = self._memory_cache[cache_key]
        if cached_mtime != mtime:
            return False
        _, cached_data = self._memory_cache[cache_key]
        if time.time() - cached_data.get("_cached_at", 0) > CACHE_TTL_SECONDS:
            return False
        return True

    def get(self, workspace_id: str, mtime: float, include_lineage: bool = True) -> Optional[Dict[str, Any]]:
        cache_key = self._compute_cache_key(workspace_id, include_lineage)

        if self._is_valid(cache_key, mtime):
            self._touch(cache_key)
            return self._memory_cache[cache_key][1]

        cache_path = self._get_cache_path(cache_key)
        if cache_path.exists():
            try:
                with open(cache_path, "r") as f:
                    data = json.load(f)
                if data.get("_mtime") == mtime:
                    self._memory_cache[cache_key] = (mtime, data)
                    self._touch(cache_key)
                    return data
            except Exception:
                pass

        return None

    def put(self, workspace_id: str, mtime: float, model: Dict[str, Any], include_lineage: bool = True):
        cache_key = self._compute_cache_key(workspace_id, include_lineage)
        model["_mtime"] = mtime
        model["_cached_at"] = time.time()

        self._memory_cache[cache_key] = (mtime, model)
        self._touch(cache_key)

        cache_path = self._get_cache_path(cache_key)
        try:
            with open(cache_path, "w") as f:
                json.dump(model, f, indent=2, default=str)
        except Exception:
            pass

        self._evict_if_needed()

    def invalidate(self, workspace_id: Optional[str] = None):
        if workspace_id:
            keys_to_remove = [k for k in self._memory_cache if k.startswith(workspace_id)]
            for k in keys_to_remove:
                del self._memory_cache[k]
                cache_path = self._get_cache_path(k)
                if cache_path.exists():
                    try:
                        cache_path.unlink()
                    except Exception:
                        pass
        else:
            self._memory_cache.clear()
            for f in CACHE_DIR.glob("*.json"):
                try:
                    f.unlink()
                except Exception:
                    pass

    def _compute_cache_key(self, workspace_id: str, include_lineage: bool) -> str:
        parts = [workspace_id, str(include_lineage)]
        return hashlib.md5("|".join(parts).encode()).hexdigest()

    def _touch(self, cache_key: str):
        if cache_key in self._access_order:
            self._access_order.remove(cache_key)
        self._access_order.append(cache_key)

    def _evict_if_needed(self):
        while len(self._access_order) > MAX_CACHE_ENTRIES:
            oldest = self._access_order.pop(0)
            if oldest in self._memory_cache:
                del self._memory_cache[oldest]
            cache_path = self._get_cache_path(oldest)
            if cache_path.exists():
                try:
                    cache_path.unlink()
                except Exception:
                    pass

    def clear(self):
        self._memory_cache.clear()
        self._access_order.clear()
        for f in CACHE_DIR.glob("*.json"):
            try:
                f.unlink()
            except Exception:
                pass


_cache_instance: Optional[SemanticModelCache] = None


def get_cache() -> SemanticModelCache:
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = SemanticModelCache()
    return _cache_instance


def invalidate_all_caches():
    get_cache().clear()