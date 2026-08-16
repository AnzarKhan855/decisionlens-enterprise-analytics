from fastapi import APIRouter
from app.analytics.system_telemetry_engine import SystemTelemetryEngine

router = APIRouter(prefix="/monitoring", tags=["Enterprise Operations Monitoring (Grafana Spec)"])


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
