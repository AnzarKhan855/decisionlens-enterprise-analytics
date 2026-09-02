from fastapi import APIRouter, Depends
from app.analytics.system_telemetry_engine import SystemTelemetryEngine
from app.core.rbac import require_role, SUPER_ADMIN, ORGANIZATION_ADMIN

router = APIRouter(
    prefix="/monitoring",
    tags=["Enterprise Operations Monitoring (Grafana Spec)"],
    dependencies=[Depends(require_role([SUPER_ADMIN, ORGANIZATION_ADMIN]))]
)


@router.get("/metrics")
def get_system_metrics():
    return SystemTelemetryEngine.get_realtime_metrics()


@router.get("/charts")
def get_grafana_charts():
    return SystemTelemetryEngine.get_grafana_charts()


@router.get("/workers")
def get_worker_status():
    return {
        "workers": SystemTelemetryEngine.get_grafana_charts().get("worker_health", [])
    }
