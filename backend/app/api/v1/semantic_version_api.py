from fastapi import APIRouter, Query, Body, HTTPException, Depends
from typing import Optional, Dict, Any
from app.analytics.semantic_version_engine import SemanticModelVersionEngine
from app.semantic_model.engine import build_semantic_model
from app.core.rbac import get_current_user_from_token, require_role, SUPER_ADMIN, ORGANIZATION_ADMIN

router = APIRouter(
    prefix="/semantic",
    tags=["Semantic Model Version Control (Microsoft Fabric Spec)"],
    dependencies=[Depends(get_current_user_from_token)]
)


@router.get("/versions/{workspace_id}")
def get_semantic_versions(workspace_id: str):
    versions = SemanticModelVersionEngine.get_versions(workspace_id)
    if not versions:
        # Create baseline v1.0.0 commit if none exists
        sem = build_semantic_model(workspace_id=workspace_id)
        v1 = SemanticModelVersionEngine.commit_version(
            workspace_id=workspace_id,
            semantic_model=sem,
            tag="v1.0.0",
            notes="Initial baseline semantic model commit"
        )
        return [v1]
    return versions


@router.post("/commit")
def commit_semantic_version(
    body: Dict[str, Any] = Body(...),
    user: Dict[str, Any] = Depends(require_role([SUPER_ADMIN, ORGANIZATION_ADMIN]))
):
    from app.services.workspace_service import EnterpriseWorkspaceManager
    ws_id = body.get("workspace_id") or EnterpriseWorkspaceManager.get_active_workspace_id()
    if not ws_id:
        raise HTTPException(status_code=400, detail="workspace_id is required")
    tag = body.get("tag", "v1.1.0")
    notes = body.get("notes", "Manual semantic model commit")
    author = body.get("author", "Enterprise Administrator")

    sem = build_semantic_model(workspace_id=ws_id, force_rebuild=True)
    return SemanticModelVersionEngine.commit_version(
        workspace_id=ws_id,
        semantic_model=sem,
        author=author,
        tag=tag,
        notes=notes
    )


@router.post("/rollback")
def rollback_semantic_version(body: Dict[str, Any] = Body(...)):
    ws_id = body.get("workspace_id")
    v_id = body.get("version_id")
    if not ws_id or not v_id:
        raise HTTPException(status_code=400, detail="workspace_id and version_id are required")
    try:
        return SemanticModelVersionEngine.rollback_version(workspace_id=ws_id, version_id=v_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/compare")
def compare_semantic_versions(workspace_id: str = Query(...), v1_id: str = Query(...), v2_id: str = Query(...)):
    return SemanticModelVersionEngine.compare_versions(workspace_id=workspace_id, v1_id=v1_id, v2_id=v2_id)
