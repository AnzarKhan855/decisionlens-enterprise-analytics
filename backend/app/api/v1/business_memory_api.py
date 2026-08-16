from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from dataclasses import field

from app.memory.business_memory_engine import BusinessMemoryEngine
from app.reports.role_based_report_engine import RoleBasedReportEngine
from app.analytics.universal_engine import UniversalAnalyticsEngine
from app.schemas.analytics import AnalyticsResult
from app.semantic_model.core import SemanticModel
from app.semantic_model.engine import build_semantic_model
from app.services.workspace_service import EnterpriseWorkspaceManager
from app.database.duckdb_engine import DuckDBEngine
from app.core.rbac import require_permission
from app.logging.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    tags=["Business Memory & Reports"],
    dependencies=[Depends(require_permission("use_copilot"))]
)


class BusinessGoalRequest(BaseModel):
    workspace_id: str
    title: str
    description: str
    target_metric: Optional[str] = None
    target_value: Optional[float] = None
    current_value: Optional[float] = None
    deadline: Optional[str] = None
    owner: str = "Unassigned"
    priority: str = "MEDIUM"


class ExecutiveDecisionRequest(BaseModel):
    workspace_id: str
    title: str
    description: str
    decision_maker: str
    rationale: str
    expected_impact: str = ""
    metrics_affected: Optional[List[str]] = None
    deadline: Optional[str] = None
    status: str = "approved"


class MilestoneRequest(BaseModel):
    workspace_id: str
    title: str
    description: str
    milestone_type: str = "operational"
    date: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    owner: str = "Unassigned"


class UserFeedbackRequest(BaseModel):
    workspace_id: str
    session_id: str
    rating: int
    comment: str = ""
    category: str = "general"
    question: Optional[str] = None
    answer: Optional[str] = None


class ReportRequest(BaseModel):
    workspace_id: str
    audience: str = "CEO"
    session_id: str = "default"
    format: str = "json"


class ForecastAccuracyRequest(BaseModel):
    workspace_id: str
    forecast_id: str
    metric: str
    model_type: str
    predicted_value: float
    actual_value: float
    error_pct: float
    period: Optional[str] = None


# =====================================================================
# Business Goals
# =====================================================================
@router.post("/memory/goals")
def create_business_goal(req: BusinessGoalRequest):
    try:
        goal_id = BusinessMemoryEngine.save_business_goal(
            workspace_id=req.workspace_id,
            title=req.title,
            description=req.description,
            target_metric=req.target_metric,
            target_value=req.target_value,
            current_value=req.current_value,
            deadline=req.deadline,
            owner=req.owner,
            priority=req.priority,
        )
        return {"status": "success", "goal_id": goal_id}
    except Exception as e:
        logger.error("[Memory] %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/goals/{workspace_id}")
def get_business_goals(workspace_id: str, status: Optional[str] = None):
    try:
        goals = BusinessMemoryEngine.get_business_goals(workspace_id, status=status)
        return {"workspace_id": workspace_id, "goals": goals}
    except Exception as e:
        logger.error("[Memory] %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================================
# Executive Decisions
# =====================================================================
@router.post("/memory/decisions")
def create_executive_decision(req: ExecutiveDecisionRequest):
    try:
        decision_id = BusinessMemoryEngine.save_executive_decision(
            workspace_id=req.workspace_id,
            title=req.title,
            description=req.description,
            decision_maker=req.decision_maker,
            rationale=req.rationale,
            expected_impact=req.expected_impact,
            metrics_affected=req.metrics_affected,
            deadline=req.deadline,
            status=req.status,
        )
        return {"status": "success", "decision_id": decision_id}
    except Exception as e:
        logger.error("[Memory] %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/decisions/{workspace_id}")
def get_executive_decisions(workspace_id: str, limit: int = 50):
    try:
        decisions = BusinessMemoryEngine.get_executive_decisions(workspace_id, limit=limit)
        return {"workspace_id": workspace_id, "decisions": decisions}
    except Exception as e:
        logger.error("[Memory] %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================================
# Business Milestones
# =====================================================================
@router.post("/memory/milestones")
def create_business_milestone(req: MilestoneRequest):
    try:
        milestone_id = BusinessMemoryEngine.save_business_milestone(
            workspace_id=req.workspace_id,
            title=req.title,
            description=req.description,
            milestone_type=req.milestone_type,
            date=req.date,
            metrics=req.metrics,
            owner=req.owner,
        )
        return {"status": "success", "milestone_id": milestone_id}
    except Exception as e:
        logger.error("[Memory] %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/milestones/{workspace_id}")
def get_business_milestones(workspace_id: str, milestone_type: Optional[str] = None, limit: int = 50):
    try:
        milestones = BusinessMemoryEngine.get_business_milestones(workspace_id, milestone_type=milestone_type, limit=limit)
        return {"workspace_id": workspace_id, "milestones": milestones}
    except Exception as e:
        logger.error("[Memory] %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================================
# User Feedback
# =====================================================================
@router.post("/memory/feedback")
def submit_user_feedback(req: UserFeedbackRequest):
    try:
        feedback_id = BusinessMemoryEngine.save_user_feedback(
            workspace_id=req.workspace_id,
            session_id=req.session_id,
            rating=req.rating,
            comment=req.comment,
            category=req.category,
            question=req.question,
            answer=req.answer,
        )
        return {"status": "success", "feedback_id": feedback_id}
    except Exception as e:
        logger.error("[Memory] %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/feedback/{workspace_id}")
def get_user_feedback(workspace_id: str, category: Optional[str] = None, limit: int = 50):
    try:
        feedback = BusinessMemoryEngine.get_user_feedback(workspace_id, category=category, limit=limit)
        return {"workspace_id": workspace_id, "feedback": feedback}
    except Exception as e:
        logger.error("[Memory] %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================================
# Forecast Accuracy
# =====================================================================
@router.post("/memory/forecast-accuracy")
def record_forecast_accuracy(req: ForecastAccuracyRequest):
    try:
        acc_id = BusinessMemoryEngine.save_forecast_accuracy(
            workspace_id=req.workspace_id,
            forecast_id=req.forecast_id,
            metric=req.metric,
            model_type=req.model_type,
            predicted_value=req.predicted_value,
            actual_value=req.actual_value,
            error_pct=req.error_pct,
            period=req.period,
        )
        return {"status": "success", "accuracy_id": acc_id}
    except Exception as e:
        logger.error("[Memory] %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/forecast-accuracy/{workspace_id}")
def get_forecast_accuracy(workspace_id: str, metric: Optional[str] = None, limit: int = 50):
    try:
        accuracy = BusinessMemoryEngine.get_forecast_accuracy(workspace_id, metric=metric, limit=limit)
        return {"workspace_id": workspace_id, "forecast_accuracy": accuracy}
    except Exception as e:
        logger.error("[Memory] %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================================
# AI Context
# =====================================================================
@router.get("/memory/context/{workspace_id}/{session_id}")
def get_ai_context(workspace_id: str, session_id: str):
    try:
        context = BusinessMemoryEngine.get_ai_context(workspace_id, session_id)
        prompt = BusinessMemoryEngine.build_context_prompt(workspace_id, session_id)
        return {
            "workspace_id": workspace_id,
            "session_id": session_id,
            "context": context,
            "prompt": prompt,
        }
    except Exception as e:
        logger.error("[Memory] %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================================
# Role-Based Reports
# =====================================================================
def _get_analytics_for_workspace(workspace_id: str) -> tuple[Optional[AnalyticsResult], Optional[SemanticModel]]:
    try:
        parquet_path = None
        try:
            parquet_path = UniversalAIBrain._resolve_parquet_path(workspace_id=workspace_id, dataset_id=None)
        except Exception:
            pass
        if not parquet_path:
            return None, None

        ws_id = workspace_id or EnterpriseWorkspaceManager.get_active_workspace_id() or "default"
        sm = build_semantic_model(workspace_id=ws_id, force_rebuild=False)
        if isinstance(sm, dict):
            from app.semantic_model.core import SemanticModel
            semantic_model = SemanticModel(
                workspace_id=ws_id,
                domain=sm.get("domain", "Generic Business"),
                dataset_type=sm.get("dataset_type", "Unknown"),
            )
        else:
            semantic_model = sm

        result = UniversalAnalyticsEngine.analyze(semantic_model, parquet_path=parquet_path)
        return result, semantic_model
    except Exception as e:
        logger.error("[Reports] %s", e)
        return None, None


@router.post("/reports/generate")
def generate_role_report(req: ReportRequest):
    try:
        result, semantic_model = _get_analytics_for_workspace(req.workspace_id)
        if not result or not semantic_model:
            raise HTTPException(status_code=404, detail="No analytics data available for this workspace.")

        report = RoleBasedReportEngine.generate_role_specific_report(
            analytics_result=result,
            semantic_model=semantic_model,
            audience=req.audience,
            format=req.format,
        )

        report_id = BusinessMemoryEngine.save_report(
            workspace_id=req.workspace_id,
            report_type="role_based",
            audience=req.audience,
            title=report.get("report_title", f"{req.audience} Report"),
            content=report.get("sections", {}),
            analytics_result=result.to_dict() if hasattr(result, "to_dict") else {},
        )
        report["report_id"] = report_id

        try:
            BusinessMemoryEngine.save_conversation(
                session_id=req.session_id,
                workspace_id=req.workspace_id,
                role="system",
                content=f"Generated {req.audience} report: {report.get('report_title', '')}",
                metadata={"report_id": report_id, "audience": req.audience},
            )
        except Exception:
            pass

        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[Reports] %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/{workspace_id}")
def get_recent_reports(workspace_id: str, audience: Optional[str] = None, limit: int = 10):
    try:
        reports = BusinessMemoryEngine.get_recent_reports(workspace_id, audience=audience, limit=limit)
        return {"workspace_id": workspace_id, "reports": reports}
    except Exception as e:
        logger.error("[Reports] %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/available-audiences")
def get_available_audiences():
    return {
        "audiences": [
            {"id": "CEO", "label": "Chief Executive Officer", "focus": "Strategic growth, market position, long-term health"},
            {"id": "CFO", "label": "Chief Financial Officer", "focus": "Financial performance, forecast accuracy, ROI, budget risks"},
            {"id": "COO", "label": "Chief Operating Officer", "focus": "Operational efficiency, anomalies, process health"},
            {"id": "CMO", "label": "Chief Marketing Officer", "focus": "Customer segments, growth opportunities, market trends"},
            {"id": "SALES DIRECTOR", "label": "Sales Director", "focus": "Revenue performance, pipeline health, top performers, conversion"},
            {"id": "SUPPLY CHAIN HEAD", "label": "Supply Chain Head", "focus": "Efficiency, inventory, anomalies, process health"},
            {"id": "BOARD", "label": "Board Members", "focus": "Comprehensive governance view, risks, opportunities, decisions"},
        ]
    }


# =====================================================================
# Scenario Simulations
# =====================================================================
class ScenarioSimulationRequest(BaseModel):
    workspace_id: str
    simulation_name: str
    scenario_type: str
    base_metric: str
    base_value: float
    adjustment_value: float
    adjustment_unit: str = "pct"
    result_estimate: Optional[float] = None
    description: Optional[str] = None
    assumptions: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


@router.post("/memory/scenarios")
def save_scenario_simulation(req: ScenarioSimulationRequest):
    try:
        sim_id = BusinessMemoryEngine.save_scenario_simulation(
            workspace_id=req.workspace_id,
            simulation_name=req.simulation_name,
            scenario_type=req.scenario_type,
            base_metric=req.base_metric,
            base_value=req.base_value,
            adjustment_value=req.adjustment_value,
            adjustment_unit=req.adjustment_unit,
            result_estimate=req.result_estimate,
            description=req.description,
            assumptions=req.assumptions,
            metadata=req.metadata,
        )
        return {"status": "success", "simulation_id": sim_id}
    except Exception as e:
        logger.error("[Memory] %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/scenarios/{workspace_id}")
def get_scenario_simulations(workspace_id: str, scenario_type: Optional[str] = None, limit: int = 50):
    try:
        sims = BusinessMemoryEngine.get_scenario_simulations(workspace_id, scenario_type=scenario_type, limit=limit)
        return {"workspace_id": workspace_id, "scenarios": sims}
    except Exception as e:
        logger.error("[Memory] %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================================
# Generated SQL History
# =====================================================================
class GeneratedSQLRequest(BaseModel):
    workspace_id: str
    session_id: str
    sql_query: str
    intent: str
    question: str
    tables_used: List[str] = field(default_factory=list)
    columns_used: List[str] = field(default_factory=list)
    rows_returned: int = 0
    confidence: float = 0.0
    status: str = "success"
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@router.post("/memory/generated-sql")
def save_generated_sql(req: GeneratedSQLRequest):
    try:
        sql_id = BusinessMemoryEngine.save_generated_sql(
            workspace_id=req.workspace_id,
            session_id=req.session_id,
            sql_query=req.sql_query,
            intent=req.intent,
            question=req.question,
            tables_used=req.tables_used,
            columns_used=req.columns_used,
            rows_returned=req.rows_returned,
            confidence=req.confidence,
            status=req.status,
            error_message=req.error_message,
            metadata=req.metadata,
        )
        return {"status": "success", "sql_id": sql_id}
    except Exception as e:
        logger.error("[Memory] %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/generated-sql/{workspace_id}")
def get_generated_sql(workspace_id: str, session_id: Optional[str] = None, limit: int = 50):
    try:
        sqls = BusinessMemoryEngine.get_generated_sql(workspace_id, session_id=session_id, limit=limit)
        return {"workspace_id": workspace_id, "generated_sql": sqls}
    except Exception as e:
        logger.error("[Memory] %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================================
# Audit Logs
# =====================================================================
class AuditLogRequest(BaseModel):
    workspace_id: str
    session_id: str
    user_id: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    status: str = "success"
    error_message: Optional[str] = None


@router.post("/memory/audit-logs")
def save_audit_log(req: AuditLogRequest):
    try:
        log_id = BusinessMemoryEngine.save_audit_log(
            workspace_id=req.workspace_id,
            session_id=req.session_id,
            user_id=req.user_id,
            action=req.action,
            resource_type=req.resource_type,
            resource_id=req.resource_id,
            details=req.details,
            ip_address=req.ip_address,
            user_agent=req.user_agent,
            status=req.status,
            error_message=req.error_message,
        )
        return {"status": "success", "log_id": log_id}
    except Exception as e:
        logger.error("[Memory] %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/audit-logs/{workspace_id}")
def get_audit_logs(workspace_id: str, action: Optional[str] = None, user_id: Optional[str] = None, limit: int = 100):
    try:
        logs = BusinessMemoryEngine.get_audit_logs(workspace_id, action=action, user_id=user_id, limit=limit)
        return {"workspace_id": workspace_id, "audit_logs": logs}
    except Exception as e:
        logger.error("[Memory] %s", e)
        raise HTTPException(status_code=500, detail=str(e))
