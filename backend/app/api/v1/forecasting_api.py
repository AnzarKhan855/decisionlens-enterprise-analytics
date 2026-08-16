from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from app.database.connection import SessionLocal
from app.database.crud import get_latest_dataset
from app.database.storage import ParquetStorageManager
from app.ingestion.semantic_profiler import SemanticDataProfiler
from app.ml.prediction_engine import UniversalPredictionEngine
from app.semantic_model.core import SemanticModel
from app.logging.logger import get_logger
from app.resilience.retry import with_retry

logger = get_logger(__name__)

router = APIRouter(
    prefix="/ml",
    tags=["Machine Learning"]
)


def _get_parquet_path(db, dataset_id: Optional[str] = None) -> Path:
    if dataset_id and dataset_id != "latest":
        direct = ParquetStorageManager.get_parquet_path(dataset_id)
        if direct and direct.exists():
            return direct
        workspace_path = ParquetStorageManager.get_parquet_path_for_workspace(dataset_id)
        if workspace_path and workspace_path.exists():
            return workspace_path

    latest = get_latest_dataset(db)
    if latest:
        file_path = Path(latest.file_path)
        if file_path.exists():
            return file_path
        parquet_path = ParquetStorageManager.get_parquet_path(str(latest.id))
        if parquet_path and parquet_path.exists():
            return parquet_path

    raise HTTPException(status_code=404, detail="No active business workspace found.")


@router.get("/forecast")
def get_time_series_forecast(
    dataset_id: Optional[str] = Query(None, description="Dataset ID"),
    horizon: int = Query(14, ge=1, le=90, description="Forecast horizon period count")
):
    db = SessionLocal()
    try:
        parquet_path = _get_parquet_path(db, dataset_id)
        profile = SemanticDataProfiler.profile(parquet_path)

        temporal = profile["column_categories"].get("temporal", [])
        measures = profile["column_categories"].get("measures", [])

        if not temporal or not measures:
            return {
                "dataset_id": dataset_id or "latest",
                "forecast_available": False,
                "reason": "Dataset lacks temporal and numeric columns required for ML forecasting.",
                "forecast": []
            }

        # Build a minimal AnalyticsResult for the canonical engine
        from app.analytics.universal_engine import UniversalAnalyticsEngine
        from app.semantic_model import build_semantic_model

        try:
            ws_id = dataset_id or "default"
            sm_dict = build_semantic_model(workspace_id=ws_id, force_rebuild=False)
            if isinstance(sm_dict, dict):
                sm = SemanticModel(
                    workspace_id=ws_id,
                    domain=sm_dict.get("domain", "Generic Business"),
                    dataset_type=sm_dict.get("dataset_type", "Unknown"),
                )
            else:
                sm = sm_dict
        except Exception as exc:
            logger.warning("[Forecasting] Semantic model build fallback: %s", exc)
            sm = SemanticModel(workspace_id="default", domain="Generic Business", dataset_type="Unknown")

        analytics = UniversalAnalyticsEngine.analyze(sm, parquet_path=parquet_path)
        predictions = with_retry(
            max_attempts=2,
            backoff_factor=0.5,
            exceptions=(Exception,),
            circuit_breaker_name="forecast",
            fallback=lambda: [],
        )(lambda: UniversalPredictionEngine.generate(
            analytics_result=analytics,
            semantic_model=sm,
        ))()

        forecast_predictions = [
            {
                "model_type": p.model_type,
                "model_used": p.model_used,
                "prediction": p.prediction,
                "confidence": p.confidence,
                "evidence": p.evidence,
                "business_impact": p.business_impact,
                "time_horizon": p.time_horizon,
                "risk_level": p.risk_level,
                "recommended_action": p.recommended_action,
                "feasible": p.feasible,
                "limitation": p.limitation,
            }
            for p in predictions
        ]

        return {
            "dataset_id": dataset_id or "latest",
            "forecast_available": bool(forecast_predictions),
            "forecast": forecast_predictions,
        }
    finally:
        db.close()


@router.get("/segmentation")
def get_customer_segmentation(
    dataset_id: Optional[str] = Query(None, description="Dataset ID"),
    k_clusters: int = Query(3, ge=2, le=10, description="Cluster count")
):
    db = SessionLocal()
    try:
        parquet_path = _get_parquet_path(db, dataset_id)
        profile = SemanticDataProfiler.profile(parquet_path)

        temporal = profile["column_categories"].get("temporal", [])
        measures = profile["column_categories"].get("measures", [])

        if not temporal or not measures:
            return {
                "dataset_id": dataset_id or "latest",
                "segmentation_available": False,
                "reason": "Dataset lacks temporal and numeric columns required for segmentation.",
                "segments": []
            }

        # Build a minimal AnalyticsResult for the canonical engine
        from app.analytics.universal_engine import UniversalAnalyticsEngine
        from app.semantic_model import build_semantic_model

        try:
            ws_id = dataset_id or "default"
            sm_dict = build_semantic_model(workspace_id=ws_id, force_rebuild=False)
            if isinstance(sm_dict, dict):
                sm = SemanticModel(
                    workspace_id=ws_id,
                    domain=sm_dict.get("domain", "Generic Business"),
                    dataset_type=sm_dict.get("dataset_type", "Unknown"),
                )
            else:
                sm = sm_dict
        except Exception as exc:
            logger.warning("[Forecasting] Semantic model build fallback: %s", exc)
            sm = SemanticModel(workspace_id="default", domain="Generic Business", dataset_type="Unknown")

        analytics = UniversalAnalyticsEngine.analyze(sm, parquet_path=parquet_path)
        predictions = with_retry(
            max_attempts=2,
            backoff_factor=0.5,
            exceptions=(Exception,),
            circuit_breaker_name="forecast",
            fallback=lambda: [],
        )(lambda: UniversalPredictionEngine.generate(
            analytics_result=analytics,
            semantic_model=sm,
        ))()

        segment_predictions = [
            {
                "model_type": p.model_type,
                "model_used": p.model_used,
                "prediction": p.prediction,
                "confidence": p.confidence,
                "evidence": p.evidence,
                "business_impact": p.business_impact,
                "time_horizon": p.time_horizon,
                "risk_level": p.risk_level,
                "recommended_action": p.recommended_action,
                "feasible": p.feasible,
                "limitation": p.limitation,
            }
            for p in predictions if "Cohort" in p.model_type or "Segment" in p.model_type
        ]

        return {
            "dataset_id": dataset_id or "latest",
            "segmentation_available": bool(segment_predictions),
            "segments": segment_predictions,
        }
    finally:
        db.close()
