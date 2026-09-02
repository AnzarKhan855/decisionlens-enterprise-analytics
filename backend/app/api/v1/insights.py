from pathlib import Path
from typing import Optional
from datetime import UTC, datetime
from fastapi import APIRouter, HTTPException, Query

from app.database.connection import SessionLocal
from app.database.crud import get_latest_dataset
from app.database.storage import ParquetStorageManager
from app.database.mongodb import insights as mongo_insights
from app.ai.universal_copilot_brain import UniversalAIBrain
from app.logging.logger import get_logger

logger = get_logger(__name__)

from fastapi import Depends
from app.core.rbac import get_current_user_from_token

router = APIRouter(
    dependencies=[Depends(get_current_user_from_token)]
)


def _get_parquet_path(db, dataset_id: Optional[str] = None) -> Path:
    path = None
    if dataset_id:
        path = ParquetStorageManager.get_parquet_path(dataset_id)
    else:
        latest = get_latest_dataset(db)
        if not latest:
            raise HTTPException(status_code=404, detail="No dataset uploaded yet.")
        path = Path(latest.file_path)

    if not path or not path.exists():
        raise HTTPException(status_code=404, detail=f"Dataset parquet file not found at {path}")
    return path


@router.get("/insights")
def get_insights(dataset_id: Optional[str] = Query(None, description="Dataset ID")):
    db = SessionLocal()
    try:
        parquet_path = _get_parquet_path(db, dataset_id)
        response = UniversalAIBrain.query(
            question="Generate comprehensive insights and executive summary for this dataset.",
            dataset_id=dataset_id,
        )
        insights = response.get("support", {}).get("analytics", {}).get("critical_findings", [])
        if not insights:
            insights = response.get("evidence", [])

        try:
            mongo_insights.update_one(
                {"dataset_id": dataset_id or "latest"},
                {
                    "$set": {
                        "dataset_id": dataset_id or "latest",
                        "domain": response.get("support", {}).get("domain"),
                        "confidence": response.get("confidence"),
                        "insights": insights,
                        "generated_at": datetime.now(UTC).isoformat(),
                    }
                },
                upsert=True,
            )
        except Exception as mongo_exc:
            logger.warning("[MongoDB Insights] %s", mongo_exc)

        return {
            "dataset_id": dataset_id or "latest",
            "insights": insights,
            "domain": response.get("support", {}).get("domain"),
            "confidence": response.get("confidence"),
        }
    finally:
        db.close()


@router.get("/anomalies")
def get_anomalies(dataset_id: Optional[str] = Query(None, description="Dataset ID")):
    db = SessionLocal()
    try:
        parquet_path = _get_parquet_path(db, dataset_id)
        response = UniversalAIBrain.query(
            question="Detect anomalies and outliers in this dataset.",
            dataset_id=dataset_id,
        )
        analytics = response.get("support", {}).get("analytics", {})
        anomalies = analytics.get("anomalies", [])
        return {
            "dataset_id": dataset_id or "latest",
            "total_anomalies": len(anomalies),
            "anomalies": anomalies
        }
    finally:
        db.close()


@router.get("/drivers")
def get_variance_drivers(dataset_id: Optional[str] = Query(None, description="Dataset ID")):
    db = SessionLocal()
    try:
        parquet_path = _get_parquet_path(db, dataset_id)
        response = UniversalAIBrain.query(
            question="Identify key drivers and root causes for this dataset.",
            dataset_id=dataset_id,
        )
        analytics = response.get("support", {}).get("analytics", {})
        drivers = analytics.get("drivers", [])
        root_causes = analytics.get("root_causes", [])
        return {
            "dataset_id": dataset_id or "latest",
            "drivers": drivers,
            "root_causes": root_causes
        }
    finally:
        db.close()
