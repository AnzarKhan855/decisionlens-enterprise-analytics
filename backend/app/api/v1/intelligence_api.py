from fastapi import APIRouter, Query, HTTPException
from typing import Optional, Dict, Any
from pathlib import Path

from app.intelligence.dataset_intelligence_layer import DatasetIntelligenceLayer
from app.logging.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/intelligence", tags=["Dataset Intelligence Layer"])


@router.get("/workspace/{workspace_id}")
def get_dataset_intelligence(workspace_id: str, force_rebuild: bool = Query(False, description="Force rebuild of intelligence model")):
    try:
        from app.database.storage import STORAGE_DIR
        from app.semantic_model.engine import _workspace_prefix_for

        clean_target = _workspace_prefix_for(workspace_id)
        parquet_dir = STORAGE_DIR
        parquet_files = []
        if parquet_dir.exists():
            for p in parquet_dir.glob("*.parquet"):
                if p.name.startswith("unified_") or p.name.startswith("tmp_"):
                    continue
                clean_pname = p.stem.lower().replace("-", "_")
                if clean_target in clean_pname or clean_pname.startswith(clean_target):
                    parquet_files.append(p)

        if not parquet_files:
            try:
                from app.services.workspace_service import EnterpriseWorkspaceManager
                ws = EnterpriseWorkspaceManager.get_workspace(workspace_id)
                if ws and isinstance(ws, dict):
                    tables = ws.get("tables", [])
                    for t in tables:
                        fp = t.get("file_path")
                        if fp:
                            p = Path(fp)
                            if p.exists() and p.is_file():
                                parquet_files.append(p)
            except Exception:
                pass

        if not parquet_files:
            return {
                "workspace_id": workspace_id,
                "status": "NO_DATA",
                "domain": "Generic Business",
                "domain_confidence": 0.0,
                "dataset_type": "Unknown",
                "error": "No dataset files found for this workspace.",
            }

        primary_parquet = sorted(parquet_files, key=lambda x: x.stat().st_mtime, reverse=True)[0]
        result = DatasetIntelligenceLayer.analyze(
            workspace_id=workspace_id,
            parquet_path=primary_parquet,
            force_rebuild=force_rebuild,
        )
        return result.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[DatasetIntelligence] API failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Dataset intelligence failed: {str(e)}")


@router.get("/workspace/{workspace_id}/summary")
def get_intelligence_summary(workspace_id: str):
    cached = DatasetIntelligenceLayer.get_cached(workspace_id)
    if cached is None:
        raise HTTPException(status_code=404, detail="No intelligence data found. Upload a dataset first.")
    return {
        "workspace_id": cached.workspace_id,
        "status": cached.status,
        "domain": cached.domain,
        "domain_confidence": cached.domain_confidence,
        "domain_reason": cached.domain_reason,
        "dataset_type": cached.dataset_type,
        "generated_at": cached.generated_at,
        "columns_count": len(cached.columns),
        "measures_count": sum(1 for c in cached.columns if c.is_measure),
        "dimensions_count": sum(1 for c in cached.columns if c.is_dimension),
        "temporal_count": sum(1 for c in cached.columns if c.is_temporal),
        "identifier_count": sum(1 for c in cached.columns if c.is_identifier),
        "entities": cached.profile.detected_entities,
        "data_quality_score": cached.data_quality.overall_score,
        "capabilities": [
            {"capability": c.capability, "available": c.available}
            for c in cached.profile.capability_matrix
        ],
    }


@router.get("/workspace/{workspace_id}/columns")
def get_intelligence_columns(workspace_id: str):
    cached = DatasetIntelligenceLayer.get_cached(workspace_id)
    if cached is None:
        raise HTTPException(status_code=404, detail="No intelligence data found.")
    return {
        "workspace_id": workspace_id,
        "columns": [c.__dict__ for c in cached.columns],
    }


@router.get("/workspace/{workspace_id}/profile")
def get_intelligence_profile(workspace_id: str):
    cached = DatasetIntelligenceLayer.get_cached(workspace_id)
    if cached is None:
        raise HTTPException(status_code=404, detail="No intelligence data found.")
    return {
        "workspace_id": workspace_id,
        "profile": cached.profile.to_dict(),
    }


@router.post("/workspace/{workspace_id}/invalidate-cache")
def invalidate_intelligence_cache(workspace_id: str):
    DatasetIntelligenceLayer.invalidate_cache(workspace_id)
    return {"status": "success", "message": f"Intelligence cache invalidated for workspace '{workspace_id}'"}
