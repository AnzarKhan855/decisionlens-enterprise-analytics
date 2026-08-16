from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import re
import time
import threadpoolctl
from concurrent.futures import ThreadPoolExecutor, as_completed
import duckdb

from app.database.duckdb_engine import DuckDBEngine
from app.ingestion.semantic_profiler import SemanticDataProfiler
from app.database.storage import STORAGE_DIR
from app.cache.memory_cache import TTLCache


discovery_cache = TTLCache(maxsize=64, ttl=120.0)
file_listing_cache = TTLCache(maxsize=32, ttl=60.0)

def clean_table_name(raw_stem: str) -> str:
    s = raw_stem.lower().replace("-", "_")
    s = re.sub(r'^[0-9a-f]{8}_[0-9a-f]{4}_[0-9a-f]{4}_[0-9a-f]{4}_[0-9a-f]{12}_?', '', s)
    s = re.sub(r'^\d+_?', '', s)
    return s.lstrip('_') or raw_stem


class WorkspaceDiscoveryEngine:
    """
    DecisionLens v10.0 Workspace Discovery & Table Classification Engine.
    Uses TTLCache for sub-10ms repeated responses and concurrent profiling
    for multi-table workspaces.
    """

    @classmethod
    def clear_cache(cls, workspace_id: Optional[str] = None):
        if workspace_id:
            discovery_cache.delete(workspace_id)
            file_listing_cache.delete(workspace_id)
        else:
            discovery_cache.clear()
            file_listing_cache.clear()

    @classmethod
    def _get_workspace_parquet_files(cls, parquet_dir: Path, workspace_id: str) -> List[Path]:
        cache_key = f"files:{workspace_id}"
        cached = file_listing_cache.get(cache_key)
        if cached is not None:
            return cached

        if not parquet_dir.exists():
            return []

        if workspace_id:
            try:
                from app.services.workspace_service import EnterpriseWorkspaceManager
                ws_info = EnterpriseWorkspaceManager.get_workspace(workspace_id)
                if ws_info and ws_info.get("tables"):
                    ws_paths = []
                    for tbl in ws_info["tables"]:
                        if tbl.get("file_path"):
                            p = Path(tbl["file_path"])
                            if p.exists() and p not in ws_paths:
                                ws_paths.append(p)
                    if ws_paths:
                        file_listing_cache.set(cache_key, ws_paths, ttl=60.0)
                        return ws_paths
            except Exception:
                pass

        clean_target = workspace_id.lower().replace("-", "_")
        all_parquets = list(parquet_dir.glob("*.parquet"))
        parquet_files = [
            p for p in all_parquets
            if not p.name.startswith("unified_")
            and not p.name.startswith("sample-")
            and (clean_target in p.stem.lower().replace("-", "_") or p.stem.lower().replace("-", "_").startswith(clean_target))
        ]

        if not parquet_files:
            parquet_files = [
                p for p in all_parquets
                if not p.name.startswith("unified_")
                and not p.name.startswith("sample-")
            ]

        file_listing_cache.set(cache_key, parquet_files, ttl=60.0)
        return parquet_files

    @classmethod
    def discover_workspace(cls, parquet_dir: Optional[Path] = None, workspace_id: Optional[str] = None, force_refresh: bool = False) -> Dict[str, Any]:
        if parquet_dir is None:
            parquet_dir = STORAGE_DIR

        target_ws_id = workspace_id or "default"
        cache_key = f"discovery:{target_ws_id}"

        if not force_refresh:
            cached = discovery_cache.get(cache_key)
            if cached is not None:
                return cached

        if not parquet_dir.exists():
            return {"tables": [], "fact_tables": [], "dimension_tables": [], "lookup_tables": [], "is_lookup_only": False}

        from app.services.workspace_service import EnterpriseWorkspaceManager
        target_ws_id = workspace_id or EnterpriseWorkspaceManager.get_active_workspace_id() or "default"

        parquet_files = cls._get_workspace_parquet_files(parquet_dir, target_ws_id)

        if not parquet_files:
            return {"tables": [], "fact_tables": [], "dimension_tables": [], "lookup_tables": [], "is_lookup_only": False}

        current_mtime = max(p.stat().st_mtime for p in parquet_files) if parquet_files else 0.0
        mtime_key = f"{cache_key}:{current_mtime}"

        if not force_refresh:
            cached = discovery_cache.get(mtime_key)
            if cached is not None:
                discovery_cache.set(cache_key, cached, ttl=120.0)
                return cached

        tables_classified = []
        fact_tables = []
        dimension_tables = []
        lookup_tables = []
        reference_tables = []
        bridge_tables = []
        metadata_tables = []

        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_file = {
                executor.submit(cls._profile_table, pfile, target_ws_id): pfile
                for pfile in parquet_files
            }
            for future in as_completed(future_to_file):
                pfile = future_to_file[future]
                try:
                    table_info, classification = future.result()
                except Exception:
                    continue

                tables_classified.append(table_info)
                role = classification["role"]
                if role == "Fact Table":
                    fact_tables.append(table_info)
                elif role == "Dimension Table":
                    dimension_tables.append(table_info)
                elif role == "Lookup Table":
                    lookup_tables.append(table_info)
                elif role == "Reference Table":
                    reference_tables.append(table_info)
                elif role == "Bridge Table":
                    bridge_tables.append(table_info)
                else:
                    metadata_tables.append(table_info)

        is_lookup_only = len(fact_tables) == 0 and (len(lookup_tables) > 0 or len(reference_tables) > 0)
        fact_tables.sort(key=lambda t: t["row_count"], reverse=True)

        result = {
            "tables": tables_classified,
            "fact_tables": fact_tables,
            "dimension_tables": dimension_tables,
            "lookup_tables": lookup_tables,
            "reference_tables": reference_tables,
            "bridge_tables": bridge_tables,
            "metadata_tables": metadata_tables,
            "is_lookup_only": is_lookup_only,
            "primary_fact_table": fact_tables[0] if fact_tables else (dimension_tables[0] if dimension_tables else None)
        }

        discovery_cache.set(cache_key, result, ttl=120.0)
        discovery_cache.set(mtime_key, result, ttl=300.0)
        return result

    @staticmethod
    def _profile_table(pfile: Path, workspace_id: Optional[str] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        raw_stem = pfile.stem
        if workspace_id:
            from app.semantic_model.engine import _strip_workspace_prefix
            raw_stem = _strip_workspace_prefix(raw_stem, workspace_id)
        table_name = clean_table_name(raw_stem)
        try:
            profile = SemanticDataProfiler.profile(pfile)
            columns = list(profile.get("columns", {}).keys())
            row_count = profile.get("total_rows", 0)
            measures = profile.get("column_categories", {}).get("measures", [])
            temporal = profile.get("column_categories", {}).get("temporal", [])
            identifiers = profile.get("column_categories", {}).get("identifiers", [])
            excluded = set(measures) | set(temporal) | set(identifiers)
            dimensions = [c for c in columns if c not in excluded]
        except Exception:
            columns = []
            row_count = 0
            measures = []
            dimensions = []

        raw_classification = SemanticDataProfiler.classify_table(table_name, row_count, measures, dimensions, columns)
        table_type = raw_classification.get("table_type", "Dimension Table")
        classification = {
            "role": table_type,
            "is_fact": table_type == "Fact Table",
            "purpose": raw_classification.get("purpose", ""),
            "explanation": raw_classification.get("explanation", ""),
            "table_type": table_type,
            "is_lookup": raw_classification.get("is_lookup", False),
        }
        table_info = {
            "file_name": pfile.name,
            "file_path": str(pfile),
            "table_name": table_name,
            "columns": columns,
            "row_count": row_count,
            "measures": measures,
            "role": table_type,
            "is_fact": table_type == "Fact Table",
            "reason": raw_classification.get("explanation", ""),
            "description": raw_classification.get("purpose", "")
        }
        return table_info, classification
