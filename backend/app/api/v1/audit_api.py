from fastapi import APIRouter, Query, Response, Body, Depends
from typing import Optional, Dict, Any
from app.services.audit_logger import EnterpriseAuditLogger
from app.core.rbac import require_permission

router = APIRouter(prefix="/audit", tags=["Enterprise Audit Logging System"])


@router.get("/logs", dependencies=[Depends(require_permission("view_audit_logs"))])
def get_audit_logs(
    user_email: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    workspace_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    return EnterpriseAuditLogger.get_logs(
        user_email=user_email,
        action=action,
        workspace_id=workspace_id,
        search=search,
        limit=limit,
        offset=offset
    )


@router.get("/export-csv", dependencies=[Depends(require_permission("view_audit_logs"))])
def export_audit_logs_csv():
    csv_content = EnterpriseAuditLogger.export_csv()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=decisionlens_audit_trail.csv"}
    )


@router.post("/log")
def log_audit_event(body: Dict[str, Any] = Body(...)):
    user_email = body.get("user", "admin@decisionlens.ai")
    action = body.get("action", "AI Query")
    ws_id = body.get("workspace_id")
    status = body.get("status", "SUCCESS")
    res_affected = body.get("affected_resource", "Dataset View")
    duration = body.get("duration_ms", 12.5)

    return EnterpriseAuditLogger.log_action(
        user_email=user_email,
        action=action,
        workspace_id=ws_id,
        status=status,
        affected_resource=res_affected,
        duration_ms=duration
    )
