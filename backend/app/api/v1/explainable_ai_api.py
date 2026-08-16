from fastapi import APIRouter, Query, Body
from typing import Optional, Dict, Any
from app.ai.universal_copilot_brain import UniversalAIBrain

router = APIRouter(prefix="/ai/xai", tags=["Explainable AI (OpenAI Enterprise Spec)"])


@router.get("/insights")
def get_explainable_ai_insights(workspace_id: Optional[str] = Query(None)):
    response = UniversalAIBrain.query(
        question="Generate explainable AI insights and business intelligence for this dataset.",
        workspace_id=workspace_id,
    ) or {}
    support = response.get("support") or {}
    analytics = support.get("analytics") if isinstance(support, dict) else {}
    if not isinstance(analytics, dict):
        analytics = {}
    critical = analytics.get("critical_findings") or []
    positive = analytics.get("positive_findings") or []
    insights = critical + positive
    if not insights:
        insights = response.get("evidence") or []
    return {
        "workspace_id": workspace_id or "active",
        "insights_count": len(insights),
        "insights": insights,
    }


@router.post("/explain")
def explain_specific_finding(body: Dict[str, Any] = Body(...)):
    finding = body.get("finding", "Primary Metric Performance")
    ws_id = body.get("workspace_id")
    response = UniversalAIBrain.query(
        question=f"Explain the finding: {finding}",
        workspace_id=ws_id,
    ) or {}
    support = response.get("support") or {}
    reasoning = support.get("business_reasoning", "") if isinstance(support, dict) else ""
    return {
        "finding_queried": finding,
        "explanation_payload": {
            "finding": finding,
            "explanation": response.get("answer", ""),
            "evidence": response.get("evidence", []),
            "confidence": response.get("confidence", 0.0),
            "reasoning": reasoning,
        }
    }
