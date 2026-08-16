from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from app.logging.logger import get_logger

logger = get_logger(__name__)


class AnalyticsCacheService:
    """
    Two-Tier (Memory + MongoDB) Cache for Canonical Analytics Object.

    Collections:
      - analytics_cache: stores full AnalyticsResult per workspace
      - workspace_summary: stores lightweight workspace metadata
      - dataset_statistics: stores dataset-level statistics

    Cache keys:
      - analytics_cache: { "workspace_id": <workspace_id> }
      - workspace_summary: { "workspace_id": <workspace_id> }
      - dataset_statistics: { "workspace_id": <workspace_id>, "dataset_id": <dataset_id> }
    """
    _memory_cache: Dict[str, Tuple[str, float, Dict[str, Any]]] = {}

    @classmethod
    def get_cached(cls, workspace_id: str, path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
        if not workspace_id:
            return None
        path_key = ""
        mtime = 0.0
        if path and path.exists():
            try:
                path_key = str(path.resolve())
                mtime = path.stat().st_mtime
            except Exception:
                pass

        if workspace_id in cls._memory_cache:
            mem_path, mem_mtime, mem_dict = cls._memory_cache[workspace_id]
            if path_key:
                if mem_path == path_key and abs(mem_mtime - mtime) < 1e-4:
                    return mem_dict
                else:
                    cls._memory_cache.pop(workspace_id, None)
            else:
                return mem_dict

        try:
            from app.database.mongodb import analytics_cache as mongo_analytics_cache
            doc = mongo_analytics_cache.find_one({"workspace_id": workspace_id})
            if doc and doc.get("analytics"):
                doc_path = doc.get("parquet_path", "")
                doc_mtime = doc.get("parquet_mtime", 0.0)
                if path_key:
                    if doc_path == path_key and abs(doc_mtime - mtime) < 1e-4:
                        analytics_dict = doc.get("analytics")
                        cls._memory_cache[workspace_id] = (doc_path, doc_mtime, analytics_dict)
                        return analytics_dict
                else:
                    analytics_dict = doc.get("analytics")
                    cls._memory_cache[workspace_id] = (doc_path, doc_mtime, analytics_dict)
                    return analytics_dict
        except Exception as e:
            logger.debug("[AnalyticsCache] Get failed for %s: %s", workspace_id, e)
        return None

    @classmethod
    def set_cached(cls, workspace_id: str, analytics_dict: Dict[str, Any], path: Optional[Path] = None) -> None:
        if not workspace_id or not analytics_dict:
            return
        path_key = ""
        mtime = 0.0
        if path and path.exists():
            try:
                path_key = str(path.resolve())
                mtime = path.stat().st_mtime
            except Exception:
                pass

        cls._memory_cache[workspace_id] = (path_key, mtime, analytics_dict)
        try:
            from app.database.mongodb import analytics_cache as mongo_analytics_cache
            mongo_analytics_cache.update_one(
                {"workspace_id": workspace_id},
                {
                    "$set": {
                        "workspace_id": workspace_id,
                        "parquet_path": path_key,
                        "parquet_mtime": mtime,
                        "analytics": analytics_dict,
                        "generated_at": analytics_dict.get("generated_at") or datetime.now(timezone.utc).isoformat(),
                        "domain": analytics_dict.get("domain"),
                        "dataset_type": analytics_dict.get("dataset_type"),
                        "confidence_score": analytics_dict.get("confidence_score"),
                    }
                },
                upsert=True,
            )
        except Exception as e:
            logger.warning("[AnalyticsCache] Set failed for %s: %s", workspace_id, e)

    @classmethod
    def invalidate(cls, workspace_id: str) -> None:
        if not workspace_id:
            return
        cls._memory_cache.pop(workspace_id, None)
        try:
            from app.database.mongodb import (
                analytics_cache as mongo_analytics_cache,
                forecast_cache as mongo_forecast_cache,
                reports as mongo_reports,
                copilot_history as mongo_copilot_history,
                kpi_history as mongo_kpi_history,
            )
            mongo_analytics_cache.delete_many({"workspace_id": workspace_id})
            mongo_forecast_cache.delete_many({"dataset_id": workspace_id})
            mongo_reports.delete_many({"dataset_id": workspace_id})
            mongo_copilot_history.delete_many({"workspace_id": workspace_id})
            mongo_kpi_history.delete_many({"dataset_id": workspace_id})

            from app.cache.memory_cache import TTLCache
            dashboard_cache = TTLCache.get_instance("dashboard_cache")
            dashboard_cache.clear_workspace(workspace_id)
            query_cache = TTLCache.get_instance("query_result")
            query_cache.clear_workspace(workspace_id)

            logger.info("[AnalyticsCache] Invalidated all caches for workspace %s", workspace_id)
        except Exception as e:
            logger.warning("[AnalyticsCache] Invalidate failed for %s: %s", workspace_id, e)

    @classmethod
    def get_workspace_summary(cls, workspace_id: str) -> Optional[Dict[str, Any]]:
        try:
            from app.database.mongodb import workspaces as mongo_workspaces
            doc = mongo_workspaces.find_one({"workspace_id": workspace_id})
            if doc:
                return {
                    "workspace_id": doc.get("workspace_id"),
                    "name": doc.get("name"),
                    "domain": doc.get("intelligence_domain") or doc.get("domain"),
                    "dataset_type": doc.get("intelligence_dataset_type") or doc.get("dataset_type"),
                    "health_score": doc.get("health_score"),
                    "rows": doc.get("rows"),
                    "columns": doc.get("columns"),
                    "updated_at": doc.get("updated_at"),
                }
        except Exception as e:
            logger.debug("[AnalyticsCache] Workspace summary failed for %s: %s", workspace_id, e)
        return None

    @classmethod
    def set_workspace_summary(cls, workspace_id: str, summary: Dict[str, Any]) -> None:
        try:
            from app.database.mongodb import workspaces as mongo_workspaces
            mongo_workspaces.update_one(
                {"workspace_id": workspace_id},
                {"$set": summary},
                upsert=True,
            )
        except Exception as e:
            logger.warning("[AnalyticsCache] Workspace summary set failed for %s: %s", workspace_id, e)

    @classmethod
    def get_dataset_statistics(cls, workspace_id: str, dataset_id: str) -> Optional[Dict[str, Any]]:
        try:
            from app.database.mongodb import datasets as mongo_datasets
            doc = mongo_datasets.find_one({"workspace_id": workspace_id, "file_path": {"$regex": dataset_id}})
            if not doc:
                doc = mongo_datasets.find_one({"dataset_id": dataset_id})
            if doc:
                return {
                    "dataset_id": dataset_id,
                    "workspace_id": workspace_id,
                    "filename": doc.get("filename"),
                    "rows": doc.get("rows"),
                    "columns": doc.get("columns"),
                    "health_score": doc.get("health_score"),
                    "dataset_type": doc.get("dataset_type"),
                    "uploaded_at": doc.get("uploaded_at"),
                }
        except Exception as e:
            logger.debug("[AnalyticsCache] Dataset statistics failed for %s/%s: %s", workspace_id, dataset_id, e)
        return None
