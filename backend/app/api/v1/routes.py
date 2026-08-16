from fastapi import APIRouter

from app.api.v1.analytics import router as analytics_router, dashboard_router
from app.api.v1.insights import router as insights_router
from app.api.v1.upload import router as upload_router
from app.api.v1.forecasting_api import router as forecasting_router
from app.api.v1.scenario_api import router as scenario_router
from app.api.v1.ai_assistant_api import router as ai_assistant_router
from app.api.v1.copilot_api import router as copilot_router
from app.api.v1.auth import router as auth_router
from app.api.v1.datasets_api import router as datasets_router
from app.api.v1.reports_api import router as reports_router
from app.api.v1.cybersecurity_api import router as cybersecurity_router

from app.api.v1.enterprise_api import router as enterprise_router
from app.api.v1.audit_api import router as audit_router
from app.api.v1.semantic_version_api import router as semantic_version_router
from app.api.v1.explainable_ai_api import router as xai_router
from app.api.v1.lineage_api import router as lineage_router
from app.api.v1.catalog_api import router as catalog_router
from app.api.v1.quality_api import router as quality_router
from app.api.v1.collaboration_api import router as collab_router
from app.api.v1.scheduler_api import router as scheduler_router
from app.api.v1.monitoring_api import router as monitoring_router
from app.api.v1.sso_api import router as sso_router

from app.api.v1.semantic_model_api import router as semantic_model_router
from app.api.v1.intelligence_api import router as intelligence_router
from app.api.v1.dynamic_kpi_api import router as dynamic_kpi_router
from app.api.v1.strategy_api import router as strategy_router


api_router = APIRouter()

api_router.include_router(sso_router)
api_router.include_router(monitoring_router)
api_router.include_router(scheduler_router)
api_router.include_router(collab_router)
api_router.include_router(quality_router)
api_router.include_router(catalog_router)
api_router.include_router(lineage_router)
api_router.include_router(xai_router)
api_router.include_router(semantic_version_router)
api_router.include_router(audit_router)
api_router.include_router(enterprise_router)
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication & Users"])
api_router.include_router(datasets_router)
api_router.include_router(reports_router)
api_router.include_router(cybersecurity_router)
api_router.include_router(analytics_router)
api_router.include_router(dashboard_router)
api_router.include_router(insights_router, prefix="/analytics", tags=["Analytics Insights"])
api_router.include_router(forecasting_router)
api_router.include_router(scenario_router)
api_router.include_router(ai_assistant_router, prefix="/ai", tags=["AI Analyst Assistant"])
api_router.include_router(upload_router)
api_router.include_router(semantic_model_router, tags=["Enterprise Semantic Model"])
api_router.include_router(intelligence_router, tags=["Dataset Intelligence Layer"])
api_router.include_router(dynamic_kpi_router)
api_router.include_router(strategy_router, tags=["Enterprise Strategy & Decision Intelligence"])