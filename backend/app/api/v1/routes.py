from fastapi import APIRouter

from app.api.v1.analytics import router as analytics_router
from app.api.v1.dashboard import router as dashboard_router

api_router = APIRouter()

api_router.include_router(
    analytics_router,
    prefix="/analytics",
    tags=["Analytics"]
)

api_router.include_router(
    dashboard_router,
    prefix="/dashboard",
    tags=["Dashboard"]
)