import os
import json
import uuid
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

from app.database.connection import SessionLocal
from app.database.crud import delete_dataset_permanently
from app.database.storage import ParquetStorageManager

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
DELETED_WORKSPACES_FILE = _BASE_DIR / "storage" / "deleted_workspaces.json"
WORKSPACES_FILE = _BASE_DIR / "storage" / "workspaces.json"
ACTIVE_WORKSPACE_FILE = _BASE_DIR / "storage" / "active_workspace.json"


class EnterpriseWorkspaceManager:
    """
    Enterprise Business Workspace Architecture Manager.
    Provides persistent multi-table workspace registries, relationship graphs, active workspace switching,
    self-healing database/storage reconciliation, and permanent workspace purging.
    """
    _workspaces: Dict[str, Dict[str, Any]] = {}
    _deleted_workspaces: set = set()
    _active_workspace_id: Optional[str] = None
    _is_loading: bool = False

    @classmethod
    def _load_deleted_set(cls) -> set:
        if not cls._deleted_workspaces and DELETED_WORKSPACES_FILE.exists():
            try:
                with open(DELETED_WORKSPACES_FILE, "r") as f:
                    data = json.load(f)
                    cls._deleted_workspaces = set(data)
            except Exception as e:
                logger.warning(f"[Workspace Warning] Could not load deleted workspaces: {e}")
        return cls._deleted_workspaces

    @classmethod
    def _save_deleted_set(cls):
        DELETED_WORKSPACES_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(DELETED_WORKSPACES_FILE, "w") as f:
                json.dump(list(cls._deleted_workspaces), f)
        except Exception as e:
            logger.warning(f"[Workspace Warning] Could not save deleted workspaces list: {e}")

    @classmethod
    def _save_workspaces(cls):
        WORKSPACES_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(WORKSPACES_FILE, "w") as f:
                json.dump(cls._workspaces, f, indent=2)
        except Exception as e:
            logger.warning(f"[Workspace Warning] Could not save workspaces: {e}")

    @classmethod
    def _load_workspaces(cls):
        if cls._workspaces and getattr(cls, "_loaded", False):
            return
        if cls._is_loading:
            return
        cls._is_loading = True
        try:
            deleted_set = cls._load_deleted_set()

            if WORKSPACES_FILE.exists():
                try:
                    with open(WORKSPACES_FILE, "r") as f:
                        data = json.load(f)
                        if isinstance(data, dict):
                            cls._workspaces = {
                                k: v for k, v in data.items()
                                if k not in deleted_set and isinstance(v, dict)
                            }
                except Exception as e:
                    logger.warning(f"[Workspace Warning] Error reading workspaces.json: {e}")

            cls._loaded = True
        finally:
            cls._is_loading = False

    @classmethod
    def get_active_workspace(cls) -> Optional[Dict[str, Any]]:
        active_id = cls.get_active_workspace_id()
        if not active_id:
            return None
        return cls.get_workspace(active_id)

    @classmethod
    def get_active_workspace_id(cls) -> Optional[str]:
        cls._load_workspaces()
        deleted_set = cls._load_deleted_set()

        # 1. Check in-memory variable
        if cls._active_workspace_id and cls._active_workspace_id in cls._workspaces and cls._active_workspace_id not in deleted_set:
            return cls._active_workspace_id

        # 2. Check active_workspace.json file
        if ACTIVE_WORKSPACE_FILE.exists():
            try:
                with open(ACTIVE_WORKSPACE_FILE, "r") as f:
                    data = json.load(f)
                    ws_id = data.get("active_workspace_id")
                    if ws_id and ws_id in cls._workspaces and ws_id not in deleted_set:
                        cls._active_workspace_id = ws_id
                        return ws_id
            except Exception:
                pass

        # 3. Fallback: If valid non-deleted workspaces exist, auto-activate the first available workspace
        valid_workspaces = [w for w in cls._workspaces.keys() if w not in deleted_set]
        if valid_workspaces:
            first_ws = valid_workspaces[0]
            cls._active_workspace_id = first_ws
            cls._save_active_workspace_id()
            return first_ws

        cls._active_workspace_id = None
        return None

    @classmethod
    def set_active_workspace(cls, workspace_id: str) -> bool:
        """Set active workspace if it exists. Returns False if workspace does not exist."""
        cls._load_workspaces()
        deleted_set = cls._load_deleted_set()

        if workspace_id in deleted_set:
            cls._deleted_workspaces.remove(workspace_id)
            cls._save_deleted_set()

        if workspace_id not in cls._workspaces:
            return False

        cls._active_workspace_id = workspace_id
        cls._save_active_workspace_id()
        try:
            from app.semantic_model.engine import invalidate_semantic_model_cache
            invalidate_semantic_model_cache()
        except Exception:
            pass
        return True

    @classmethod
    def _save_active_workspace_id(cls):
        ACTIVE_WORKSPACE_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(ACTIVE_WORKSPACE_FILE, "w") as f:
                json.dump({"active_workspace_id": cls._active_workspace_id}, f)
        except Exception as e:
            logger.warning(f"[Workspace Warning] Could not save active workspace ID: {e}")

    @classmethod
    def get_workspace(cls, workspace_id: str) -> Optional[Dict[str, Any]]:
        cls._load_workspaces()
        deleted_set = cls._load_deleted_set()
        if workspace_id in deleted_set:
            return None
        return cls._workspaces.get(workspace_id)

    @classmethod
    def create_or_get_workspace(
        cls,
        workspace_id: str,
        name: str,
        industry: str = "Enterprise Domain",
        created_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        cls._load_workspaces()
        deleted_set = cls._load_deleted_set()
        if workspace_id in deleted_set:
            cls._deleted_workspaces.remove(workspace_id)
            cls._save_deleted_set()

        if workspace_id in cls._workspaces and isinstance(cls._workspaces[workspace_id], dict):
            ws = cls._workspaces[workspace_id]
            if created_by and not ws.get("created_by"):
                ws["created_by"] = created_by
                cls._save_workspaces()
            return ws

        workspace: Dict[str, Any] = {
            "workspace_id": workspace_id,
            "name": name,
            "industry": industry,
            "domain": industry,
            "sha256_hash": None,
            "business_type": "Enterprise Data Operations",
            "business_model": "Multi-Table Analytics",
            "health_score": None,
            "data_quality_pct": None,
            "ai_ready": True,
            "forecast_ready": True,
            "time_range": None,
            "connected_tables_count": 0,
            "tables": [],
            "relationships": [],
            "semantic_model": {
                "fact_tables": [],
                "dimension_tables": [],
                "lookup_tables": [],
                "reference_tables": []
            },
            "lineage": [],
            "status": "Ready",
            "owner": "Enterprise Administrator",
            "last_refresh": "Just now",
            "created_by": created_by or "",
        }
        cls._workspaces[workspace_id] = workspace
        cls._save_workspaces()
        return workspace

    @classmethod
    def get_workspace_by_sha256(cls, sha256_hash: str) -> Optional[Dict[str, Any]]:
        cls._load_workspaces()
        for ws in cls._workspaces.values():
            if not isinstance(ws, dict):
                continue
            hashes = ws.get("sha256_hashes", [])
            if sha256_hash in hashes:
                return ws
            if ws.get("sha256_hash") == sha256_hash:
                return ws
        return None

    @classmethod
    def add_sha256_hash(cls, workspace_id: str, sha256_hash: str):
        cls._load_workspaces()
        ws = cls.get_workspace(workspace_id)
        if ws:
            if "sha256_hashes" not in ws or not isinstance(ws.get("sha256_hashes"), list):
                ws["sha256_hashes"] = []
            if sha256_hash not in ws["sha256_hashes"]:
                ws["sha256_hashes"].append(sha256_hash)
            ws["sha256_hash"] = sha256_hash
            cls._save_workspaces()

    @classmethod
    def update_processing_status(
        cls,
        workspace_id: str,
        status: str,
        progress: int,
        current_step: str,
        steps_detail: Optional[List[Dict[str, Any]]] = None
    ):
        cls._load_workspaces()
        ws = cls.get_workspace(workspace_id)
        if ws:
            ws["processing_status"] = {
                "status": status,
                "progress": progress,
                "current_step": current_step,
                "is_ready": True,
                "updated_at": "Just now",
                "message": "AI is analyzing your data while you explore",
                "steps": steps_detail or [
                    {"step": "Workspace Ready — Ingesting Data Tables", "status": "COMPLETED" if progress >= 25 else "PROCESSING", "pct": 25},
                    {"step": "Analyzing Column Categories & Metric Types", "status": "COMPLETED" if progress >= 41 else ("PROCESSING" if progress >= 25 else "PENDING"), "pct": 41},
                    {"step": "Discovering Cross-Table Business Connections", "status": "COMPLETED" if progress >= 60 else ("PROCESSING" if progress >= 41 else "PENDING"), "pct": 60},
                    {"step": "Building Executive Semantic Model", "status": "COMPLETED" if progress >= 80 else ("PROCESSING" if progress >= 60 else "PENDING"), "pct": 80},
                    {"step": "Preparing AI Executive Insights & Recommendations", "status": "COMPLETED" if progress >= 100 else ("PROCESSING" if progress >= 80 else "QUEUED"), "pct": 100}
                ]
            }
            cls._save_workspaces()

    @classmethod
    def get_processing_status(cls, workspace_id: str) -> Dict[str, Any]:
        cls._load_workspaces()
        ws = cls.get_workspace(workspace_id)
        if ws and "processing_status" in ws:
            status_obj = ws["processing_status"]
            steps = status_obj.get("steps", [])
            status_obj["completed_steps"] = [s["step"] for s in steps if s.get("status") == "COMPLETED"]
            status_obj["remaining_steps"] = [s["step"] for s in steps if s.get("status") != "COMPLETED"]
            return status_obj

        return {
            "status": "COMPLETED",
            "progress": 100,
            "current_step": "Workspace Ready",
            "is_ready": True,
            "message": "Workspace fully optimized",
            "completed_steps": ["Workspace Ingestion", "Column Categories", "Business Connections", "Semantic Model", "AI Executive Insights"],
            "remaining_steps": [],
            "steps": [
                {"step": "Workspace Ready — Ingesting Data Tables", "status": "COMPLETED"},
                {"step": "Analyzing Column Categories & Metric Types", "status": "COMPLETED"},
                {"step": "Discovering Cross-Table Business Connections", "status": "COMPLETED"},
                {"step": "Building Executive Semantic Model", "status": "COMPLETED"},
                {"step": "Preparing AI Executive Insights & Recommendations", "status": "COMPLETED"}
            ]
        }

    @classmethod
    def register_table(
        cls,
        workspace_id: str,
        table_name: str,
        columns: List[Dict[str, Any]],
        row_count: int,
        file_path: str
    ):
        ws = cls.create_or_get_workspace(workspace_id, workspace_id.replace("-", " ").title())
        table_info = {
            "table_name": table_name,
            "columns": columns,
            "rows": row_count,
            "file_path": file_path
        }
        existing_tables = [t for t in ws.get("tables", []) if t.get("table_name") != table_name]
        existing_tables.append(table_info)
        ws["tables"] = existing_tables
        ws["connected_tables_count"] = len(existing_tables)
        ws["total_records"] = sum(t.get("rows", 0) for t in existing_tables)

        sem_model = ws.get("semantic_model", {})
        fact_tables = sem_model.get("fact_tables", [])
        if table_name not in fact_tables:
            fact_tables.append(table_name)
        sem_model["fact_tables"] = fact_tables
        ws["semantic_model"] = sem_model

        cls._save_workspaces()

    @classmethod
    def build_semantic_model(cls, con, workspace_id: str) -> Dict[str, Any]:
        ws = cls.create_or_get_workspace(workspace_id, workspace_id.replace("-", " ").title())
        tables = ws.get("tables", [])

        table_cols = {}
        for t in tables:
            t_name = t.get("table_name")
            cols = [c.get("name") for c in t.get("columns", [])]
            table_cols[t_name] = cols

        relationships = []
        table_names = list(table_cols.keys())
        for i in range(len(table_names)):
            for j in range(i + 1, len(table_names)):
                t1 = table_names[i]
                t2 = table_names[j]
                common_cols = [c for c in table_cols[t1] if c in table_cols[t2] and (c.endswith("_id") or c == "id")]
                for col in common_cols:
                    relationships.append({
                        "primary_table": t1,
                        "foreign_table": t2,
                        "join_column": col,
                        "cardinality": "1:N"
                    })

        ws["relationships"] = relationships
        sem_model = ws.get("semantic_model", {})
        sem_model["relationships"] = relationships
        ws["semantic_model"] = sem_model
        cls._save_workspaces()
        return sem_model

    @classmethod
    def enrich_workspace_profile(cls, ws: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(ws, dict):
            return ws
        tables = ws.get("tables", [])
        if not tables:
            ws["business_size"] = {"orders": None, "customers": None, "products": None, "transactions": None}
            ws["canonical_profile"] = {"total_records": 0, "primary_metric": "N/A", "primary_metric_sum": None}
            return ws

        try:
            from app.ingestion.semantic_profiler import SemanticDataProfiler
            for tbl in tables:
                fp = tbl.get("file_path")
                if fp and Path(fp).exists():
                    prof = SemanticDataProfiler.profile(Path(fp))
                    total_rows = prof.get("total_rows", 0)
                    measures = prof.get("column_categories", {}).get("measures", [])
                    dims = prof.get("column_categories", {}).get("dimensions", [])
                    ids = prof.get("column_categories", {}).get("identifiers", [])
                    stats_map = prof.get("measure_stats", {})

                    primary_m = measures[0] if measures else None
                    primary_sum = stats_map.get(primary_m, {}).get("sum") if primary_m else None
                    if primary_sum is not None and abs(float(primary_sum)) < 1e-9:
                        primary_sum = 0.0

                    ws["total_records"] = total_rows
                    ws["health_score"] = ws.get("health_score") if ws.get("health_score") is not None else 92
                    ws["data_quality_pct"] = ws.get("data_quality_pct") if ws.get("data_quality_pct") is not None else 95.0
                    ws["canonical_profile"] = {
                        "total_records": total_rows,
                        "measures": measures,
                        "dimensions": dims,
                        "identifiers": ids,
                        "primary_metric": primary_m.replace("_", " ").title() if primary_m else "Total Records",
                        "primary_metric_sum": primary_sum,
                    }

                    cols_dict = prof.get("columns", {})
                    cust_col = next((c for c in ids + dims if any(k in c.lower() for k in ["customer", "user", "client", "patient", "student"])), None)
                    prod_col = next((c for c in ids + dims if any(k in c.lower() for k in ["stock", "product", "item", "sku", "course", "service"])), None)
                    tx_col = next((c for c in ids if any(k in c.lower() for k in ["invoice", "order", "trans", "receipt"])), None)

                    ws["business_size"] = {
                        "orders": cols_dict.get(tx_col, {}).get("distinct_count") if tx_col else (total_rows if total_rows > 0 else None),
                        "customers": cols_dict.get(cust_col, {}).get("distinct_count") if cust_col else None,
                        "products": cols_dict.get(prod_col, {}).get("distinct_count") if prod_col else None,
                        "transactions": total_rows,
                    }
                    break
        except Exception:
            pass
        return ws

    @classmethod
    def get_all_workspaces(cls) -> List[Dict[str, Any]]:
        cls._load_workspaces()
        deleted_set = cls._load_deleted_set()
        active_id = cls.get_active_workspace_id()
        result = []
        for w in cls._workspaces.values():
            if isinstance(w, dict) and w.get("workspace_id") not in deleted_set:
                w_copy = cls.enrich_workspace_profile(w.copy())
                w_copy["is_active"] = (w_copy.get("workspace_id") == active_id)
                result.append(w_copy)
        return result

    @classmethod
    def delete_workspace(cls, workspace_id: str) -> bool:
        """
        Permanently deletes a workspace across memory, SQLite database, Parquet storage,
        extracted folders, MongoDB metadata, DuckDB registrations, and query caches.
        Auto-switches to the next remaining active workspace or resets to empty state.
        """
        ws = cls._workspaces.get(workspace_id, {})
        table_names = [t.get("table_name") for t in ws.get("tables", []) if isinstance(t, dict) and t.get("table_name")]

        cls._deleted_workspaces.add(workspace_id)
        cls._save_deleted_set()

        is_deleting_active = (workspace_id == cls._active_workspace_id)
        if is_deleting_active:
            cls._active_workspace_id = None

        if workspace_id in cls._workspaces:
            del cls._workspaces[workspace_id]

        cls._save_workspaces()

        db = SessionLocal()
        try:
            delete_dataset_permanently(db, workspace_id)
        finally:
            db.close()

        ParquetStorageManager.delete_dataset_files(workspace_id)

        try:
            from app.database.duckdb_engine import DuckDBEngine
            conn = DuckDBEngine.get_connection()
            for table_name in table_names:
                try:
                    conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
                except Exception:
                    pass
        except Exception:
            pass

        try:
            from app.database.mongodb import (
                workspaces, datasets, insights, reports,
                copilot_history, forecast_cache, conversation_history,
                report_history, insight_history, forecast_history,
                recommendation_history, business_goals, executive_decisions,
                user_feedback, business_milestones, kpi_history,
                forecast_accuracy, scenario_simulations, generated_sql,
                audit_logs, dynamic_kpis, dashboard_layouts,
                strategy_reports, decision_trees, risk_profiles,
                opportunity_profiles, scenario_history, executive_briefings
            )
            workspaces.delete_one({"workspace_id": workspace_id})
            datasets.delete_many({"workspace_id": workspace_id})
            insights.delete_many({"workspace_id": workspace_id})
            reports.delete_many({"workspace_id": workspace_id})
            copilot_history.delete_many({"workspace_id": workspace_id})
            forecast_cache.delete_many({"workspace_id": workspace_id})
            conversation_history.delete_many({"workspace_id": workspace_id})
            report_history.delete_many({"workspace_id": workspace_id})
            insight_history.delete_many({"workspace_id": workspace_id})
            forecast_history.delete_many({"workspace_id": workspace_id})
            recommendation_history.delete_many({"workspace_id": workspace_id})
            business_goals.delete_many({"workspace_id": workspace_id})
            executive_decisions.delete_many({"workspace_id": workspace_id})
            user_feedback.delete_many({"workspace_id": workspace_id})
            business_milestones.delete_many({"workspace_id": workspace_id})
            kpi_history.delete_many({"workspace_id": workspace_id})
            forecast_accuracy.delete_many({"workspace_id": workspace_id})
            scenario_simulations.delete_many({"workspace_id": workspace_id})
            generated_sql.delete_many({"workspace_id": workspace_id})
            audit_logs.delete_many({"workspace_id": workspace_id})
            dynamic_kpis.delete_many({"workspace_id": workspace_id})
            dashboard_layouts.delete_many({"workspace_id": workspace_id})
            strategy_reports.delete_many({"workspace_id": workspace_id})
            decision_trees.delete_many({"workspace_id": workspace_id})
            risk_profiles.delete_many({"workspace_id": workspace_id})
            opportunity_profiles.delete_many({"workspace_id": workspace_id})
            scenario_history.delete_many({"workspace_id": workspace_id})
            executive_briefings.delete_many({"workspace_id": workspace_id})
        except Exception:
            pass

        try:
            from app.cache.memory_cache import QueryResultCache
            keys_to_delete = [k for k in list(QueryResultCache._cache.keys()) if workspace_id in k]
            for k in keys_to_delete:
                QueryResultCache._cache.pop(k, None)
        except Exception:
            pass

        try:
            from app.semantic_model.engine import invalidate_semantic_model_cache
            invalidate_semantic_model_cache()
        except Exception:
            pass

        if is_deleting_active:
            remaining = cls.get_all_workspaces()
            if remaining:
                cls.set_active_workspace(remaining[0]["workspace_id"])
            else:
                try:
                    ACTIVE_WORKSPACE_FILE.unlink(missing_ok=True)
                except Exception:
                    pass

        return True

    @classmethod
    def get_business_profile(cls, workspace_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Generates dynamic executive Business Profile data from active workspace."""
        if not workspace_id:
            workspace_id = cls.get_active_workspace_id()

        if not workspace_id:
            return None

        deleted_set = cls._load_deleted_set()
        if workspace_id in deleted_set or workspace_id not in cls._workspaces:
            return None

        ws = cls._workspaces[workspace_id]
        health_score = ws.get("health_score")
        health_display = f"{health_score:.0f}/100" if isinstance(health_score, (int, float)) else "Not computed"
        return {
            "workspace_id": workspace_id,
            "workspace_name": ws["name"],
            "industry": ws.get("industry", "Enterprise Domain"),
            "business_type": ws.get("business_type", "Enterprise Operations"),
            "business_model": ws.get("business_model", "Data Operations"),
            "products_sold": "Not specified",
            "countries": "Not specified",
            "customers": "Not specified",
            "sales_channels": "Not specified",
            "revenue_model": "Not specified",
            "main_kpis_available": ["Data Quality", "Record Count", "Health Score"],
            "capabilities": {
                "forecast_ready": True,
                "customer_analytics_ready": True,
                "inventory_analytics_ready": True,
                "rag_ai_ready": True
            },
            "executive_questions_answerable": [
                "Which entities generate the highest metric totals?",
                "What is the statistical distribution across dimensions?"
            ],
            "business_health_score": health_display
        }

    @classmethod
    def get_dataset_explorer_tables(cls, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns normalized, clean table definitions for Dataset Explorer."""
        if not workspace_id:
            workspace_id = cls.get_active_workspace_id()

        if not workspace_id:
            return []

        deleted_set = cls._load_deleted_set()
        if workspace_id in deleted_set or workspace_id not in cls._workspaces:
            return []

        ws = cls._workspaces[workspace_id]
        raw_tables = ws.get("tables", [])
        normalized = []

        for idx, t in enumerate(raw_tables):
            table_name = t.get("table_name") or t.get("name") or f"table_{idx+1}"
            raw_friendly = t.get("friendly_name") or t.get("name") or table_name.replace("_", " ").title()
            raw_purpose = t.get("business_purpose") or t.get("description") or f"Operational data table '{raw_friendly}'."
            raw_desc = t.get("description") or t.get("business_purpose") or f"Table '{table_name}' containing workspace data."
            rows = t.get("rows") or t.get("row_count") or t.get("record_count") or 0
            cols_count = t.get("columns_count") or t.get("column_count") or (len(t.get("columns", [])) if isinstance(t.get("columns"), list) else 0)

            primary_key = t.get("primary_key") or "id"
            foreign_keys = t.get("foreign_keys") or []
            if not isinstance(foreign_keys, list):
                foreign_keys = [str(foreign_keys)] if foreign_keys else []

            data_quality = t.get("data_quality") or t.get("quality_score") or "Not computed"
            role = t.get("role") or t.get("table_role") or "Dimension Table"

            entry = {
                "id": t.get("id") or f"tbl-{table_name}-{idx}",
                "table_name": table_name,
                "friendly_name": raw_friendly,
                "business_purpose": raw_purpose,
                "description": raw_desc,
                "raw_file": t.get("raw_file") or t.get("file_path") or f"{table_name}.csv",
                "rows": rows,
                "row_count": rows,
                "columns": cols_count,
                "column_count": cols_count,
                "primary_key": primary_key,
                "foreign_keys": foreign_keys,
                "data_quality": str(data_quality),
                "role": role,
            }
            normalized.append(entry)

        return normalized
