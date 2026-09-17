import os
import time
import uuid
import threading
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.logging.logger import get_logger

logger = get_logger(__name__)


class JobState(str, Enum):
    CREATED = "CREATED"
    UPLOADING = "UPLOADING"
    UPLOADED = "UPLOADED"
    VALIDATING = "VALIDATING"
    PROCESSING = "PROCESSING"
    PROFILING = "PROFILING"
    BUILDING_SEMANTIC_MODEL = "BUILDING_SEMANTIC_MODEL"
    READY = "READY"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


# Stage display names and default percentage milestones
STAGE_PROGRESS_MAP = {
    JobState.CREATED: (5, "Job initialized"),
    JobState.UPLOADING: (10, "Uploading dataset stream to durable storage"),
    JobState.UPLOADED: (20, "File received and integrity verified"),
    JobState.VALIDATING: (35, "Validating schema, encoding, and data safety"),
    JobState.PROCESSING: (55, "Converting raw data to high-performance analytical Parquet"),
    JobState.PROFILING: (75, "Analyzing distributions, statistics, and quality metrics"),
    JobState.BUILDING_SEMANTIC_MODEL: (90, "Discovering relationships and building executive semantic model"),
    JobState.READY: (100, "Dataset fully ingested and ready for executive intelligence"),
    JobState.FAILED: (100, "Dataset processing failed"),
    JobState.CANCELLED: (100, "Dataset ingestion cancelled by user"),
}


class IngestionJobService:
    """
    Enterprise Ingestion Job Service.
    Orchestrates the asynchronous ingestion lifecycle, state machine transitions,
    durable MongoDB persistence, and stage-by-stage telemetry for all datasets.
    """

    _lock = threading.Lock()
    _jobs_cache: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def _get_mongo_collection(cls):
        try:
            from app.database.mongodb import ingestion_jobs
            return ingestion_jobs
        except Exception as e:
            logger.debug("[IngestionJobService] MongoDB collection unavailable: %s", e)
            return None

    @classmethod
    def create_job(
        cls,
        workspace_id: str,
        dataset_id: str,
        filename: str,
        file_size_bytes: int = 0,
        user_email: str = "",
        initial_status: JobState = JobState.UPLOADED,
    ) -> Dict[str, Any]:
        """Creates a new durable ingestion job and persists it to MongoDB and memory."""
        job_id = f"job-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        pct, msg = STAGE_PROGRESS_MAP.get(initial_status, (20, "File uploaded"))

        job_doc: Dict[str, Any] = {
            "job_id": job_id,
            "workspace_id": workspace_id,
            "dataset_id": dataset_id,
            "filename": filename,
            "file_size_bytes": file_size_bytes,
            "user_email": user_email,
            "status": initial_status.value,
            "current_stage": initial_status.value,
            "progress_pct": pct,
            "message": msg,
            "created_at": now,
            "updated_at": now,
            "completed_at": None,
            "error": None,
            "metrics": {
                "rows": 0,
                "columns": 0,
                "total_duration_ms": 0.0,
                "stage_timings_ms": {},
            },
            "steps": [
                {"step": "File Upload & Storage", "status": "COMPLETED", "pct": 20},
                {"step": "Schema & Encoding Validation", "status": "PENDING", "pct": 35},
                {"step": "Analytical Parquet Conversion", "status": "PENDING", "pct": 55},
                {"step": "Data Quality & Profiling", "status": "PENDING", "pct": 75},
                {"step": "Executive Semantic Model", "status": "PENDING", "pct": 90},
                {"step": "Executive Intelligence Preparation", "status": "PENDING", "pct": 100},
            ]
        }

        with cls._lock:
            cls._jobs_cache[job_id] = job_doc

        coll = cls._get_mongo_collection()
        if coll is not None:
            try:
                coll.insert_one(job_doc.copy())
            except Exception as exc:
                logger.warning("[IngestionJobService] Failed to persist new job %s to Mongo: %s", job_id, exc)

        # Notify workspace service of new processing state
        try:
            from app.services.workspace_service import EnterpriseWorkspaceManager
            EnterpriseWorkspaceManager.update_processing_status(
                workspace_id,
                status="PROCESSING",
                progress=pct,
                current_step=msg,
            )
        except Exception:
            pass

        logger.info("[IngestionJobService] Created job %s for workspace %s (filename: %s)", job_id, workspace_id, filename)
        return job_doc

    @classmethod
    def update_job(
        cls,
        job_id: str,
        status: JobState,
        progress_pct: Optional[int] = None,
        stage_name: Optional[str] = None,
        message: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
        metrics_update: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Updates job status, progress, stage, and metrics in memory and MongoDB."""
        now = datetime.now(timezone.utc).isoformat()
        default_pct, default_msg = STAGE_PROGRESS_MAP.get(status, (progress_pct or 0, stage_name or status.value))

        pct = progress_pct if progress_pct is not None else default_pct
        msg = message or default_msg
        stage = stage_name or status.value

        with cls._lock:
            job = cls._jobs_cache.get(job_id)
            if not job:
                # Attempt to retrieve from Mongo
                coll = cls._get_mongo_collection()
                if coll is not None:
                    job = coll.find_one({"job_id": job_id})
                    if job:
                        job.pop("_id", None)
                        cls._jobs_cache[job_id] = job

            if not job:
                logger.warning("[IngestionJobService] Cannot update unknown job %s", job_id)
                return None

            job["status"] = status.value
            job["current_stage"] = stage
            job["progress_pct"] = pct
            job["message"] = msg
            job["updated_at"] = now

            if status in (JobState.READY, JobState.FAILED, JobState.CANCELLED):
                job["completed_at"] = now

            if error_details:
                job["error"] = error_details

            if metrics_update:
                cur_metrics = job.get("metrics", {})
                cur_metrics.update(metrics_update)
                job["metrics"] = cur_metrics

            # Update step statuses
            for s in job.get("steps", []):
                step_pct = s.get("pct", 100)
                if pct >= step_pct:
                    s["status"] = "COMPLETED"
                elif status == JobState.FAILED and s.get("status") != "COMPLETED":
                    s["status"] = "FAILED"
                    break
                elif s.get("status") != "COMPLETED":
                    s["status"] = "PROCESSING" if pct >= (step_pct - 20) else "PENDING"

            job_copy = job.copy()

        # Update MongoDB
        coll = cls._get_mongo_collection()
        if coll is not None:
            try:
                coll.update_one(
                    {"job_id": job_id},
                    {"$set": {
                        "status": job["status"],
                        "current_stage": job["current_stage"],
                        "progress_pct": job["progress_pct"],
                        "message": job["message"],
                        "updated_at": job["updated_at"],
                        "completed_at": job["completed_at"],
                        "error": job["error"],
                        "metrics": job["metrics"],
                        "steps": job["steps"],
                    }}
                )
            except Exception as exc:
                logger.warning("[IngestionJobService] Failed to update job %s in Mongo: %s", job_id, exc)

        # Mirror status to workspace manager
        ws_id = job.get("workspace_id")
        if ws_id:
            try:
                from app.services.workspace_service import EnterpriseWorkspaceManager
                ws_status = "COMPLETED" if status == JobState.READY else ("FAILED" if status == JobState.FAILED else "PROCESSING")
                EnterpriseWorkspaceManager.update_processing_status(
                    ws_id,
                    status=ws_status,
                    progress=pct,
                    current_step=msg,
                )
            except Exception:
                pass

        return job_copy

    @classmethod
    def get_job(cls, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a job by ID from local cache or MongoDB."""
        with cls._lock:
            if job_id in cls._jobs_cache:
                return cls._jobs_cache[job_id].copy()

        coll = cls._get_mongo_collection()
        if coll is not None:
            try:
                doc = coll.find_one({"job_id": job_id})
                if doc:
                    doc.pop("_id", None)
                    with cls._lock:
                        cls._jobs_cache[job_id] = doc
                    return doc
            except Exception as exc:
                logger.warning("[IngestionJobService] Failed to query job %s: %s", job_id, exc)

        return None

    @classmethod
    def get_active_job_for_workspace(cls, workspace_id: str) -> Optional[Dict[str, Any]]:
        """Returns the most recent active or recently completed job for a workspace."""
        with cls._lock:
            matching = [j for j in cls._jobs_cache.values() if j.get("workspace_id") == workspace_id]
            if matching:
                matching.sort(key=lambda x: x.get("created_at", ""), reverse=True)
                return matching[0].copy()

        coll = cls._get_mongo_collection()
        if coll is not None:
            try:
                from pymongo import DESCENDING
                doc = coll.find_one({"workspace_id": workspace_id}, sort=[("created_at", DESCENDING)])
                if doc:
                    doc.pop("_id", None)
                    with cls._lock:
                        cls._jobs_cache[doc["job_id"]] = doc
                    return doc
            except Exception as exc:
                logger.warning("[IngestionJobService] Failed to find job for ws %s: %s", workspace_id, exc)

        return None

    @classmethod
    def cancel_job(cls, job_id: str) -> bool:
        """Cancels a running job."""
        job = cls.get_job(job_id)
        if not job:
            return False
        if job.get("status") in (JobState.READY.value, JobState.FAILED.value, JobState.CANCELLED.value):
            return False
        cls.update_job(job_id, JobState.CANCELLED, progress_pct=100, message="Ingestion cancelled by user.")
        return True

    @classmethod
    def run_pipeline(
        cls,
        job_id: str,
        raw_file_path: Path,
        workspace_id: str,
        filename: str,
        user: Optional[Dict[str, Any]] = None,
        extension: str = ".csv",
    ) -> Dict[str, Any]:
        """
        Executes the end-to-end analytical ingestion pipeline.
        Designed to run safely in background threads or synchronously when requested.
        """
        t_start = time.perf_counter()
        timings: Dict[str, float] = {}
        stage_now = JobState.VALIDATING

        logger.info("[IngestionPipeline] Starting async execution for job %s (file: %s)", job_id, filename)

        try:
            # Check for early cancellation
            job = cls.get_job(job_id)
            if job and job.get("status") == JobState.CANCELLED.value:
                logger.info("[IngestionPipeline] Job %s was cancelled before execution.", job_id)
                return job

            # ------------------------------------------------------------------
            # Stage 1: VALIDATING
            # ------------------------------------------------------------------
            stage_now = JobState.VALIDATING
            t0 = time.perf_counter()
            cls.update_job(job_id, JobState.VALIDATING, 35, message="Validating schema, encoding, and data safety")

            if not raw_file_path.exists() or raw_file_path.stat().st_size == 0:
                raise ValueError(f"Uploaded file '{filename}' does not exist or is empty.")

            timings["validation_ms"] = round((time.perf_counter() - t0) * 1000, 2)

            # ------------------------------------------------------------------
            # Stage 2: PROCESSING (Parquet Conversion)
            # ------------------------------------------------------------------
            stage_now = JobState.PROCESSING
            t0 = time.perf_counter()
            cls.update_job(job_id, JobState.PROCESSING, 55, message="Converting raw data to high-performance analytical Parquet")

            from app.ingestion.generic_loader import GenericDataLoader
            orig_stem = Path(filename).stem.lower().replace("-", "_").replace(" ", "_")
            clean_name = f"{workspace_id}__{orig_stem}"

            parquet_path = GenericDataLoader.convert_to_parquet(raw_file_path, clean_name)
            if not parquet_path.exists() or parquet_path.stat().st_size == 0:
                raise ValueError("Parquet conversion resulted in an empty or missing file.")

            timings["parquet_conversion_ms"] = round((time.perf_counter() - t0) * 1000, 2)

            # ------------------------------------------------------------------
            # Stage 3: PROFILING (Domain & Data Quality)
            # ------------------------------------------------------------------
            stage_now = JobState.PROFILING
            t0 = time.perf_counter()
            cls.update_job(job_id, JobState.PROFILING, 75, message="Analyzing distributions, statistics, and quality metrics")

            from app.ingestion.dataset_detector import DatasetDetector
            from app.ingestion.validator import DataValidator

            detection = DatasetDetector.detect_from_parquet(parquet_path)
            dataset_type = detection.get("dataset_type", "Generic")

            validation_report = DataValidator.validate(parquet_path)
            health_score = validation_report.get("health_score", 100)
            semantic_profile = validation_report.get("semantic_profile", {})

            total_rows = semantic_profile.get("total_rows", 0)
            total_cols = semantic_profile.get("total_columns", 0)

            # Register dataset row in SQLite metadata
            db = None
            try:
                from app.database.connection import SessionLocal
                from app.database.crud import save_dataset
                db = SessionLocal()
                save_dataset(
                    db=db,
                    filename=filename,
                    file_path=str(parquet_path),
                    dataset_type=dataset_type,
                    rows=total_rows,
                    columns=total_cols,
                    file_type=extension.replace(".", ""),
                )
            except Exception as db_err:
                logger.warning("[IngestionPipeline] SQLite dataset registration warning: %s", db_err)
            finally:
                if db is not None:
                    db.close()

            timings["profiling_ms"] = round((time.perf_counter() - t0) * 1000, 2)

            # ------------------------------------------------------------------
            # Stage 4: BUILDING_SEMANTIC_MODEL
            # ------------------------------------------------------------------
            stage_now = JobState.BUILDING_SEMANTIC_MODEL
            t0 = time.perf_counter()
            cls.update_job(job_id, JobState.BUILDING_SEMANTIC_MODEL, 90, message="Discovering relationships and building executive semantic model")

            from app.intelligence.dataset_intelligence_layer import DatasetIntelligenceLayer
            intelligence_result = DatasetIntelligenceLayer.analyze(
                workspace_id=workspace_id,
                parquet_path=parquet_path,
                force_rebuild=True,
            )

            from app.services.workspace_service import EnterpriseWorkspaceManager
            from app.semantic_model.engine import invalidate_semantic_model_cache
            from app.services.analytics_cache_service import AnalyticsCacheService

            ws_title = orig_stem.replace("_", " ").title()
            cols_summary = [
                {"name": c, "type": semantic_profile.get("columns", {}).get(c, {}).get("inferred_type", "VARCHAR")}
                for c in semantic_profile.get("columns", {})
            ]

            EnterpriseWorkspaceManager.create_or_get_workspace(
                workspace_id,
                ws_title,
                industry=dataset_type,
                created_by=user.get("email", "") if user else ""
            )
            EnterpriseWorkspaceManager.register_table(
                workspace_id,
                orig_stem,
                cols_summary,
                total_rows,
                str(parquet_path)
            )
            EnterpriseWorkspaceManager.set_active_workspace(workspace_id)

            invalidate_semantic_model_cache()
            try:
                AnalyticsCacheService.invalidate(workspace_id)
            except Exception:
                pass

            timings["semantic_model_ms"] = round((time.perf_counter() - t0) * 1000, 2)
            total_duration_ms = round((time.perf_counter() - t_start) * 1000, 2)
            timings["total_duration_ms"] = total_duration_ms

            # ------------------------------------------------------------------
            # Stage 5: READY
            # ------------------------------------------------------------------
            final_job = cls.update_job(
                job_id,
                JobState.READY,
                progress_pct=100,
                stage_name="READY",
                message="Dataset successfully processed and workspace activated.",
                metrics_update={
                    "rows": total_rows,
                    "columns": total_cols,
                    "total_duration_ms": total_duration_ms,
                    "stage_timings_ms": timings,
                    "health_score": health_score,
                    "domain": getattr(intelligence_result, "domain", dataset_type),
                }
            )

            logger.info(
                "[IngestionPipeline] Job %s COMPLETED in %.2f ms (%d rows, %d cols)",
                job_id, total_duration_ms, total_rows, total_cols
            )
            return final_job or {}

        except Exception as exc:
            total_duration_ms = round((time.perf_counter() - t_start) * 1000, 2)
            logger.exception("[IngestionPipeline] Job %s FAILED at stage %s: %s", job_id, stage_now, exc)

            err_info = {
                "failed_stage": stage_now.value if hasattr(stage_now, "value") else str(stage_now),
                "exception_class": exc.__class__.__name__,
                "message": str(exc),
                "suggested_fix": "Please check dataset encoding, headers, delimiter, and formatting.",
            }

            failed_job = cls.update_job(
                job_id,
                JobState.FAILED,
                progress_pct=100,
                stage_name="FAILED",
                message=f"Processing failed at {stage_now}: {str(exc)}",
                error_details=err_info,
                metrics_update={"total_duration_ms": total_duration_ms, "stage_timings_ms": timings}
            )

            try:
                from app.services.workspace_service import EnterpriseWorkspaceManager
                EnterpriseWorkspaceManager.update_processing_status(
                    workspace_id,
                    status="FAILED",
                    progress=100,
                    current_step=f"Processing failed at {stage_now}",
                )
            except Exception:
                pass

            return failed_job or {}
