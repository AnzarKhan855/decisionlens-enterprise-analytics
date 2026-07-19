from fastapi import APIRouter

from app.services.dashboard_service import get_overview

router = APIRouter()


@router.get("/overview")
def dashboard_overview():
    return get_overview()