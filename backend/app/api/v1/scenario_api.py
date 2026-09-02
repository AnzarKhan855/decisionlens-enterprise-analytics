from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from app.services.strategy_engine import StrategyDecisionEngine
from app.services.scenario_lever_engine import ScenarioLeverEngine
from app.ingestion.semantic_profiler import SemanticDataProfiler
from app.database.connection import SessionLocal
from app.database.crud import get_latest_dataset
from app.database.storage import ParquetStorageManager
from app.core.rbac import require_permission
from app.logging.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/analytics",
    tags=["Scenario Simulation"],
    dependencies=[Depends(require_permission("view_dashboards"))]
)


class ScenarioRequest(BaseModel):
    price_change_pct: float = 0.0
    marketing_change_pct: float = 0.0
    discount_reduction_pct: float = 0.0
    inventory_change_pct: float = 0.0
    shipping_reduction_pct: float = 0.0
    return_rate_change_pct: float = 0.0
    elasticity_overrides: Optional[Dict[str, float]] = None


class ScenarioChange(BaseModel):
    lever_id: str
    change_pct: float


class ScenarioSimulateRequest(BaseModel):
    changes: List[ScenarioChange]


def _get_parquet_path(db, dataset_id: Optional[str] = None, workspace_id: Optional[str] = None):
    if dataset_id and dataset_id != "latest":
        direct = ParquetStorageManager.get_parquet_path(dataset_id)
        if direct and direct.exists():
            return direct
        workspace_path = ParquetStorageManager.get_parquet_path_for_workspace(dataset_id)
        if workspace_path and workspace_path.exists():
            return workspace_path

    if workspace_id:
        ws_path = ParquetStorageManager.get_parquet_path_for_workspace(workspace_id)
        if ws_path and ws_path.exists():
            return ws_path

    try:
        from app.services.workspace_service import EnterpriseWorkspaceManager
        active_ws = EnterpriseWorkspaceManager.get_active_workspace_id()
        if active_ws:
            ws_path = ParquetStorageManager.get_parquet_path_for_workspace(active_ws)
            if ws_path and ws_path.exists():
                return ws_path
    except Exception:
        pass

    latest = get_latest_dataset(db)
    if latest:
        file_path = getattr(latest, "file_path", None)
        if file_path:
            from pathlib import Path
            fp = Path(file_path)
            if fp.exists():
                return fp
        parquet_path = ParquetStorageManager.get_parquet_path(str(latest.id))
        if parquet_path and parquet_path.exists():
            return parquet_path

    return None


def _get_workspace_id(db, dataset_id: Optional[str] = None, workspace_id: Optional[str] = None) -> str:
    target = workspace_id or dataset_id
    if target and target != "latest":
        return target

    try:
        from app.services.workspace_service import EnterpriseWorkspaceManager
        active_ws = EnterpriseWorkspaceManager.get_active_workspace_id()
        if active_ws:
            return active_ws
    except Exception:
        pass

    latest = get_latest_dataset(db)
    if latest:
        return str(latest.workspace_id) if hasattr(latest, "workspace_id") else str(latest.id)
    return "default"


def _build_semantic_model(workspace_id: str):
    try:
        from app.semantic_model.engine import build_semantic_model
        return build_semantic_model(workspace_id=workspace_id, force_rebuild=False)
    except Exception as exc:
        logger.warning("[Scenario] Failed to build semantic model for %s: %s", workspace_id, exc)
        return None


def _build_analytics_result(parquet_path, workspace_id: str):
    try:
        from app.services.analytics_cache_service import AnalyticsCacheService
        c_dict = AnalyticsCacheService.get_cached(workspace_id, parquet_path)
        if c_dict:
            from app.schemas.analytics import AnalyticsResult
            return AnalyticsResult.model_validate(c_dict)
    except Exception:
        pass

    try:
        from app.semantic_model.core import SemanticModel
        from app.analytics.universal_engine import UniversalAnalyticsEngine
        sm = SemanticModel(workspace_id=workspace_id, domain="Generic Business", dataset_type="Unknown")
        return UniversalAnalyticsEngine.analyze(sm, parquet_path=parquet_path, workspace_id=workspace_id)
    except Exception as exc:
        logger.warning("[Scenario] Failed to build analytics result for %s: %s", workspace_id, exc)
        return None


_profile_cache_map: Dict[str, Any] = {}

def _get_cached_profile(parquet_path):
    if not parquet_path:
        return {}
    key = str(parquet_path)
    try:
        mtime = parquet_path.stat().st_mtime
    except Exception:
        mtime = 0.0
    if key in _profile_cache_map:
        cached_mtime, prof = _profile_cache_map[key]
        if abs(cached_mtime - mtime) < 1e-4:
            return prof
    prof = SemanticDataProfiler.profile(parquet_path)
    _profile_cache_map[key] = (mtime, prof)
    return prof


@router.get("/scenario/levers")
def get_scenario_levers(dataset_id: Optional[str] = Query(None), workspace_id: Optional[str] = Query(None)):
    """
    Discover dynamically available scenario levers from the uploaded dataset.
    Returns HTTP 200 with empty available_levers list when no dataset is present.
    """
    db = SessionLocal()
    try:
        target_ws = workspace_id or dataset_id
        parquet_path = _get_parquet_path(db, dataset_id, target_ws)
        if not parquet_path:
            return {
                "available_levers": [],
                "unavailable_reasons": ["No dataset uploaded to active workspace yet."],
                "total_columns": 0,
                "total_rows": 0,
                "dataset_id": target_ws or "none"
            }

        ws_id = _get_workspace_id(db, dataset_id, target_ws)
        profile = _get_cached_profile(parquet_path)
        semantic_model = _build_semantic_model(ws_id)
        analytics_result = _build_analytics_result(parquet_path, ws_id)

        result = ScenarioLeverEngine.discover_levers(
            profile=profile,
            semantic_model=semantic_model,
            analytics_result=analytics_result,
        )
        result["dataset_id"] = target_ws or "latest"
        result["workspace_id"] = ws_id
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[Scenario] Lever discovery failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Lever discovery failed: {str(exc)}")
    finally:
        db.close()


@router.post("/scenario/simulate")
def simulate_scenario_data_driven(
    request: ScenarioSimulateRequest,
    dataset_id: Optional[str] = Query(None),
    workspace_id: Optional[str] = Query(None)
):
    """
    Simulate scenario using dynamically discovered levers.
    """
    db = SessionLocal()
    try:
        target_ws = workspace_id or dataset_id
        parquet_path = _get_parquet_path(db, dataset_id, target_ws)
        if not parquet_path:
            raise HTTPException(status_code=400, detail="No dataset uploaded to active workspace. Upload a dataset to run scenario simulation.")
        ws_id = _get_workspace_id(db, dataset_id, target_ws)
        profile = _get_cached_profile(parquet_path)
        semantic_model = _build_semantic_model(ws_id)
        analytics_result = _build_analytics_result(parquet_path, ws_id)

        changes = [c.model_dump() if hasattr(c, "model_dump") else c for c in request.changes]
        result = ScenarioLeverEngine.simulate(
            workspace_id=ws_id,
            changes=changes,
            profile=profile,
            semantic_model=semantic_model,
            analytics_result=analytics_result,
        )
        result["dataset_id"] = target_ws or "latest"
        result["workspace_id"] = ws_id
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[Scenario] Data-driven simulation failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Scenario simulation failed: {str(exc)}")
    finally:
        db.close()


@router.post("/simulate")
def simulate_scenario_legacy(request: ScenarioRequest, dataset_id: Optional[str] = Query(None)):
    """
    Legacy scenario simulation endpoint (backward compatible).
    Falls back to StrategyDecisionEngine when possible, otherwise uses data-driven engine.
    """
    db = SessionLocal()
    try:
        parquet_path = _get_parquet_path(db, dataset_id)
        workspace_id = _get_workspace_id(db, dataset_id)
        profile = SemanticDataProfiler.profile(parquet_path)

        table_name = None
        try:
            from app.database.duckdb_engine import DuckDBEngine
            con = DuckDBEngine.get_connection()
            path_str = str(parquet_path).replace("\\", "/")
            con.execute(f"CREATE OR REPLACE VIEW scenario_view AS SELECT * FROM read_parquet('{path_str}')")
            table_name = "scenario_view"
        except Exception as exc:
            logger.error("[Scenario] Failed to create view: %s", exc)
            raise HTTPException(status_code=500, detail="Unable to prepare dataset for scenario simulation.")

        try:
            from app.database.duckdb_engine import DuckDBEngine
            con = DuckDBEngine.get_connection()
        except Exception as exc:
            logger.error("[Scenario] DuckDB connection failed: %s", exc)
            raise HTTPException(status_code=500, detail="Database connection unavailable.")

        try:
            result = StrategyDecisionEngine.simulate_what_if_scenario(
                con=con,
                table_name=table_name,
                profile=profile,
                price_change_pct=request.price_change_pct,
                marketing_change_pct=request.marketing_change_pct,
                discount_reduction_pct=request.discount_reduction_pct,
                inventory_change_pct=request.inventory_change_pct,
                shipping_reduction_pct=request.shipping_reduction_pct,
                return_rate_change_pct=request.return_rate_change_pct,
                elasticity_overrides=request.elasticity_overrides,
            )
            result["dataset_id"] = dataset_id or "latest"
            result["mode"] = "legacy_retail"
            return result
        except Exception as exc:
            logger.warning("[Scenario] Legacy simulation failed, falling back to data-driven: %s", exc)
            analytics_result = _build_analytics_result(parquet_path, workspace_id)
            semantic_model = _build_semantic_model(workspace_id)
            profile_for_fallback = SemanticDataProfiler.profile(parquet_path)
            levers_result = ScenarioLeverEngine.discover_levers(
                profile=profile_for_fallback,
                semantic_model=semantic_model,
                analytics_result=analytics_result,
            )
            available = levers_result.get("available_levers", [])
            changes = []
            if request.price_change_pct and available:
                changes.append({"lever_id": available[0]["id"], "change_pct": request.price_change_pct})
            if len(available) > 1 and request.marketing_change_pct:
                changes.append({"lever_id": available[1]["id"], "change_pct": request.marketing_change_pct})
            if len(available) > 2 and request.discount_reduction_pct:
                changes.append({"lever_id": available[2]["id"], "change_pct": request.discount_reduction_pct})
            result = ScenarioLeverEngine.simulate(
                workspace_id=workspace_id,
                changes=changes,
                profile=profile_for_fallback,
                semantic_model=semantic_model,
                analytics_result=analytics_result,
            )
            result["dataset_id"] = dataset_id or "latest"
            result["mode"] = "data_driven_fallback"
            return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[Scenario] Simulation failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Scenario simulation failed: {str(exc)}")
    finally:
        db.close()


@router.get("/simulate")
def simulate_scenario_get(
    price_change_pct: float = Query(0.0),
    marketing_change_pct: float = Query(0.0),
    discount_reduction_pct: float = Query(0.0),
    inventory_change_pct: float = Query(0.0),
    shipping_reduction_pct: float = Query(0.0),
    return_rate_change_pct: float = Query(0.0),
    dataset_id: Optional[str] = Query(None),
):
    """
    GET endpoint for scenario simulation (legacy, backward compatible).
    """
    db = SessionLocal()
    try:
        parquet_path = _get_parquet_path(db, dataset_id)
        workspace_id = _get_workspace_id(db, dataset_id)
        profile = SemanticDataProfiler.profile(parquet_path)

        try:
            from app.database.duckdb_engine import DuckDBEngine
            con = DuckDBEngine.get_connection()
            path_str = str(parquet_path).replace("\\", "/")
            con.execute(f"CREATE OR REPLACE VIEW scenario_view AS SELECT * FROM read_parquet('{path_str}')")
            table_name = "scenario_view"
        except Exception as exc:
            logger.error("[Scenario] Failed to create view: %s", exc)
            raise HTTPException(status_code=500, detail="Unable to prepare dataset for scenario simulation.")

        try:
            result = StrategyDecisionEngine.simulate_what_if_scenario(
                con=con,
                table_name=table_name,
                profile=profile,
                price_change_pct=price_change_pct,
                marketing_change_pct=marketing_change_pct,
                discount_reduction_pct=discount_reduction_pct,
                inventory_change_pct=inventory_change_pct,
                shipping_reduction_pct=shipping_reduction_pct,
                return_rate_change_pct=return_rate_change_pct,
            )
            result["dataset_id"] = dataset_id or "latest"
            result["mode"] = "legacy_retail"
            return result
        except Exception as exc:
            logger.warning("[Scenario] Legacy GET simulation failed, falling back to data-driven: %s", exc)
            analytics_result = _build_analytics_result(parquet_path, workspace_id)
            semantic_model = _build_semantic_model(workspace_id)
            profile_for_fallback = SemanticDataProfiler.profile(parquet_path)
            levers_result = ScenarioLeverEngine.discover_levers(
                profile=profile_for_fallback,
                semantic_model=semantic_model,
                analytics_result=analytics_result,
            )
            available = levers_result.get("available_levers", [])
            changes = []
            if price_change_pct and available:
                changes.append({"lever_id": available[0]["id"], "change_pct": price_change_pct})
            if len(available) > 1 and marketing_change_pct:
                changes.append({"lever_id": available[1]["id"], "change_pct": marketing_change_pct})
            if len(available) > 2 and discount_reduction_pct:
                changes.append({"lever_id": available[2]["id"], "change_pct": discount_reduction_pct})
            result = ScenarioLeverEngine.simulate(
                workspace_id=workspace_id,
                changes=changes,
                profile=profile_for_fallback,
                semantic_model=semantic_model,
                analytics_result=analytics_result,
            )
            result["dataset_id"] = dataset_id or "latest"
            result["mode"] = "data_driven_fallback"
            return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[Scenario] Simulation failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Scenario simulation failed: {str(exc)}")
    finally:
        db.close()
