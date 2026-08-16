from fastapi import APIRouter, Query, Body, HTTPException
from typing import Optional, Dict, Any
from app.services.refresh_scheduler import EnterpriseRefreshScheduler

router = APIRouter(prefix="/scheduler", tags=["Enterprise Refresh Scheduling (Fabric Spec)"])


@router.post("/schedules")
def configure_refresh_schedule(body: Dict[str, Any] = Body(...)):
    ws_id = body.get("workspace_id", "ws-enterprise-generic")
    cadence = body.get("cadence", "Daily")
    cron_expr = body.get("cron_expression")
    email = body.get("notification_email", "admin@decisionlens.ai")
    active = body.get("is_active", True)
    return EnterpriseRefreshScheduler.configure_schedule(
        workspace_id=ws_id,
        cadence=cadence,
        cron_expression=cron_expr,
        notification_email=email,
        is_active=active
    )


@router.get("/schedules/{workspace_id}")
def get_refresh_schedule(workspace_id: str):
    return EnterpriseRefreshScheduler.get_schedule(workspace_id)


@router.post("/trigger")
def trigger_workspace_refresh(body: Dict[str, Any] = Body(...)):
    ws_id = body.get("workspace_id", "ws-enterprise-generic")
    triggered_by = body.get("triggered_by", "Manual API Trigger")
    return EnterpriseRefreshScheduler.trigger_workspace_refresh(workspace_id=ws_id, triggered_by=triggered_by)


@router.get("/history/{workspace_id}")
def get_refresh_history(workspace_id: str):
    history = EnterpriseRefreshScheduler.get_history(workspace_id)
    if not history:
        # Generate baseline history record
        b_entry = EnterpriseRefreshScheduler.trigger_workspace_refresh(workspace_id=workspace_id, triggered_by="Baseline Schedule Initialization")
        return [b_entry]
    return history
