import uuid
import os
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, File, HTTPException, UploadFile, Query, Form, Body, BackgroundTasks, Depends
from fastapi.responses import JSONResponse

from app.core.rbac import get_current_user_from_token
from app.database.storage import ParquetStorageManager
from app.database.duckdb_engine import DuckDBEngine
from app.ingestion.generic_loader import GenericDataLoader, CsvImportError
from app.ingestion.dataset_detector import DatasetDetector
from app.ingestion.validator import DataValidator
from app.database.connection import SessionLocal
from app.database.crud import save_dataset
from app.database.mongodb import datasets as mongo_datasets, workspaces as mongo_workspaces
from app.logging.logger import get_logger
from app.security.file_validator import validate_upload, sanitize_filename
from app.security.input_sanitizer import InputSanitizer

logger = get_logger(__name__)

router = APIRouter(
    prefix="/upload",
    tags=["Upload"]
)


def process_single_file(file: UploadFile, workspace_id: Optional[str] = None, background_tasks: Optional[BackgroundTasks] = None, user: Optional[dict] = None):
    current_stage = "File Extension Validation"
    allowed_extensions = [".csv", ".xlsx", ".xls", ".parquet"]
    filename = sanitize_filename(file.filename or "uploaded_file")
    extension = Path(filename).suffix.lower()

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension '{extension}'. Allowed: {allowed_extensions}"
        )

    MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024
    file_bytes = file.file.read(MAX_FILE_SIZE_BYTES + 1)
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE_BYTES // (1024*1024)} MB."
        )

    validation = validate_upload(file_bytes, filename)
    if not validation["valid"]:
        raise HTTPException(
            status_code=422,
            detail={
                "status": "error",
                "stage": current_stage,
                "errors": validation["errors"],
                "recovery_suggestion": "Fix the file issues and retry upload.",
            }
        )
    for warning in validation.get("warnings", []):
        logger.warning("[Upload Validation Warning] %s", warning)

    import hashlib
    file_sha256 = hashlib.sha256(file_bytes).hexdigest()
    orig_stem = Path(filename).stem.lower().replace("-", "_").replace(" ", "_")
    from app.services.workspace_service import EnterpriseWorkspaceManager
    active_ws_id = EnterpriseWorkspaceManager.get_active_workspace_id()

    existing_ws = None
    for w in EnterpriseWorkspaceManager.get_all_workspaces():
        hashes = w.get("sha256_hashes", [])
        if file_sha256 in hashes or w.get("sha256_hash") == file_sha256:
            existing_ws = w
            break

    if workspace_id and workspace_id.strip():
        ws_id = workspace_id.strip()
    elif existing_ws:
        ws_id = existing_ws["workspace_id"]
    elif active_ws_id:
        ws_id = active_ws_id
    else:
        ws_id = f"ws-{uuid.uuid4().hex[:8]}"

    db = None
    try:
        current_stage = "Parquet Storage Conversion"
        raw_path = ParquetStorageManager.save_raw_file(file_bytes, ws_id, filename)
        orig_stem = Path(filename).stem.lower().replace("-", "_").replace(" ", "_")
        clean_name = f"{ws_id}_{orig_stem}"
        parquet_path = GenericDataLoader.convert_to_parquet(raw_path, clean_name)

        current_stage = "Domain Intelligence Classification"
        detection = DatasetDetector.detect_from_parquet(parquet_path)
        dataset_type = detection["dataset_type"]

        current_stage = "Data Quality Validation & Profiling"
        validation_report = DataValidator.validate(parquet_path)
        health_score = validation_report["health_score"]
        semantic_profile = validation_report["semantic_profile"]

        current_stage = "Dataset Intelligence Layer"
        from app.intelligence.dataset_intelligence_layer import DatasetIntelligenceLayer
        intelligence_result = DatasetIntelligenceLayer.analyze(workspace_id=ws_id, parquet_path=parquet_path, force_rebuild=True)

        current_stage = "Metadata Registration"
        db = SessionLocal()
        db_dataset = save_dataset(
            db=db,
            filename=filename,
            file_path=str(parquet_path),
            dataset_type=dataset_type,
            rows=semantic_profile["total_rows"],
            columns=semantic_profile["total_columns"],
            file_type=extension.replace(".", "")
        )

        ws_title = orig_stem.replace("_", " ").title()
        current_stage = "Workspace Registration & Active Activation"
        from app.semantic_model.engine import invalidate_semantic_model_cache

        cols_summary = [{"name": c, "type": semantic_profile["columns"][c].get("inferred_type", "VARCHAR")} for c in semantic_profile["columns"]]
        ws = EnterpriseWorkspaceManager.create_or_get_workspace(ws_id, ws_title, industry=dataset_type, created_by=user.get("email", "") if user else "")
        EnterpriseWorkspaceManager.add_sha256_hash(ws_id, file_sha256)
        EnterpriseWorkspaceManager.register_table(ws_id, orig_stem, cols_summary, semantic_profile["total_rows"], str(parquet_path))
        EnterpriseWorkspaceManager.set_active_workspace(ws_id)

        invalidate_semantic_model_cache()

        return {
            "status": "success",
            "upload_status": "COMPLETED",
            "dataset_id": ws_id,
            "workspace_id": ws_id,
            "workspace_name": ws_title,
            "active_workspace": ws_id,
            "filename": filename,
            "dataset_type": dataset_type,
            "health_score": health_score,
            "rows": semantic_profile["total_rows"],
            "columns": semantic_profile["total_columns"],
            "intelligence": {
                "domain": intelligence_result.domain,
                "domain_confidence": intelligence_result.domain_confidence,
                "dataset_type": intelligence_result.dataset_type,
                "status": intelligence_result.status,
                "generated_at": intelligence_result.generated_at,
            }
        }
    except HTTPException:
        raise
    except CsvImportError as csv_err:
        logger.error("[Upload CSV Import Failure] filename=%s | stage=%s | path=%s | error=%s", csv_err.filename, csv_err.stage, csv_err.absolute_path, str(csv_err))
        raise HTTPException(
            status_code=422,
            detail={
                "status": "error",
                "stage": current_stage,
                "exception": csv_err.original_exception.__class__.__name__ if csv_err.original_exception else csv_err.stage,
                "message": str(csv_err),
                "filename": csv_err.filename,
                "absolute_path": csv_err.absolute_path,
                "sql_query": "Check file format and data structure",
                "suggested_fix": "Check CSV encoding, delimiter, headers, quoting, and malformed rows.",
            }
        )
    except Exception as exc:
        logger.exception("[Upload Unexpected Error] stage=%s | ws_id=%s | exc=%s", current_stage, ws_id, exc)
        raise HTTPException(status_code=500, detail="An error occurred while processing the uploaded file.")
    finally:
        if db is not None:
            db.close()


@router.post("/")
@router.post("/file")
def upload_dataset(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    workspace_id: Optional[str] = Form(None),
    user: dict = Depends(get_current_user_from_token)
):
    try:
        res = process_single_file(file, workspace_id=workspace_id, background_tasks=background_tasks, user=user)
        return {
            "message": "Dataset uploaded and processed successfully.",
            **res
        }
    except HTTPException as http_err:
        raise http_err
    except Exception as exc:
        logger.exception("[Upload Unexpected Top-Level Error] %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "An error occurred while processing the uploaded file.",
                "exception": exc.__class__.__name__,
                "detail": str(exc),
                "suggested_fix": "Please verify file format and dataset structure.",
            }
        )


@router.post("/batch")
def upload_multiple_datasets(
    files: List[UploadFile] = File(...),
    workspace_id: Optional[str] = Form(None),
    user: dict = Depends(get_current_user_from_token)
):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided for upload.")

    results = []
    errors = []

    for f in files:
        try:
            res = process_single_file(f, workspace_id=workspace_id, user=user)
            results.append(res)
        except Exception as e:
            logger.warning("[Batch Upload] Failed to process %s: %s", f.filename, e)
            errors.append({"filename": f.filename, "error": "Failed to process file. Please check the format and try again."})

    return {
        "message": f"Successfully processed {len(results)} of {len(files)} uploaded dataset(s).",
        "processed_datasets": results,
        "errors": errors
    }
