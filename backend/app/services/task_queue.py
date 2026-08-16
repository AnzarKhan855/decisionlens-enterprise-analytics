from typing import Dict, Any, List, Optional
import json
import time
from pathlib import Path
from app.database.storage import STORAGE_DIR

QUEUE_FILE = STORAGE_DIR / "task_queue_state.json"


class EnterpriseTaskQueue:
    """
    DecisionLens v13.1 Production Durable Task Queue & Event Stream Engine.
    Tracks state transitions: QUEUED -> EXTRACTING -> PROFILING -> RELATIONSHIPS -> AI_ANALYSIS -> COMPLETED.
    """
    _jobs: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def _load(cls):
        if QUEUE_FILE.exists():
            try:
                with open(QUEUE_FILE, "r") as f:
                    cls._jobs = json.load(f)
            except Exception:
                pass

    @classmethod
    def _save(cls):
        try:
            with open(QUEUE_FILE, "w") as f:
                json.dump(cls._jobs, f, indent=2)
        except Exception:
            pass

    @classmethod
    def enqueue_job(cls, job_id: str, workspace_id: str, job_type: str = "workspace_ingestion") -> Dict[str, Any]:
        cls._load()
        job = {
            "job_id": job_id,
            "workspace_id": workspace_id,
            "job_type": job_type,
            "status": "QUEUED",
            "progress": 5,
            "current_step": "Queued in Persistent Task Queue",
            "created_at": time.time(),
            "updated_at": time.time(),
            "completed_steps": [],
            "remaining_steps": [
                "Extracting Archive & Parquet Conversion",
                "Schema & Column Profiling",
                "Cross-Table Relationship Discovery",
                "Executive Semantic Layer Construction",
                "AI Executive Briefing & Storytelling"
            ]
        }
        cls._jobs[job_id] = job
        cls._save()
        return job

    @classmethod
    def update_job(cls, job_id: str, status: str, progress: int, current_step: str, step_completed: Optional[str] = None):
        cls._load()
        if job_id in cls._jobs:
            job = cls._jobs[job_id]
            job["status"] = status
            job["progress"] = progress
            job["current_step"] = current_step
            job["updated_at"] = time.time()
            if step_completed and step_completed not in job["completed_steps"]:
                job["completed_steps"].append(step_completed)
                if step_completed in job["remaining_steps"]:
                    job["remaining_steps"].remove(step_completed)
            cls._save()

    @classmethod
    def get_job(cls, job_id: str) -> Optional[Dict[str, Any]]:
        cls._load()
        return cls._jobs.get(job_id)

    @classmethod
    def get_workspace_job(cls, workspace_id: str) -> Optional[Dict[str, Any]]:
        cls._load()
        for j in cls._jobs.values():
            if j.get("workspace_id") == workspace_id:
                return j
        return None
