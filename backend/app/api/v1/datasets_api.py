from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends

from app.database.connection import SessionLocal
from app.database.crud import get_all_datasets, get_dataset_by_id, delete_dataset_permanently
from app.database.storage import ParquetStorageManager
from app.database.duckdb_engine import DuckDBEngine
from app.services.workspace_service import EnterpriseWorkspaceManager
from app.core.rbac import get_current_user_from_token, require_permission
from app.logging.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/datasets",
    tags=["Dataset Library"],
    dependencies=[Depends(require_permission("view_allowed_datasets"))]
)


@router.get("")
def list_workspace_datasets(
    search: Optional[str] = Query(None, description="Search dataset name"),
    tag: Optional[str] = Query(None, description="Filter by tag")
):
    db = SessionLocal()
    try:
        datasets = get_all_datasets(db)
        results = []

        for d in datasets:
            if search and search.lower() not in d.filename.lower():
                continue
            results.append({
                "id": str(d.id),
                "name": d.filename,
                "description": f"Uploaded enterprise dataset containing {d.rows:,} rows",
                "dataset_type": d.dataset_type,
                "file_type": d.file_type,
                "rows": d.rows,
                "columns": d.columns,
            "status": "Analyzed",
            "tags": ["Custom", d.file_type.upper()],
                "uploaded_at": d.uploaded_at.strftime("%Y-%m-%d %H:%M:%S") if d.uploaded_at else "2026-07-23"
            })

        return {
            "total_datasets": len(results),
            "datasets": results
        }
    finally:
        db.close()


@router.get("/{dataset_id}/preview")
def preview_dataset(dataset_id: str, limit: int = Query(10, ge=1, le=100)):
    db = SessionLocal()
    try:
        parquet_path = None

        parquet_path = ParquetStorageManager.get_parquet_path(dataset_id)

        if not parquet_path or not parquet_path.exists():
            raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found.")

        schema = DuckDBEngine.get_schema(parquet_path)
        preview = DuckDBEngine.preview(parquet_path, limit=limit)
        row_count = DuckDBEngine.get_row_count(parquet_path)

        return {
            "dataset_id": dataset_id,
            "row_count": row_count,
            "column_count": len(schema),
            "schema": schema,
            "preview_data": preview
        }
    finally:
        db.close()


@router.delete("/{dataset_id}")
def delete_dataset(dataset_id: str, user: dict = Depends(require_permission("manage_org_datasets"))):
    logger.info("[PERMANENT DELETION] Delete request received for Dataset ID: '%s'", dataset_id)

    db = SessionLocal()
    try:
        # 1. Database deletion status
        db_deleted = int(delete_dataset_permanently(db, dataset_id) or 0)
        logger.info("[PERMANENT DELETION] 1. Database Deletion Status: SUCCESS (%d records purged from SQLite)", db_deleted)

        # 2. File deletion status (Parquet, CSV, ZIP, Upload folders)
        files_deleted = int(ParquetStorageManager.delete_dataset_files(dataset_id) or 0)
        logger.info("[PERMANENT DELETION] 2. File Deletion Status: SUCCESS (%d storage files/folders unlinked)", files_deleted)

        # 3. DuckDB & Workspace cleanup status
        ws_deleted = EnterpriseWorkspaceManager.delete_workspace(dataset_id)
        logger.info("[PERMANENT DELETION] 3. DuckDB & Workspace Registry Status: SUCCESS (%s)", ws_deleted)

        # 4. Cache cleanup status
        from app.semantic_model.engine import invalidate_semantic_model_cache
        invalidate_semantic_model_cache()
        logger.info("[PERMANENT DELETION] 4. Cache Cleanup Status: SUCCESS (In-Memory Workspace & Dynamic Caches Evicted)")

        logger.info("[PERMANENT DELETION] FINAL RESULT: Permanent Deletion Completed Successfully for '%s'", dataset_id)

        return {
            "status": "success",
            "message": f"Dataset '{dataset_id}' permanently removed from system.",
            "dataset_id": dataset_id,
            "database_status": "purged",
            "file_status": "unlinked",
            "duckdb_status": "cleaned",
            "cache_status": "evicted"
        }
    except Exception as e:
        logger.error("[PERMANENT DELETION] ERROR: Deletion failed for '%s': %s", dataset_id, e)
        raise HTTPException(status_code=500, detail=f"Permanent deletion failed: {str(e)}")
    finally:
        db.close()
