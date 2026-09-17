import hashlib
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse

from app.core.rbac import get_current_user_from_token
from app.database.storage import ParquetStorageManager
from app.logging.logger import get_logger
from app.security.file_validator import sanitize_filename
from app.services.ingestion_job_service import IngestionJobService, JobState
from app.services.workspace_service import EnterpriseWorkspaceManager

logger = get_logger(__name__)

router = APIRouter(
    prefix="/upload",
    tags=["Upload"]
)

CHUNK_SIZE = 1024 * 1024  # 1MB chunk size for memory-safe streaming
MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024  # 500MB maximum upload limit


def process_single_file(
    file: UploadFile,
    workspace_id: Optional[str] = None,
    background_tasks: Optional[BackgroundTasks] = None,
    user: Optional[dict] = None,
    sync: bool = False,
) -> Dict[str, Any]:
    """
    Streams the uploaded file to disk, creates a durable Ingestion Job,
    and dispatches background analytical processing (or executes synchronously if sync=True).
    """
    current_stage = "File Extension Validation"
    allowed_extensions = [".csv", ".xlsx", ".xls", ".parquet"]
    filename = sanitize_filename(file.filename or "uploaded_file")
    extension = Path(filename).suffix.lower()

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension '{extension}'. Allowed: {allowed_extensions}"
        )

    # 1. Determine or generate workspace ID early
    ws_id = workspace_id.strip() if workspace_id and workspace_id.strip() else f"ws-{uuid.uuid4().hex[:8]}"
    orig_stem = Path(filename).stem.lower().replace("-", "_").replace(" ", "_")
    ws_title = orig_stem.replace("_", " ").title()

    # 2. Stream file directly to durable raw storage with SHA256 calculation
    current_stage = "File Streaming & Deduplication"
    raw_path = ParquetStorageManager.get_raw_path(ws_id, filename)
    ParquetStorageManager.ensure_directories()

    hasher = hashlib.sha256()
    file_size_bytes = 0

    try:
        with open(raw_path, "wb") as buffer:
            while True:
                chunk = file.file.read(CHUNK_SIZE)
                if not chunk:
                    break
                file_size_bytes += len(chunk)
                if file_size_bytes > MAX_FILE_SIZE_BYTES:
                    buffer.close()
                    raw_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Maximum size is {MAX_FILE_SIZE_BYTES // (1024*1024)} MB."
                    )
                buffer.write(chunk)
                hasher.update(chunk)
    except HTTPException:
        raise
    except Exception as read_err:
        if raw_path.exists():
            raw_path.unlink(missing_ok=True)
        logger.error("[Upload Stream Error] Failed to stream file %s: %s", filename, read_err)
        raise HTTPException(status_code=500, detail="Failed to write uploaded file to storage.")

    if file_size_bytes == 0:
        if raw_path.exists():
            raw_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=422,
            detail={
                "status": "error",
                "stage": "preflight_empty",
                "message": f"Uploaded file '{filename}' is empty (0 bytes).",
                "recovery_suggestion": "Please ensure the file contains valid business data and retry.",
            }
        )

    file_sha256 = hasher.hexdigest()

    # 3. Check for existing identical workspace by hash to deduplicate
    for w in EnterpriseWorkspaceManager.get_all_workspaces():
        hashes = w.get("sha256_hashes", [])
        if file_sha256 in hashes or w.get("sha256_hash") == file_sha256:
            if not workspace_id:
                ws_id = w["workspace_id"]
                ws_title = w.get("name", ws_title)
            break

    # 4. Create durable Ingestion Job in MongoDB & memory
    job = IngestionJobService.create_job(
        workspace_id=ws_id,
        dataset_id=ws_id,
        filename=filename,
        file_size_bytes=file_size_bytes,
        user_email=user.get("email", "") if user else "",
        initial_status=JobState.UPLOADED,
    )

    # 5. Execute pipeline either synchronously or asynchronously
    if sync:
        logger.info("[Upload] Executing synchronous ingestion for job %s", job["job_id"])
        final_job = IngestionJobService.run_pipeline(
            job_id=job["job_id"],
            raw_file_path=raw_path,
            workspace_id=ws_id,
            filename=filename,
            user=user,
            extension=extension,
        )

        if final_job.get("status") == JobState.FAILED.value:
            err = final_job.get("error") or {}
            raise HTTPException(
                status_code=422,
                detail={
                    "status": "error",
                    "stage": err.get("failed_stage", "PROCESSING"),
                    "message": err.get("message", "Processing failed"),
                    "suggested_fix": err.get("suggested_fix", "Check file format and data structure"),
                }
            )

        metrics = final_job.get("metrics", {})
        return {
            "status": "success",
            "upload_status": "COMPLETED",
            "job_id": job["job_id"],
            "dataset_id": ws_id,
            "workspace_id": ws_id,
            "workspace_name": ws_title,
            "active_workspace": ws_id,
            "filename": filename,
            "rows": metrics.get("rows", 0),
            "columns": metrics.get("columns", 0),
            "health_score": metrics.get("health_score", 100),
            "dataset_type": metrics.get("domain", "Generic"),
            "intelligence": {
                "domain": metrics.get("domain", "Generic"),
                "status": "READY",
            }
        }

    # Asynchronous background execution (default for large files & responsive UI)
    if background_tasks is not None:
        background_tasks.add_task(
            IngestionJobService.run_pipeline,
            job["job_id"],
            raw_path,
            ws_id,
            filename,
            user,
            extension,
        )
    else:
        # Fallback thread runner if background_tasks was not passed
        threading.Thread(
            target=IngestionJobService.run_pipeline,
            args=(job["job_id"], raw_path, ws_id, filename, user, extension),
            daemon=True
        ).start()

    logger.info("[Upload] Dispatched async ingestion pipeline for job %s (ws: %s)", job["job_id"], ws_id)

    return {
        "status": "processing",
        "upload_status": "PROCESSING",
        "job_id": job["job_id"],
        "dataset_id": ws_id,
        "workspace_id": ws_id,
        "workspace_name": ws_title,
        "active_workspace": ws_id,
        "filename": filename,
        "stage": "UPLOADED",
        "progress_pct": 20,
        "message": "Dataset uploaded successfully. Analytical ingestion running in background.",
        "status_url": f"/api/v1/upload/status/{job['job_id']}",
    }


@router.post("/")
@router.post("/file")
def upload_dataset(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    workspace_id: Optional[str] = Form(None),
    sync: bool = Query(False, description="Run synchronously if True (default False for large datasets)"),
    user: dict = Depends(get_current_user_from_token)
):
    """
    Primary dataset upload endpoint.
    Accepts CSV, Excel, or Parquet datasets, streams them memory-safely to storage,
    and returns an Ingestion Job ID for background processing.
    """
    try:
        res = process_single_file(
            file=file,
            workspace_id=workspace_id,
            background_tasks=background_tasks,
            user=user,
            sync=sync,
        )
        return {
            "message": "Dataset upload accepted. Ingestion in progress.",
            **res
        }
    except HTTPException as http_err:
        raise http_err
    except Exception as exc:
        logger.exception("[Upload Unexpected Error] %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "An unexpected error occurred while processing the uploaded file.",
                "exception": exc.__class__.__name__,
                "detail": str(exc),
                "suggested_fix": "Please verify file format and dataset structure.",
            }
        )


@router.post("/batch")
def upload_multiple_datasets(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    workspace_id: Optional[str] = Form(None),
    sync: bool = Query(False),
    user: dict = Depends(get_current_user_from_token)
):
    """Batch dataset upload endpoint."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided for upload.")

    results = []
    errors = []

    for f in files:
        try:
            res = process_single_file(
                file=f,
                workspace_id=workspace_id,
                background_tasks=background_tasks,
                user=user,
                sync=sync,
            )
            results.append(res)
        except Exception as e:
            logger.warning("[Batch Upload] Failed to process %s: %s", f.filename, e)
            errors.append({
                "filename": f.filename,
                "error": str(e) if isinstance(e, HTTPException) else "Failed to process file.",
            })

    return {
        "message": f"Successfully initiated processing for {len(results)} of {len(files)} uploaded dataset(s).",
        "processed_datasets": results,
        "errors": errors,
    }


@router.get("/status/{job_id}")
@router.get("/job/{job_id}")
def get_job_status(job_id: str):
    """
    Queries real-time job status, progress percentage, current stage, and metrics.
    """
    job = IngestionJobService.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return job


@router.post("/cancel/{job_id}")
def cancel_job(job_id: str, user: dict = Depends(get_current_user_from_token)):
    """
    Cancels an active dataset ingestion job.
    """
    success = IngestionJobService.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=400, detail=f"Cannot cancel job '{job_id}'. It may already be completed or not found.")
    cancelled_job = IngestionJobService.get_job(job_id)
    return {"status": "success", "message": f"Job '{job_id}' has been cancelled.", "job": cancelled_job}


@router.get("/workspace/{workspace_id}/status")
def get_workspace_job_status(workspace_id: str):
    """
    Retrieves the most recent ingestion job status for a workspace.
    """
    job = IngestionJobService.get_active_job_for_workspace(workspace_id)
    if job:
        return job
    return EnterpriseWorkspaceManager.get_processing_status(workspace_id)
