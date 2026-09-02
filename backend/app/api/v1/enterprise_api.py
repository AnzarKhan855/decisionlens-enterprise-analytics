from fastapi import APIRouter, Query, Depends
from typing import Optional, Dict, Any
from app.services.enterprise_search import EnterpriseSearchEngine
from app.services.task_queue import EnterpriseTaskQueue
from app.core.rbac import get_current_user_from_token

router = APIRouter(
    tags=["Enterprise Intelligence v13.0"],
    dependencies=[Depends(get_current_user_from_token)]
)


@router.get("/search")
def search_enterprise(q: str = Query(..., description="Query term to search across tables, KPIs, and reports")):
    return EnterpriseSearchEngine.search(q)


@router.get("/queue/job/{job_id}")
def get_queue_job_status(job_id: str):
    job = EnterpriseTaskQueue.get_job(job_id)
    if not job:
        return {"status": "NOT_FOUND", "job_id": job_id}
    return job
