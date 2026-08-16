from fastapi import APIRouter, Query
from typing import Optional, Dict, Any
from app.services.enterprise_search import EnterpriseSearchEngine
from app.services.task_queue import EnterpriseTaskQueue

router = APIRouter(tags=["Enterprise Intelligence v13.0"])


@router.get("/search")
def search_enterprise(q: str = Query(..., description="Query term to search across tables, KPIs, and reports")):
    return EnterpriseSearchEngine.search(q)


@router.get("/queue/job/{job_id}")
def get_queue_job_status(job_id: str):
    job = EnterpriseTaskQueue.get_job(job_id)
    if not job:
        return {"status": "NOT_FOUND", "job_id": job_id}
    return job
