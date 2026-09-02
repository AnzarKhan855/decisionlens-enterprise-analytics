from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends
from app.core.rbac import get_current_user_from_token
from app.database.connection import SessionLocal
from app.database.crud import get_all_datasets
from app.database.storage import ParquetStorageManager
from app.ai.universal_copilot_brain import UniversalAIBrain

router = APIRouter(
    tags=["AI Analyst Assistant"],
    dependencies=[Depends(get_current_user_from_token)]
)


class AIQueryRequest(BaseModel):
    dataset_id: Optional[str] = None
    question: str


def _get_parquet_path(db, dataset_id: Optional[str] = None) -> Path:
    if dataset_id and dataset_id != "latest":
        path = ParquetStorageManager.get_parquet_path(dataset_id)
        if path and path.exists():
            return path

    best_path = UniversalAIBrain._resolve_parquet_path(workspace_id=None, dataset_id=dataset_id)
    if best_path and best_path.exists():
        return best_path

    raise HTTPException(status_code=404, detail="No active business workspace found.")


@router.post("/query")
def ask_ai_assistant(body: AIQueryRequest):
    db = SessionLocal()
    try:
        parquet_path = _get_parquet_path(db, body.dataset_id)
        response = UniversalAIBrain.query(
            question=body.question,
            dataset_id=body.dataset_id,
        )
        return {
            "dataset_id": body.dataset_id or "latest",
            "results": response
        }
    finally:
        db.close()
