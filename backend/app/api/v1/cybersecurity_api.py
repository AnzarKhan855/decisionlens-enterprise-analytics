from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from app.core.rbac import require_role, SUPER_ADMIN, ORGANIZATION_ADMIN
from app.services.cybersecurity_engine import CybersecurityEngine
from app.services.dynamic_dashboard_service import _find_best_parquet
from app.database.connection import SessionLocal
from app.database.storage import ParquetStorageManager

router = APIRouter(
    prefix="/cybersecurity",
    tags=["Cybersecurity Decision Intelligence"],
    dependencies=[Depends(require_role([SUPER_ADMIN, ORGANIZATION_ADMIN]))]
)


@router.get("/dashboard")
def get_cybersecurity_intelligence(dataset_id: Optional[str] = None, workspace_id: Optional[str] = None):
    target = workspace_id or dataset_id
    parquet_path = None
    if target and target != "latest":
        parquet_path = ParquetStorageManager.get_parquet_path_for_workspace(target)
    else:
        from app.services.workspace_service import EnterpriseWorkspaceManager
        active_ws = EnterpriseWorkspaceManager.get_active_workspace_id()
        if active_ws:
            parquet_path = ParquetStorageManager.get_parquet_path_for_workspace(active_ws)

    if not parquet_path or not parquet_path.exists():
        db = SessionLocal()
        try:
            parquet_path = _find_best_parquet(db)
        finally:
            db.close()

    if not parquet_path or not parquet_path.exists():
        raise HTTPException(status_code=404, detail="No active business workspace found.")

    analytics = CybersecurityEngine.analyze_security_logs(parquet_path)
    analytics["dataset_id"] = target or "latest"
    return analytics
