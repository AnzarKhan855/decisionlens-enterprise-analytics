from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from collections import defaultdict

from app.database.mongodb import (
    conversation_history,
    report_history,
    insight_history,
    forecast_history,
    recommendation_history,
    business_goals,
    executive_decisions,
    forecast_accuracy,
    kpi_history,
    user_feedback,
    business_milestones,
    scenario_simulations,
    generated_sql,
    audit_logs,
)
from app.logging.logger import get_logger

logger = get_logger(__name__)


class BusinessMemoryEngine:
    """
    Long-term Business Memory Engine.

    Every workspace has persistent memory stored in MongoDB.
    Provides context-aware retrieval for AI responses and role-based report generation.

    Stores:
      - Conversation History
      - Reports
      - Insights
      - Forecast History
      - Recommendation History
      - Business Goals
      - Executive Decisions
      - Forecast Accuracy
      - KPI History
      - User Feedback
      - Business Milestones
    """

    @classmethod
    def _now(cls) -> str:
        return datetime.now(timezone.utc).isoformat()

    @classmethod
    def _ts(cls) -> int:
        return int(datetime.now(timezone.utc).timestamp())

    # =====================================================================
    # Conversation History
    # =====================================================================
    @classmethod
    def save_conversation(
        cls,
        session_id: str,
        workspace_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        doc = {
            "session_id": session_id,
            "workspace_id": workspace_id,
            "role": role,
            "content": content,
            "timestamp": cls._now(),
            "ts": cls._ts(),
            "metadata": metadata or {},
        }
        result = conversation_history.insert_one(doc)
        return str(result.inserted_id)

    @classmethod
    def get_conversation_history(
        cls,
        session_id: str,
        workspace_id: str,
        last_n: int = 20,
    ) -> List[Dict[str, Any]]:
        cursor = conversation_history.find(
            {"session_id": session_id, "workspace_id": workspace_id},
            {"_id": 0},
        ).sort("ts", -1).limit(last_n)
        return list(reversed(list(cursor)))

    # =====================================================================
    # Reports
    # =====================================================================
    @classmethod
    def save_report(
        cls,
        workspace_id: str,
        report_type: str,
        audience: str,
        title: str,
        content: Dict[str, Any],
        analytics_result: Optional[Dict[str, Any]] = None,
    ) -> str:
        doc = {
            "workspace_id": workspace_id,
            "report_type": report_type,
            "audience": audience,
            "title": title,
            "content": content,
            "analytics_result": analytics_result or {},
            "timestamp": cls._now(),
            "ts": cls._ts(),
            "generated_by": "business_memory_engine",
        }
        result = report_history.insert_one(doc)
        return str(result.inserted_id)

    @classmethod
    def get_recent_reports(
        cls,
        workspace_id: str,
        audience: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {"workspace_id": workspace_id}
        if audience:
            query["audience"] = audience
        cursor = report_history.find(query, {"_id": 0}).sort("ts", -1).limit(limit)
        return list(cursor)

    # =====================================================================
    # Insights
    # =====================================================================
    @classmethod
    def save_insight(
        cls,
        workspace_id: str,
        insight_type: str,
        title: str,
        description: str,
        severity: str = "MEDIUM",
        metric: Optional[str] = None,
        value: Optional[float] = None,
    ) -> str:
        doc = {
            "workspace_id": workspace_id,
            "insight_type": insight_type,
            "title": title,
            "description": description,
            "severity": severity,
            "metric": metric,
            "value": value,
            "timestamp": cls._now(),
            "ts": cls._ts(),
        }
        result = insight_history.insert_one(doc)
        return str(result.inserted_id)

    @classmethod
    def get_insights(
        cls,
        workspace_id: str,
        insight_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {"workspace_id": workspace_id}
        if insight_type:
            query["insight_type"] = insight_type
        cursor = insight_history.find(query, {"_id": 0}).sort("ts", -1).limit(limit)
        return list(cursor)

    # =====================================================================
    # Forecast History
    # =====================================================================
    @classmethod
    def save_forecast(
        cls,
        workspace_id: str,
        model_type: str,
        metric: str,
        predictions: List[Dict[str, Any]],
        actuals: Optional[List[Dict[str, Any]]] = None,
        confidence: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        doc = {
            "workspace_id": workspace_id,
            "model_type": model_type,
            "metric": metric,
            "predictions": predictions,
            "actuals": actuals or [],
            "confidence": confidence,
            "metadata": metadata or {},
            "timestamp": cls._now(),
            "ts": cls._ts(),
        }
        result = forecast_history.insert_one(doc)
        return str(result.inserted_id)

    @classmethod
    def get_forecast_history(
        cls,
        workspace_id: str,
        metric: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {"workspace_id": workspace_id}
        if metric:
            query["metric"] = metric
        cursor = forecast_history.find(query, {"_id": 0}).sort("ts", -1).limit(limit)
        return list(cursor)

    # =====================================================================
    # Recommendation History
    # =====================================================================
    @classmethod
    def save_recommendation(
        cls,
        workspace_id: str,
        title: str,
        category: str,
        priority: str,
        action: str,
        expected_roi: str = "",
        financial_impact: str = "",
        confidence: float = 0.0,
        status: str = "pending",
        outcome: Optional[str] = None,
        evidence: Optional[str] = None,
    ) -> str:
        doc = {
            "workspace_id": workspace_id,
            "title": title,
            "category": category,
            "priority": priority,
            "action": action,
            "expected_roi": expected_roi,
            "financial_impact": financial_impact,
            "confidence": confidence,
            "status": status,
            "outcome": outcome,
            "evidence": evidence,
            "timestamp": cls._now(),
            "ts": cls._ts(),
        }
        result = recommendation_history.insert_one(doc)
        return str(result.inserted_id)

    @classmethod
    def get_recommendation_history(
        cls,
        workspace_id: str,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {"workspace_id": workspace_id}
        if status:
            query["status"] = status
        cursor = recommendation_history.find(query, {"_id": 0}).sort("ts", -1).limit(limit)
        return list(cursor)

    @classmethod
    def update_recommendation_status(
        cls,
        recommendation_id: str,
        status: str,
        outcome: Optional[str] = None,
    ) -> bool:
        update: Dict[str, Any] = {"status": status}
        if outcome:
            update["outcome"] = outcome
        result = recommendation_history.update_one(
            {"_id": recommendation_id},
            {"$set": update},
        )
        return result.modified_count > 0

    # =====================================================================
    # Business Goals
    # =====================================================================
    @classmethod
    def save_business_goal(
        cls,
        workspace_id: str,
        title: str,
        description: str,
        target_metric: Optional[str] = None,
        target_value: Optional[float] = None,
        current_value: Optional[float] = None,
        deadline: Optional[str] = None,
        owner: str = "Unassigned",
        priority: str = "MEDIUM",
        status: str = "active",
    ) -> str:
        doc = {
            "workspace_id": workspace_id,
            "title": title,
            "description": description,
            "target_metric": target_metric,
            "target_value": target_value,
            "current_value": current_value,
            "deadline": deadline,
            "owner": owner,
            "priority": priority,
            "status": status,
            "timestamp": cls._now(),
            "ts": cls._ts(),
        }
        result = business_goals.insert_one(doc)
        return str(result.inserted_id)

    @classmethod
    def get_business_goals(
        cls,
        workspace_id: str,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {"workspace_id": workspace_id}
        if status:
            query["status"] = status
        cursor = business_goals.find(query, {"_id": 0}).sort("ts", -1)
        return list(cursor)

    @classmethod
    def update_business_goal_progress(
        cls,
        goal_id: str,
        current_value: float,
        status: str = "active",
    ) -> bool:
        result = business_goals.update_one(
            {"_id": goal_id},
            {"$set": {"current_value": current_value, "status": status, "updated_at": cls._now()}},
        )
        return result.modified_count > 0

    # =====================================================================
    # Executive Decisions
    # =====================================================================
    @classmethod
    def save_executive_decision(
        cls,
        workspace_id: str,
        title: str,
        description: str,
        decision_maker: str,
        rationale: str,
        expected_impact: str = "",
        metrics_affected: Optional[List[str]] = None,
        deadline: Optional[str] = None,
        status: str = "approved",
    ) -> str:
        doc = {
            "workspace_id": workspace_id,
            "title": title,
            "description": description,
            "decision_maker": decision_maker,
            "rationale": rationale,
            "expected_impact": expected_impact,
            "metrics_affected": metrics_affected or [],
            "deadline": deadline,
            "status": status,
            "timestamp": cls._now(),
            "ts": cls._ts(),
        }
        result = executive_decisions.insert_one(doc)
        return str(result.inserted_id)

    @classmethod
    def get_executive_decisions(
        cls,
        workspace_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        cursor = executive_decisions.find(
            {"workspace_id": workspace_id},
            {"_id": 0},
        ).sort("ts", -1).limit(limit)
        return list(cursor)

    # =====================================================================
    # Forecast Accuracy
    # =====================================================================
    @classmethod
    def save_forecast_accuracy(
        cls,
        workspace_id: str,
        forecast_id: str,
        metric: str,
        model_type: str,
        predicted_value: float,
        actual_value: float,
        error_pct: float,
        mae: Optional[float] = None,
        rmse: Optional[float] = None,
        direction_correct: bool = False,
        period: Optional[str] = None,
    ) -> str:
        doc = {
            "workspace_id": workspace_id,
            "forecast_id": forecast_id,
            "metric": metric,
            "model_type": model_type,
            "predicted_value": predicted_value,
            "actual_value": actual_value,
            "error_pct": round(error_pct, 4),
            "mae": mae,
            "rmse": rmse,
            "direction_correct": direction_correct,
            "period": period,
            "timestamp": cls._now(),
            "ts": cls._ts(),
        }
        result = forecast_accuracy.insert_one(doc)
        return str(result.inserted_id)

    @classmethod
    def get_forecast_accuracy(
        cls,
        workspace_id: str,
        metric: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {"workspace_id": workspace_id}
        if metric:
            query["metric"] = metric
        cursor = forecast_accuracy.find(query, {"_id": 0}).sort("ts", -1).limit(limit)
        return list(cursor)

    # =====================================================================
    # KPI History
    # =====================================================================
    @classmethod
    def save_kpi_snapshot(
        cls,
        workspace_id: str,
        kpis: List[Dict[str, Any]],
        dataset_id: Optional[str] = None,
    ) -> str:
        doc = {
            "workspace_id": workspace_id,
            "dataset_id": dataset_id,
            "kpis": kpis,
            "timestamp": cls._now(),
            "ts": cls._ts(),
        }
        result = kpi_history.insert_one(doc)
        return str(result.inserted_id)

    @classmethod
    def get_kpi_history(
        cls,
        workspace_id: str,
        kpi_name: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {"workspace_id": workspace_id}
        if kpi_name:
            query["kpis.name"] = kpi_name
        cursor = kpi_history.find(query, {"_id": 0}).sort("ts", -1).limit(limit)
        return list(cursor)

    # =====================================================================
    # User Feedback
    # =====================================================================
    @classmethod
    def save_user_feedback(
        cls,
        workspace_id: str,
        session_id: str,
        rating: int,
        comment: str = "",
        category: str = "general",
        question: Optional[str] = None,
        answer: Optional[str] = None,
    ) -> str:
        doc = {
            "workspace_id": workspace_id,
            "session_id": session_id,
            "rating": rating,
            "comment": comment,
            "category": category,
            "question": question,
            "answer": answer,
            "timestamp": cls._now(),
            "ts": cls._ts(),
        }
        result = user_feedback.insert_one(doc)
        return str(result.inserted_id)

    @classmethod
    def get_user_feedback(
        cls,
        workspace_id: str,
        category: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {"workspace_id": workspace_id}
        if category:
            query["category"] = category
        cursor = user_feedback.find(query, {"_id": 0}).sort("ts", -1).limit(limit)
        return list(cursor)

    # =====================================================================
    # Business Milestones
    # =====================================================================
    @classmethod
    def save_business_milestone(
        cls,
        workspace_id: str,
        title: str,
        description: str,
        milestone_type: str = "operational",
        date: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
        owner: str = "Unassigned",
    ) -> str:
        doc = {
            "workspace_id": workspace_id,
            "title": title,
            "description": description,
            "milestone_type": milestone_type,
            "date": date or cls._now(),
            "metrics": metrics or {},
            "owner": owner,
            "timestamp": cls._now(),
            "ts": cls._ts(),
        }
        result = business_milestones.insert_one(doc)
        return str(result.inserted_id)

    @classmethod
    def get_business_milestones(
        cls,
        workspace_id: str,
        milestone_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {"workspace_id": workspace_id}
        if milestone_type:
            query["milestone_type"] = milestone_type
        cursor = business_milestones.find(query, {"_id": 0}).sort("ts", -1).limit(limit)
        return list(cursor)

    # =====================================================================
    # Context Retrieval for AI Responses
    # =====================================================================
    @classmethod
    def get_ai_context(cls, workspace_id: str, session_id: str) -> Dict[str, Any]:
        recent_conversations = cls.get_conversation_history(session_id, workspace_id, last_n=10)
        recent_reports = cls.get_recent_reports(workspace_id, limit=5)
        recent_insights = cls.get_insights(workspace_id, limit=10)
        recent_forecasts = cls.get_forecast_history(workspace_id, limit=5)
        recent_recommendations = cls.get_recommendation_history(workspace_id, limit=10)
        active_goals = cls.get_business_goals(workspace_id, status="active")
        recent_decisions = cls.get_executive_decisions(workspace_id, limit=10)
        recent_kpis = cls.get_kpi_history(workspace_id, limit=5)
        recent_milestones = cls.get_business_milestones(workspace_id, limit=5)

        return {
            "current_dataset": {"workspace_id": workspace_id},
            "previous_conversations": recent_conversations,
            "previous_reports": recent_reports,
            "previous_insights": recent_insights,
            "previous_forecasts": recent_forecasts,
            "previous_recommendations": recent_recommendations,
            "business_goals": active_goals,
            "previous_decisions": recent_decisions,
            "previous_kpis": recent_kpis,
            "business_milestones": recent_milestones,
            "context_generated_at": cls._now(),
        }

    @classmethod
    def build_context_prompt(cls, workspace_id: str, session_id: str) -> str:
        context = cls.get_ai_context(workspace_id, session_id)
        parts: List[str] = ["BUSINESS MEMORY CONTEXT\n"]

        if context["previous_conversations"]:
            parts.append("RECENT CONVERSATIONS:")
            for turn in context["previous_conversations"][-5:]:
                parts.append(f"- [{turn['role']}] {turn['content'][:200]}")
            parts.append("")

        if context["previous_reports"]:
            parts.append("RECENT REPORTS:")
            for rpt in context["previous_reports"][:3]:
                parts.append(f"- [{rpt.get('audience', 'N/A')}] {rpt.get('title', 'Untitled')} ({rpt.get('timestamp', '')[:10]})")
            parts.append("")

        if context["previous_insights"]:
            parts.append("RECENT INSIGHTS:")
            for ins in context["previous_insights"][:5]:
                parts.append(f"- [{ins.get('severity', 'N/A')}] {ins.get('title', '')}: {ins.get('description', '')[:150]}")
            parts.append("")

        if context["previous_forecasts"]:
            parts.append("RECENT FORECASTS:")
            for f in context["previous_forecasts"][:3]:
                parts.append(f"- [{f.get('model_type', 'N/A')}] {f.get('metric', '')}: confidence={f.get('confidence', 0)}")
            parts.append("")

        if context["previous_recommendations"]:
            parts.append("RECENT RECOMMENDATIONS:")
            for rec in context["previous_recommendations"][:5]:
                parts.append(f"- [{rec.get('status', 'pending')}] {rec.get('title', '')}: {rec.get('action', '')[:100]}")
            parts.append("")

        if context["business_goals"]:
            parts.append("ACTIVE BUSINESS GOALS:")
            for g in context["business_goals"][:5]:
                parts.append(f"- {g.get('title', '')}: target={g.get('target_value', 'N/A')}, current={g.get('current_value', 'N/A')}")
            parts.append("")

        if context["previous_decisions"]:
            parts.append("PREVIOUS EXECUTIVE DECISIONS:")
            for d in context["previous_decisions"][:5]:
                parts.append(f"- [{d.get('status', 'N/A')}] {d.get('title', '')} by {d.get('decision_maker', 'Unknown')}")
            parts.append("")

        if context["previous_kpis"]:
            parts.append("PREVIOUS KPI SNAPSHOTS:")
            for k in context["previous_kpis"][:3]:
                ts = k.get("timestamp", "")[:10]
                kpi_names = [kpi.get("name", "") for kpi in k.get("kpis", [])[:3]]
                parts.append(f"- {ts}: {', '.join(kpi_names)}")
            parts.append("")

        if context["business_milestones"]:
            parts.append("BUSINESS MILESTONES:")
            for m in context["business_milestones"][:3]:
                parts.append(f"- {m.get('title', '')} ({m.get('date', '')[:10]}): {m.get('description', '')[:100]}")
            parts.append("")

        parts.append("END OF BUSINESS MEMORY CONTEXT\n")
        return "\n".join(parts)

    # =====================================================================
    # Scenario Simulations
    # =====================================================================
    @classmethod
    def save_scenario_simulation(
        cls,
        workspace_id: str,
        simulation_name: str,
        scenario_type: str,
        base_metric: str,
        base_value: float,
        adjustment_value: float,
        adjustment_unit: str = "pct",
        result_estimate: Optional[float] = None,
        description: Optional[str] = None,
        assumptions: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        doc = {
            "workspace_id": workspace_id,
            "simulation_name": simulation_name,
            "scenario_type": scenario_type,
            "base_metric": base_metric,
            "base_value": base_value,
            "adjustment_value": adjustment_value,
            "adjustment_unit": adjustment_unit,
            "result_estimate": result_estimate,
            "description": description,
            "assumptions": assumptions or [],
            "metadata": metadata or {},
            "timestamp": cls._now(),
            "ts": cls._ts(),
        }
        result = scenario_simulations.insert_one(doc)
        return str(result.inserted_id)

    @classmethod
    def get_scenario_simulations(
        cls,
        workspace_id: str,
        scenario_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {"workspace_id": workspace_id}
        if scenario_type:
            query["scenario_type"] = scenario_type
        cursor = scenario_simulations.find(query, {"_id": 0}).sort("ts", -1).limit(limit)
        return list(cursor)

    # =====================================================================
    # Generated SQL History
    # =====================================================================
    @classmethod
    def save_generated_sql(
        cls,
        workspace_id: str,
        session_id: str,
        sql_query: str,
        intent: str,
        question: str,
        tables_used: List[str],
        columns_used: List[str],
        rows_returned: int = 0,
        confidence: float = 0.0,
        status: str = "success",
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        doc = {
            "workspace_id": workspace_id,
            "session_id": session_id,
            "sql_query": sql_query,
            "intent": intent,
            "question": question,
            "tables_used": tables_used,
            "columns_used": columns_used,
            "rows_returned": rows_returned,
            "confidence": confidence,
            "status": status,
            "error_message": error_message,
            "metadata": metadata or {},
            "timestamp": cls._now(),
            "ts": cls._ts(),
        }
        result = generated_sql.insert_one(doc)
        return str(result.inserted_id)

    @classmethod
    def get_generated_sql(
        cls,
        workspace_id: str,
        session_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {"workspace_id": workspace_id}
        if session_id:
            query["session_id"] = session_id
        cursor = generated_sql.find(query, {"_id": 0}).sort("ts", -1).limit(limit)
        return list(cursor)

    # =====================================================================
    # Audit Logs
    # =====================================================================
    @classmethod
    def save_audit_log(
        cls,
        workspace_id: str,
        session_id: str,
        action: str,
        resource_type: str,
        user_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        status: str = "success",
        error_message: Optional[str] = None,
    ) -> str:
        doc = {
            "workspace_id": workspace_id,
            "session_id": session_id,
            "user_id": user_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details or {},
            "ip_address": ip_address,
            "user_agent": user_agent,
            "status": status,
            "error_message": error_message,
            "timestamp": cls._now(),
            "ts": cls._ts(),
        }
        result = audit_logs.insert_one(doc)
        return str(result.inserted_id)

    @classmethod
    def get_audit_logs(
        cls,
        workspace_id: str,
        action: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {"workspace_id": workspace_id}
        if action:
            query["action"] = action
        if user_id:
            query["user_id"] = user_id
        cursor = audit_logs.find(query, {"_id": 0}).sort("ts", -1).limit(limit)
        return list(cursor)

    @classmethod
    def extract_entities_and_terms(cls, text: str, profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        measures = (profile or {}).get("column_categories", {}).get("measures", [])
        dimensions = (profile or {}).get("column_categories", {}).get("dimensions", [])
        temporal = (profile or {}).get("column_categories", {}).get("temporal", [])
        text_lower = text.lower()
        entities = []
        business_terms = []
        important_metrics = []
        important_dimensions = []
        for m in measures:
            if m.lower() in text_lower:
                important_metrics.append(m)
                entities.append(m)
        for d in dimensions:
            if d.lower() in text_lower:
                important_dimensions.append(d)
                entities.append(d)
        for t in temporal:
            if t.lower() in text_lower:
                entities.append(t)
                business_terms.append(t)
        return {
            "entities": list(set(entities)),
            "business_terms": list(set(business_terms)),
            "important_metrics": list(set(important_metrics)),
            "important_dimensions": list(set(important_dimensions)),
        }
