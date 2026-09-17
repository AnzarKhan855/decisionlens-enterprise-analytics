from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.analytics.universal_engine import UniversalAnalyticsEngine
from app.cache.memory_cache import TTLCache
from app.core.rbac import require_permission
from app.database.mongodb import insights as mongo_insights
from app.logging.logger import get_logger
from app.semantic_model.core import SemanticModel
from app.services.analytics_cache_service import AnalyticsCacheService
from app.services.dynamic_dashboard_service import get_dynamic_dashboard
from app.services.workspace_service import EnterpriseWorkspaceManager

logger = get_logger(__name__)


router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
    dependencies=[Depends(require_permission("view_dashboards"))]
)

_cache = TTLCache(maxsize=4, ttl=30.0)


def _get_parquet_path(workspace_id: Optional[str] = None) -> Optional[Path]:
    from app.database.storage import STORAGE_DIR, ParquetStorageManager
    target_ws = workspace_id or EnterpriseWorkspaceManager.get_active_workspace_id()
    if not target_ws:
        return None

    # 1. Check workspace registered tables
    ws = EnterpriseWorkspaceManager.get_workspace(target_ws)
    if ws and ws.get("tables"):
        for t in ws["tables"]:
            fp = t.get("file_path")
            if fp:
                p = Path(fp)
                if p.exists():
                    return p
                alt = STORAGE_DIR / p.name
                if alt.exists():
                    return alt

    # 2. Check ParquetStorageManager workspace resolution
    ws_path = ParquetStorageManager.get_parquet_path_for_workspace(target_ws)
    if ws_path and ws_path.exists():
        return ws_path

    # 3. Check unified dataset
    unified = STORAGE_DIR / f"unified_{target_ws}.parquet"
    if unified.exists():
        return unified

    # 4. Check direct dataset id
    direct = STORAGE_DIR / f"{target_ws}.parquet"
    if direct.exists():
        return direct

    return None


def _get_or_build_semantic_model(workspace_id: Optional[str] = None) -> SemanticModel:
    try:
        from app.semantic_model import build_semantic_model
        target_ws = workspace_id or EnterpriseWorkspaceManager.get_active_workspace_id()
        if target_ws:
            model = build_semantic_model(workspace_id=target_ws, force_rebuild=False)
            if isinstance(model, dict):
                return SemanticModel(
                    workspace_id=target_ws,
                    domain=model.get("domain", "Generic Business"),
                    dataset_type=model.get("dataset_type", "Unknown"),
                    is_lookup_only=model.get("is_lookup_only", False),
                )
            return model
    except Exception as exc:
        logger.warning("[Semantic Model] Fallback to empty model: %s", exc)
    return SemanticModel(workspace_id="fallback", domain="Generic Business", dataset_type="Unknown")


def _load_profile(workspace_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    try:
        from app.intelligence.dataset_intelligence_layer import DatasetIntelligenceLayer
        target_ws = workspace_id or EnterpriseWorkspaceManager.get_active_workspace_id()
        if target_ws:
            cached = DatasetIntelligenceLayer.get_cached(target_ws)
            if cached is not None:
                return {
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
        logger.debug("[UniversalAnalytics] Could not load cached profile: %s", e)
    return None


@router.get("/universal/{workspace_id}")
def universal_analytics_by_workspace(workspace_id: str):
    try:
        cached = AnalyticsCacheService.get_cached(workspace_id)
        if cached is not None:
            return cached

        path = _get_parquet_path(workspace_id)
        if not path or not path.exists():
            return {"error": "No dataset available", "workspace_id": workspace_id}

        model = _get_or_build_semantic_model(workspace_id)
        profile = _load_profile(workspace_id)

        result = UniversalAnalyticsEngine.analyze(
            model,
            parquet_path=path,
            workspace_id=workspace_id,
            profile=profile,
        )
        result_dict = result.to_dict()

        AnalyticsCacheService.set_cached(workspace_id, result_dict)

        try:
            mongo_insights.update_one(
                {"dataset_id": workspace_id},
                {
                    "$set": {
                        "dataset_id": workspace_id,
                        "domain": result_dict.get("domain"),
                        "confidence": result_dict.get("confidence_score"),
                        "insights": result_dict.get("critical_findings", []),
                        "analytics": result_dict,
                        "generated_at": result_dict.get("generated_at"),
                    }
                },
                upsert=True,
            )
        except Exception as mongo_exc:
            logger.warning("[MongoDB Analytics] %s", mongo_exc)

        return result_dict
    except Exception as exc:
        logger.error("[Universal Analytics] %s", exc)
        raise HTTPException(status_code=500, detail="Unable to run universal analytics.")


@router.get("/universal")
def universal_analytics():
    try:
        ws_id = EnterpriseWorkspaceManager.get_active_workspace_id()
        if not ws_id:
            return {"error": "No active workspace"}
        return universal_analytics_by_workspace(ws_id)
    except Exception as exc:
        logger.error("[Universal Analytics] %s", exc)
        raise HTTPException(status_code=500, detail="Unable to run universal analytics.")


@router.get("/kpis")
def get_analytics_kpis():
    try:
        dash = get_dynamic_dashboard()
        return {"kpis": dash.get("kpis", [])}
    except Exception as exc:
        logger.warning("[Analytics KPIs] %s", exc)
        return {"kpis": []}


@router.get("/strategic-decisions")
def get_strategic_decisions(
    dataset_id: Optional[str] = Query(None),
    workspace_id: Optional[str] = Query(None),
):
    try:
        from app.services.enterprise_strategy_engine import EnterpriseStrategyEngine
        target_ws = workspace_id or dataset_id or EnterpriseWorkspaceManager.get_active_workspace_id()
        if not target_ws:
            return {"decisions": [], "ceo_health_scorecard": None}
        report = EnterpriseStrategyEngine.analyze(target_ws)
        recs = report.get("recommendations", [])
        mapped_decisions = []
        for i, r in enumerate(recs):
            mapped_decisions.append({
                "id": r.get("id", f"DEC-{i+1:03d}"),
                "title": r.get("title", ""),
                "category": r.get("category", "Executive Strategy"),
                "priority": r.get("priority", "HIGH"),
                "reason": r.get("reason", ""),
                "action": r.get("action", ""),
                "expected_impact": r.get("expected_impact", "Performance Improvement"),
                "estimated_roi": r.get("estimated_roi", "Positive ROI"),
                "confidence": r.get("confidence", 85.0),
                "risk_level": r.get("risk_level", "LOW"),
            })
        return {
            "decisions": mapped_decisions,
            "ceo_health_scorecard": {
                "overall_health": report.get("confidence_score", 85.0),
                "strategic_priorities": len(mapped_decisions),
                "domain": report.get("domain", "Enterprise"),
            },
        }
    except Exception as exc:
        logger.error("[Strategic Decisions API] %s", exc)
        return {"decisions": [], "ceo_health_scorecard": None}


dashboard_router = APIRouter(tags=["Dynamic Dashboard"])


@dashboard_router.get("/dashboard/dynamic")
def get_dynamic_dashboard_endpoint(
    dataset_id: Optional[str] = Query(None),
    workspace_id: Optional[str] = Query(None)
):
    try:
        data = get_dynamic_dashboard(dataset_id=dataset_id, workspace_id=workspace_id)
        return data
    except Exception as exc:
        logger.error("[Dynamic Dashboard] %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate dynamic dashboard.")
