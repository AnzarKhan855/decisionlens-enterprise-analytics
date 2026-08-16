from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Any, Dict, Optional

from app.analytics.universal_engine import UniversalAnalyticsEngine
from app.services.dynamic_kpi_engine import DynamicKPIEngine
from app.semantic_model import build_semantic_model
from app.semantic_model.core import SemanticModel
from app.services.workspace_service import EnterpriseWorkspaceManager
from app.database.mongodb import dynamic_kpis as mongo_dynamic_kpis
from app.database.storage import ParquetStorageManager
from app.core.rbac import require_permission
from app.logging.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/dashboard/intelligence",
    tags=["Dynamic KPI Intelligence"],
    dependencies=[Depends(require_permission("view_dashboards"))]
)


def _get_parquet_path(workspace_id: str) -> Optional[Any]:
    try:
        ws = EnterpriseWorkspaceManager.get_workspace(workspace_id)
        if ws and ws.get("tables"):
            for t in ws["tables"]:
                fp = t.get("file_path")
                if fp:
                    from pathlib import Path
                    p = Path(fp)
                    if p.exists():
                        return p
    except Exception:
        pass
    try:
        return ParquetStorageManager.get_parquet_path(workspace_id)
    except Exception:
        pass
    return None


def _load_profile(workspace_id: str) -> Optional[Dict[str, Any]]:
    try:
        from app.intelligence.dataset_intelligence_layer import DatasetIntelligenceLayer
        cached = DatasetIntelligenceLayer.get_cached(workspace_id)
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
        logger.debug("[DynamicKPI] Could not load cached profile: %s", e)
    return None


@router.get("/{workspace_id}")
def get_dynamic_kpi_intelligence(workspace_id: str, force_rebuild: bool = Query(False, description="Force rebuild of KPI intelligence")):
    try:
        cached = mongo_dynamic_kpis.find_one({"workspace_id": workspace_id})
        if cached and not force_rebuild:
            cached.pop("_id", None)
            return cached

        path = _get_parquet_path(workspace_id)
        if not path:
            return {
                "workspace_id": workspace_id,
                "status": "NO_DATA",
                "domain": "Generic Business",
                "dataset_type": "Unknown",
                "kpi_cards": {"top": [], "secondary": [], "supporting": []},
                "executive_summary": {},
                "chart_recommendations": [],
                "business_findings": [],
                "dashboard_metadata": {},
                "errors": ["No dataset available for this workspace."],
                "generated_at": "",
            }

        model = build_semantic_model(workspace_id=workspace_id, force_rebuild=False)
        if isinstance(model, dict):
            model = SemanticModel(
                workspace_id=workspace_id,
                domain=model.get("domain", "Generic Business"),
                dataset_type=model.get("dataset_type", "Unknown"),
                is_lookup_only=model.get("is_lookup_only", False),
            )

        profile = _load_profile(workspace_id)
        analytics_result = UniversalAnalyticsEngine.analyze(
            model,
            parquet_path=path,
            workspace_id=workspace_id,
            profile=profile,
        )

        dynamic_result = DynamicKPIEngine.analyze(
            analytics_result=analytics_result,
            semantic_model=model,
            profile=profile,
        )

        result = dynamic_result.to_dict()

        try:
            mongo_dynamic_kpis.update_one(
                {"workspace_id": workspace_id},
                {"$set": result},
                upsert=True,
            )
        except Exception as mongo_exc:
            logger.warning("[MongoDB DynamicKPI] %s", mongo_exc)

        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[DynamicKPI] API failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Dynamic KPI intelligence failed: {str(exc)}")
