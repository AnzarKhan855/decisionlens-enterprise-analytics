from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from app.services.cybersecurity_engine import CybersecurityEngine
from app.services.dynamic_dashboard_service import _find_best_parquet
from app.database.connection import SessionLocal
from app.database.storage import ParquetStorageManager

router = APIRouter(
    prefix="/cybersecurity",
    tags=["Cybersecurity Decision Intelligence"]
)


@router.get("/dashboard")
def get_cybersecurity_intelligence(dataset_id: Optional[str] = None):
    db = SessionLocal()
    try:
        parquet_path = None
        if dataset_id and dataset_id != "latest":
            parquet_path = ParquetStorageManager.get_parquet_path(dataset_id)
        else:
            parquet_path = _find_best_parquet(db)

        if not parquet_path or not parquet_path.exists():
            raise HTTPException(status_code=404, detail="No active business workspace found.")

        analytics = CybersecurityEngine.analyze_security_logs(parquet_path)
        analytics["dataset_id"] = dataset_id or "latest"
        return analytics
    finally:
        db.close()
