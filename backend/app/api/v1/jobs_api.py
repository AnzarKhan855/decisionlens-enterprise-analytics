from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid
from datetime import datetime, timezone
import threading

from app.core.rbac import require_permission
from app.logging.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/jobs",
    tags=["Async Job Management"],
    dependencies=[Depends(require_permission("view_dashboards"))]
)

_jobs_lock = threading.Lock()
_jobs_store: Dict[str, Dict[str, Any]] = {}


class JobSubmitRequest(BaseModel):
    job_type: str
    params: Optional[Dict[str, Any]] = None


def create_job(job_type: str, params: Optional[Dict[str, Any]] = None) -> str:
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    with _jobs_lock:
        _jobs_store[job_id] = {
            "job_id": job_id,
            "job_type": job_type,
            "params": params or {},
            "status": "processing",
            "progress_pct": 10,
            "stage": "Job initialized",
            "stages": [
                {"name": "Initialization", "status": "completed"},
                {"name": "Data Validation", "status": "in_progress"},
                {"name": "Computation", "status": "pending"},
                {"name": "Result Finalization", "status": "pending"},
            ],
            "result": None,
            "error": None,
            "created_at": now,
            "updated_at": now,
        }
    return job_id


def update_job_progress(job_id: str, progress_pct: int, stage: str, stage_index: int = 1):
    with _jobs_lock:
        if job_id in _jobs_store:
            job = _jobs_store[job_id]
            job["progress_pct"] = progress_pct
            job["stage"] = stage
            job["updated_at"] = datetime.now(timezone.utc).isoformat()
            if "stages" in job and 0 <= stage_index < len(job["stages"]):
                for i in range(stage_index):
                    job["stages"][i]["status"] = "completed"
                job["stages"][stage_index]["status"] = "in_progress"


def complete_job(job_id: str, result: Dict[str, Any]):
    with _jobs_lock:
        if job_id in _jobs_store:
            job = _jobs_store[job_id]
            job["status"] = "completed"
            job["progress_pct"] = 100
            job["stage"] = "Completed successfully"
            job["result"] = result
            job["updated_at"] = datetime.now(timezone.utc).isoformat()
            if "stages" in job:
                for st in job["stages"]:
                    st["status"] = "completed"


def fail_job(job_id: str, error_message: str):
    with _jobs_lock:
        if job_id in _jobs_store:
            job = _jobs_store[job_id]
            job["status"] = "failed"
            job["error"] = error_message
            job["stage"] = f"Failed: {error_message}"
            job["updated_at"] = datetime.now(timezone.utc).isoformat()


def _run_report_job(job_id: str, dataset_id: Optional[str]):
    try:
        update_job_progress(job_id, 30, "Validating dataset & quality metrics", 1)
        from app.api.v1.reports_api import _get_report_data
        report = _get_report_data(dataset_id)
        update_job_progress(job_id, 80, "Finalizing executive report findings", 2)
        complete_job(job_id, report)
    except Exception as exc:
        logger.error("[Async Job %s] Report generation failed: %s", job_id, exc)
        fail_job(job_id, str(exc))


def _run_strategy_job(job_id: str, workspace_id: Optional[str]):
    try:
        update_job_progress(job_id, 40, "Calculating strategic variance & drivers", 1)
        from app.api.v1.strategy_api import get_strategic_report
        strategy = get_strategic_report()
        update_job_progress(job_id, 85, "Synthesizing executive priorities & risk matrix", 2)
        complete_job(job_id, strategy)
    except Exception as exc:
        logger.error("[Async Job %s] Strategy generation failed: %s", job_id, exc)
        fail_job(job_id, str(exc))


def _run_scenario_job(job_id: str, changes: list, dataset_id: Optional[str]):
    try:
        update_job_progress(job_id, 40, "Evaluating lever sensitivity & metric relationships", 1)
        from app.api.v1.scenario_api import ScenarioSimulateRequest, simulate_scenario_data_driven
        req = ScenarioSimulateRequest(changes=changes)
        res = simulate_scenario_data_driven(req, dataset_id=dataset_id)
        update_job_progress(job_id, 90, "Recalculating forecast & estimated impact", 2)
        complete_job(job_id, res)
    except Exception as exc:
        logger.error("[Async Job %s] Scenario simulation failed: %s", job_id, exc)
        fail_job(job_id, str(exc))


@router.post("/submit")
def submit_job(req: JobSubmitRequest, background_tasks: BackgroundTasks):
    params = req.params or {}
    job_id = create_job(req.job_type, params)

    if req.job_type == "report":
        background_tasks.add_task(_run_report_job, job_id, params.get("dataset_id"))
    elif req.job_type == "strategy":
        background_tasks.add_task(_run_strategy_job, job_id, params.get("workspace_id"))
    elif req.job_type == "scenario":
        background_tasks.add_task(_run_scenario_job, job_id, params.get("changes", []), params.get("dataset_id"))
    else:
        fail_job(job_id, f"Unsupported job_type '{req.job_type}'")

    return {
        "job_id": job_id,
        "status": "processing",
        "message": f"Job '{req.job_type}' submitted successfully.",
    }


@router.get("/{job_id}")
def get_job_details(job_id: str):
    with _jobs_lock:
        if job_id not in _jobs_store:
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
        return _jobs_store[job_id]


@router.get("/{job_id}/status")
def get_job_status(job_id: str):
    with _jobs_lock:
        if job_id not in _jobs_store:
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
        job = _jobs_store[job_id]
        return {
            "job_id": job_id,
            "status": job["status"],
            "progress_pct": job["progress_pct"],
            "stage": job["stage"],
            "stages": job.get("stages", []),
            "error": job["error"],
            "updated_at": job["updated_at"],
        }
