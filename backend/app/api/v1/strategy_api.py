from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, Dict, Any, List

from app.services.enterprise_strategy_engine import EnterpriseStrategyEngine
from app.services.workspace_service import EnterpriseWorkspaceManager
from app.core.rbac import require_permission
from app.logging.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/strategy",
    tags=["Enterprise Strategy & Decision Intelligence"],
    dependencies=[Depends(require_permission("view_dashboards"))]
)


@router.get("")
def get_strategy_report_active():
    try:
        from app.services.workspace_service import EnterpriseWorkspaceManager
        workspace_id = EnterpriseWorkspaceManager.get_active_workspace_id()
        if not workspace_id:
            raise HTTPException(status_code=404, detail="No active workspace found")
        result = EnterpriseStrategyEngine.analyze(workspace_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[StrategyAPI] %s", exc)
        raise HTTPException(status_code=500, detail="Unable to generate strategy report.")


@router.get("/{workspace_id}")
def get_strategy_report(workspace_id: str):
    try:
        result = EnterpriseStrategyEngine.analyze(workspace_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[StrategyAPI] %s", exc)
        raise HTTPException(status_code=500, detail="Unable to generate strategy report.")


@router.get("/{workspace_id}/briefing")
def get_executive_briefing(workspace_id: str, role: str = Query("CEO")):
    try:
        result = EnterpriseStrategyEngine.generate_executive_briefing(workspace_id, role=role)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[StrategyAPI] Briefing failed: %s", exc)
        raise HTTPException(status_code=500, detail="Unable to generate executive briefing.")


@router.get("/{workspace_id}/decision-tree")
def get_decision_tree(workspace_id: str):
    try:
        result = EnterpriseStrategyEngine.get_decision_tree(workspace_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[StrategyAPI] Decision tree failed: %s", exc)
        raise HTTPException(status_code=500, detail="Unable to generate decision tree.")


@router.get("/{workspace_id}/risks")
def get_risk_profile(workspace_id: str):
    try:
        result = EnterpriseStrategyEngine.get_risk_profile(workspace_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[StrategyAPI] Risk profile failed: %s", exc)
        raise HTTPException(status_code=500, detail="Unable to generate risk profile.")


@router.get("/{workspace_id}/opportunities")
def get_opportunity_profile(workspace_id: str):
    try:
        result = EnterpriseStrategyEngine.get_opportunity_profile(workspace_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[StrategyAPI] Opportunity profile failed: %s", exc)
        raise HTTPException(status_code=500, detail="Unable to generate opportunity profile.")


@router.get("/{workspace_id}/scenario-history")
def get_scenario_history(workspace_id: str):
    try:
        items = EnterpriseStrategyEngine.get_scenario_history(workspace_id)
        return {"workspace_id": workspace_id, "scenarios": items}
    except Exception as exc:
        logger.error("[StrategyAPI] Scenario history failed: %s", exc)
        raise HTTPException(status_code=500, detail="Unable to fetch scenario history.")
