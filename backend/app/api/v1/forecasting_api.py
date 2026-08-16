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


def _get_workspace_id(db, dataset_id: Optional[str] = None) -> str:
    if dataset_id and dataset_id != "latest":
        return dataset_id
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


@router.get("/forecast")
def get_time_series_forecast(
    dataset_id: Optional[str] = Query(None, description="Dataset ID"),
    horizon: int = Query(14, ge=1, le=90, description="Forecast horizon period count")
):
    db = SessionLocal()
    try:
        parquet_path = _get_parquet_path(db, dataset_id)
        ws_id = _get_workspace_id(db, dataset_id)
        profile = SemanticDataProfiler.profile(parquet_path)

        from app.services.analytics_cache_service import AnalyticsCacheService
        from app.schemas.analytics import AnalyticsResult, Prediction

        analytics = None
        c_dict = AnalyticsCacheService.get_cached(ws_id, parquet_path)
        if c_dict:
            try:
                analytics = AnalyticsResult.from_dict(c_dict)
            except Exception:
                pass

        if analytics is None:
            from app.analytics.universal_engine import UniversalAnalyticsEngine
            from app.semantic_model import build_semantic_model
            from app.semantic_model.core import SemanticModel

            try:
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
                sm = SemanticModel(workspace_id=ws_id, domain="Generic Business", dataset_type="Unknown")

            analytics = UniversalAnalyticsEngine.analyze(sm, parquet_path=parquet_path, workspace_id=ws_id)

        predictions = getattr(analytics, "predictions", []) or []
        if not predictions:
            from app.semantic_model.core import SemanticModel
            sm = getattr(analytics, "semantic_model", None) or SemanticModel(workspace_id=ws_id)
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
                "model_type": p.model_type if hasattr(p, "model_type") else p.get("model_type"),
                "model_used": p.model_used if hasattr(p, "model_used") else p.get("model_used"),
                "prediction": p.prediction if hasattr(p, "prediction") else p.get("prediction"),
                "confidence": p.confidence if hasattr(p, "confidence") else p.get("confidence"),
                "evidence": p.evidence if hasattr(p, "evidence") else p.get("evidence"),
                "business_impact": p.business_impact if hasattr(p, "business_impact") else p.get("business_impact"),
                "time_horizon": p.time_horizon if hasattr(p, "time_horizon") else p.get("time_horizon"),
                "risk_level": p.risk_level if hasattr(p, "risk_level") else p.get("risk_level"),
                "recommended_action": p.recommended_action if hasattr(p, "recommended_action") else p.get("recommended_action"),
                "feasible": p.feasible if hasattr(p, "feasible") else p.get("feasible"),
                "limitation": p.limitation if hasattr(p, "limitation") else p.get("limitation"),
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
        ws_id = _get_workspace_id(db, dataset_id)

        from app.services.analytics_cache_service import AnalyticsCacheService
        from app.schemas.analytics import AnalyticsResult

        analytics = None
        c_dict = AnalyticsCacheService.get_cached(ws_id, parquet_path)
        if c_dict:
            try:
                analytics = AnalyticsResult.from_dict(c_dict)
            except Exception:
                pass

        if analytics is None:
            from app.analytics.universal_engine import UniversalAnalyticsEngine
            from app.semantic_model import build_semantic_model
            from app.semantic_model.core import SemanticModel

            try:
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
                sm = SemanticModel(workspace_id=ws_id, domain="Generic Business", dataset_type="Unknown")

            analytics = UniversalAnalyticsEngine.analyze(sm, parquet_path=parquet_path, workspace_id=ws_id)

        predictions = getattr(analytics, "predictions", []) or []
        if not predictions:
            from app.semantic_model.core import SemanticModel
            sm = getattr(analytics, "semantic_model", None) or SemanticModel(workspace_id=ws_id)
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
                "model_type": p.model_type if hasattr(p, "model_type") else p.get("model_type"),
                "model_used": p.model_used if hasattr(p, "model_used") else p.get("model_used"),
                "prediction": p.prediction if hasattr(p, "prediction") else p.get("prediction"),
                "confidence": p.confidence if hasattr(p, "confidence") else p.get("confidence"),
                "evidence": p.evidence if hasattr(p, "evidence") else p.get("evidence"),
                "business_impact": p.business_impact if hasattr(p, "business_impact") else p.get("business_impact"),
                "time_horizon": p.time_horizon if hasattr(p, "time_horizon") else p.get("time_horizon"),
                "risk_level": p.risk_level if hasattr(p, "risk_level") else p.get("risk_level"),
                "recommended_action": p.recommended_action if hasattr(p, "recommended_action") else p.get("recommended_action"),
                "feasible": p.feasible if hasattr(p, "feasible") else p.get("feasible"),
                "limitation": p.limitation if hasattr(p, "limitation") else p.get("limitation"),
            }
            for p in predictions
            if ("Cohort" in (p.model_type if hasattr(p, "model_type") else p.get("model_type", "")) or
                "Segment" in (p.model_type if hasattr(p, "model_type") else p.get("model_type", "")))
        ]

        return {
            "dataset_id": dataset_id or "latest",
            "segmentation_available": bool(segment_predictions),
            "segments": segment_predictions,
        }
    finally:
        db.close()
