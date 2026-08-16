from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from fastapi import HTTPException
import threading
import logging

from app.database.connection import SessionLocal
from app.database.storage import ParquetStorageManager
from app.database.duckdb_engine import DuckDBEngine
from app.analytics.universal_engine import UniversalAnalyticsEngine
from app.ingestion.workspace_discovery import WorkspaceDiscoveryEngine
from app.ingestion.semantic_profiler import SemanticDataProfiler
from app.semantic_model import build_semantic_model, invalidate_semantic_model_cache
from app.semantic_model.core import SemanticModel
from app.schemas.analytics import AnalyticsResult, HealthScore
from app.dashboard.storyteller import UniversalDashboardStoryteller
from app.dashboard.cards import _safe_str
from app.ai.universal_copilot_brain import UniversalAIBrain
from app.cache.memory_cache import TTLCache
from app.logging.logger import get_logger
from app.logging.logger import get_logger
from app.validation.chart_validator import validate_charts

logger = get_logger(__name__)
_dashboard_cache = TTLCache(maxsize=32, ttl=60.0)


class DynamicDashboardService:
    _dashboard_cache = _dashboard_cache


_NUMERIC_TYPE_KEYWORDS = ["BIGINT", "INTEGER", "INT", "SMALLINT", "TINYINT", "DOUBLE", "FLOAT", "DECIMAL", "HUGEINT", "REAL"]
_SYSTEM_FILE_PREFIXES = ("sample-", "unified_", "tmp_")
_MEASURE_COLUMN_KEYWORDS = [
    "price", "amount", "revenue", "sales", "cost", "profit", "quantity", "value",
    "duration", "probability", "risk", "likelihood", "margin", "discount", "fee",
    "income", "expense", "balance", "payout", "premium", "claim", "payment",
    "freight", "shipping", "tax", "score", "grade", "weight", "length", "height",
    "width", "depth", "count", "total", "sum", "avg", "mean", "installment",
    "sequential", "photos_qty", "description_length", "name_length",
    "lat", "lng", "latitude", "longitude",
]


def _is_measure_column(col_name: str) -> bool:
    col_lower = col_name.lower()
    for kw in _MEASURE_COLUMN_KEYWORDS:
        if kw in col_lower:
            return True
    return False


def _score_parquet_candidate(pfile: Path) -> Tuple[int, int, int]:
    numeric_cols = 0
    row_count = 0
    conn = DuckDBEngine.get_connection()
    try:
        schema = conn.execute(f"DESCRIBE SELECT * FROM read_parquet('{pfile.as_posix()}')").fetchall()
        numeric_cols = sum(1 for c in schema if any(nt in c[1].upper() for nt in _NUMERIC_TYPE_KEYWORDS))
        row_count = conn.execute(f"SELECT COUNT(*) FROM read_parquet('{pfile.as_posix()}')").fetchone()[0]
    except Exception as e:
        logger.debug(f"Parquet candidate scoring failed for {pfile}: {str(e)}")
    finally:
        conn.close()
    return numeric_cols, row_count, numeric_cols * 100000 + row_count


def _profile_table_score(pfile: Path) -> Tuple[int, int]:
    measure_cols = 0
    row_count = 0
    try:
        profile = SemanticDataProfiler.profile(pfile)
        row_count = profile.get("total_rows", 0)
        for col_name, col_info in profile.get("columns", {}).items():
            col_type = col_info.get("data_type", "").upper()
            if any(nt in col_type for nt in _NUMERIC_TYPE_KEYWORDS) and _is_measure_column(col_name):
                measure_cols += 1
    except Exception as e:
        logger.debug(f"Profile table score failed for {pfile}: {str(e)}")
    return measure_cols, row_count


def _table_has_temporal(pfile: Path) -> bool:
    try:
        profile = SemanticDataProfiler.profile(pfile)
        temporal = profile.get("column_categories", {}).get("temporal", [])
        if temporal:
            return True
        for col_name, col_info in profile.get("columns", {}).items():
            col_type = col_info.get("data_type", "").upper()
            if any(dt in col_type for dt in ["DATE", "TIME", "TIMESTAMP"]):
                return True
            if any(kw in col_name.lower() for kw in ["date", "timestamp", "time", "created", "updated", "delivered", "approved", "shipping"]):
                return True
    except Exception as e:
        logger.debug(f"Temporal detection failed for {pfile}: {str(e)}")
    return False


def _table_has_measures(pfile: Path) -> bool:
    try:
        profile = SemanticDataProfiler.profile(pfile)
        measures = profile.get("column_categories", {}).get("measures", [])
        if measures:
            return True
        for col_name, col_info in profile.get("columns", {}).items():
            col_type = col_info.get("data_type", "").upper()
            if any(nt in col_type for nt in _NUMERIC_TYPE_KEYWORDS) and _is_measure_column(col_name):
                return True
    except Exception as e:
        logger.debug(f"Measure detection failed for {pfile}: {str(e)}")
    return False


def _workspace_prefix_score(pfile: Path, workspace_id: str) -> int:
    clean_ws = workspace_id.lower().replace("-", "_")
    p_stem = pfile.stem.lower().replace("-", "_")
    if p_stem.startswith(clean_ws + "__"):
        return 1000000
    if clean_ws in p_stem:
        return 500000
    return 0


def _find_best_parquet(db, target_workspace_id: Optional[str] = None) -> Optional[Path]:
    from app.database.storage import STORAGE_DIR
    from app.services.workspace_service import EnterpriseWorkspaceManager

    active_ws_id = target_workspace_id or EnterpriseWorkspaceManager.get_active_workspace_id()

    if active_ws_id:
        ws_info = EnterpriseWorkspaceManager.get_workspace(active_ws_id)
        if ws_info and ws_info.get("tables"):
            best_path: Optional[Path] = None
            best_score = 0
            for tbl in ws_info["tables"]:
                fp = tbl.get("file_path")
                if not fp:
                    continue
                p = Path(fp)
                if not p.exists():
                    continue
                if p.name.startswith(_SYSTEM_FILE_PREFIXES):
                    continue
                measure_cols, row_count = _profile_table_score(p)
                ws_prefix_bonus = _workspace_prefix_score(p, active_ws_id)
                score = ws_prefix_bonus + measure_cols * 10000 + row_count
                if score > best_score:
                    best_score = score
                    best_path = p
            if best_path is not None and best_score > 0:
                return best_path

        ws_unified = STORAGE_DIR / f"unified_{active_ws_id}.parquet"
        if ws_unified.exists():
            try:
                if DuckDBEngine.get_row_count(ws_unified) > 0:
                    return ws_unified
            except Exception as e:
                logger.debug(f"Unified parquet check failed for {ws_unified}: {str(e)}")

    best_path = None
    best_score = 0
    for pfile in STORAGE_DIR.glob("*.parquet"):
        if pfile.name.startswith(_SYSTEM_FILE_PREFIXES):
            continue
        if not pfile.exists():
            continue
        measure_cols, row_count = _profile_table_score(pfile)
        ws_prefix_bonus = _workspace_prefix_score(pfile, active_ws_id or "")
        score = ws_prefix_bonus + measure_cols * 10000 + row_count
        if score > best_score:
            best_score = score
            best_path = pfile

    return best_path


def get_dynamic_dashboard(dataset_id: Optional[str] = None, workspace_id: Optional[str] = None, return_analytics_result: bool = False):
    db = SessionLocal()
    try:
        from app.services.workspace_service import EnterpriseWorkspaceManager
        target_ws_id = workspace_id or (dataset_id if (dataset_id and dataset_id != "latest") else EnterpriseWorkspaceManager.get_active_workspace_id())

        if target_ws_id:
            EnterpriseWorkspaceManager.set_active_workspace(target_ws_id)

        parquet_path: Optional[Path] = None
        if dataset_id and dataset_id != "latest":
            parquet_path = ParquetStorageManager.get_parquet_path(dataset_id)
            if not parquet_path or not parquet_path.exists():
                parquet_path = _find_best_parquet(db, target_workspace_id=dataset_id)
        else:
            parquet_path = _find_best_parquet(db, target_workspace_id=target_ws_id)

        if not parquet_path or not parquet_path.exists():
            has_workspace = bool(EnterpriseWorkspaceManager.get_active_workspace_id())
            if not has_workspace:
                message = "No workspaces yet. Create a workspace by uploading a CSV, Excel, or Parquet file to begin analysis."
            else:
                message = "No dataset available in the current workspace. Upload a CSV, Excel, or Parquet file to generate executive analytics."
            res = {
                "workspace_exists": has_workspace,
                "message": message,
                "kpis": [],
                "action_center": [],
                "executive_newsfeed": [],
                "charts": [],
                "insights": [],
                "executive_briefing": {
                    "greeting": "No Workspaces Yet" if not has_workspace else "No Data Available",
                    "business_name": EnterpriseWorkspaceManager.get_active_workspace_id() or "Active Workspace",
                    "health_score": 0,
                    "primary_metric": "N/A",
                    "status": "No Data",
                    "main_opportunity": "Upload a dataset to unlock insights.",
                    "biggest_risk": "No data to assess.",
                    "forecast": "N/A",
                    "ai_confidence": "N/A",
                },
                "health_score": None,
                "profile": {}
            }
            if return_analytics_result:
                return res, None
            return res

        active_ws = EnterpriseWorkspaceManager.get_active_workspace_id() or ""
        cache_key = f"dashboard:{active_ws}:{parquet_path}"
        cached = _dashboard_cache.get(cache_key, workspace_id=active_ws)
        if cached is not None:
            if return_analytics_result:
                return cached, None
            return cached

        sem_model = {}
        domain = "Generic Business"
        try:
            sm = build_semantic_model(workspace_id=active_ws, force_rebuild=False)
            if isinstance(sm, dict):
                sem_model = sm
                domain = sm.get("domain", domain)
            else:
                domain = sm.domain
        except Exception as e:
            logger.warning(f"Semantic model build failed for workspace {active_ws}: {str(e)}")
            sm = SemanticModel(workspace_id=active_ws, domain=domain, dataset_type="Unknown")

        if isinstance(sem_model, dict) and sem_model.get("is_lookup_only"):
            warning = {"message": "Uploaded dataset is a lookup table."}
            result = {
                "workspace_exists": True,
                "is_lookup_only": True,
                "dataset_type": "Lookup / Reference Table",
                "lookup_table_warning": warning,
                "message": warning.get("message", "No operational transactions detected."),
                "kpis": [],
                "charts": [],
                "action_center": [],
                "executive_newsfeed": [],
                "insights": [],
                "executive_briefing": {
                    "greeting": "Reference / Lookup Data Ingested",
                    "summary": warning.get("message", "No operational transactions detected.")
                },
                "health_score": None,
                "profile": {}
            }
            _dashboard_cache.set(cache_key, result, ttl=60.0)
            return result

        if isinstance(sem_model, dict):
            sm = SemanticModel(
                workspace_id=active_ws,
                domain=domain,
                dataset_type=sem_model.get("dataset_type", "Unknown"),
                is_lookup_only=sem_model.get("is_lookup_only", False),
            )
        else:
            sm = sem_model

        analytics_result = None
        analytics_dict = {}
        try:
            analytics_result = UniversalAnalyticsEngine.analyze(sm, parquet_path=parquet_path, dataset_id=dataset_id)
            analytics_dict = analytics_result.to_dict()
        except Exception as e:
            logger.error(f"Analytics engine failed for dataset {dataset_id}: {str(e)}")
            analytics_result = AnalyticsResult(
                domain=domain,
                dataset_type=getattr(sm, "dataset_type", "Unknown"),
                semantic_model=sm,
                health_score=HealthScore(overall_score=0.0, grade="N/A", status="Error", breakdown=[]),
                errors=[f"Analytics engine failed: {str(e)}"],
            )
            analytics_dict = analytics_result.to_dict()

        profile = {}
        try:
            from app.intelligence.dataset_intelligence_layer import DatasetIntelligenceLayer
            ws_id = EnterpriseWorkspaceManager.get_active_workspace_id()
            if ws_id:
                cached = DatasetIntelligenceLayer.get_cached(ws_id)
                if cached is not None:
                    profile = {
                        "total_rows": cached.profile.total_records,
                        "total_columns": cached.profile.total_columns,
                        "column_categories": {
                            "measures": cached.profile.detected_measures,
                            "dimensions": cached.profile.detected_dimensions,
                            "temporal": cached.profile.detected_temporal,
                            "identifiers": [c.name for c in cached.columns if c.is_identifier],
                        },
                        "columns": {
                            c.name: {
                                "data_type": c.data_type,
                                "category": "measure" if c.is_measure else "dimension" if c.is_dimension else "temporal" if c.is_temporal else "identifier" if c.is_identifier else "dimension",
                                "null_percentage": c.null_percentage,
                                "distinct_count": c.distinct_count,
                            }
                            for c in cached.columns
                        },
                    }
        except Exception as e:
            logger.debug(f"Semantic profiling failed for {parquet_path}: {str(e)}")

        sql_query = _safe_str(analytics_dict.get("sql_query", ""), "")
        tables_used = analytics_dict.get("tables_used", []) or ([parquet_path.name] if parquet_path else [])
        columns_used = analytics_dict.get("columns_used", []) or []
        evidence_rows = []
        evidence_items = []
        rows_returned = 0

        prediction_result = None
        try:
            from app.ml.prediction_engine import UniversalPredictionEngine
            from types import SimpleNamespace
            partial = SimpleNamespace(
                trends=analytics_dict.get("trends", {}) or {},
                correlations=analytics_dict.get("correlations", []) or [],
                root_causes=analytics_dict.get("root_causes", []) or [],
                drivers=analytics_dict.get("drivers", []) or [],
                anomalies=analytics_dict.get("anomalies", []) or [],
                outliers=analytics_dict.get("outliers", []) or [],
                kpis=analytics_dict.get("kpis", []) or [],
                volume=analytics_dict.get("volume", 0) or 0,
                confidence_score=analytics_dict.get("confidence_score", 0.0) or 0.0,
                evidence=analytics_dict.get("evidence", {}) or {},
            )
            prediction_result = UniversalPredictionEngine.generate(
                analytics_result=partial,
                semantic_model=sm,
            )
        except Exception as e:
            logger.warning(f"Prediction engine failed for dataset {dataset_id}: {str(e)}")

        dashboard = UniversalDashboardStoryteller.generate(
            analytics_result=analytics_result,
            prediction_result=prediction_result,
            executive_report=None,
            parquet_path=parquet_path,
            profile=profile,
            dataset_id=dataset_id or "latest",
            workspace_id=active_ws,
            sql_query=sql_query,
            tables_used=tables_used,
            columns_used=columns_used,
            evidence_items=evidence_items,
            rows_returned=rows_returned,
        )

        result = dashboard.model_dump() if hasattr(dashboard, "model_dump") else dashboard.__dict__
        result["errors"] = result.get("errors", []) or []
        if "charts" in result and result["charts"]:
            result["charts"] = validate_charts(result["charts"])
        _dashboard_cache.set(cache_key, result, ttl=60.0, workspace_id=active_ws)
        if return_analytics_result:
            return result, analytics_result
        return result
    finally:
        db.close()
