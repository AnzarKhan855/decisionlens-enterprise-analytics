from __future__ import annotations

from typing import Any, Dict, List, Optional


class BusinessContextBuilder:
    """
    Business Context Builder for the Enterprise Decision Engine.

    Assembles a comprehensive business context from all available
    data sources before AI reasoning or LLM generation.

    Context includes:
      - Dataset summary
      - Business domain
      - Important KPIs
      - Important metrics
      - Important dimensions
      - Relationships
      - Top risks
      - Top opportunities
      - Forecast status
      - Recommendations
      - Executive summary
      - Business findings
      - Recent conversation
      - Previous decisions
    """

    @classmethod
    def build(
        cls,
        workspace_id: str,
        session_id: str,
        analytics_dict: Optional[Dict[str, Any]] = None,
        semantic_model: Optional[Any] = None,
        question: str = "",
    ) -> Dict[str, Any]:
        context: Dict[str, Any] = {
            "workspace_id": workspace_id,
            "session_id": session_id,
            "question": question,
            "dataset_summary": {},
            "domain": "Generic Business",
            "important_kpis": [],
            "important_metrics": [],
            "important_dimensions": [],
            "relationships": [],
            "top_risks": [],
            "top_opportunities": [],
            "forecast": {},
            "recommendations": [],
            "executive_summary": "",
            "business_findings": [],
            "recent_conversation": [],
            "previous_decisions": [],
            "active_goals": [],
            "health_score": {},
            "confidence_score": 0.0,
            "prediction_feasible": False,
            "prediction_limitation": None,
            "anomalies_detected": 0,
            "drivers_identified": 0,
            "kpi_count": 0,
            "recommendation_count": 0,
            "forecast_available": False,
        }

        try:
            from app.memory.business_memory_engine import BusinessMemoryEngine
            ai_context = BusinessMemoryEngine.get_ai_context(workspace_id, session_id)

            context["recent_conversation"] = ai_context.get("previous_conversations", [])[-5:]
            context["previous_decisions"] = ai_context.get("previous_decisions", [])[:5]
            context["active_goals"] = ai_context.get("business_goals", [])[:5]
            context["previous_recommendations"] = ai_context.get("previous_recommendations", [])[:5]
            context["previous_forecasts"] = ai_context.get("previous_forecasts", [])[:3]
            context["previous_reports"] = ai_context.get("previous_reports", [])[:3]
            context["previous_kpis"] = ai_context.get("previous_kpis", [])[:3]
        except Exception:
            pass

        if analytics_dict:
            context["domain"] = analytics_dict.get("domain", context["domain"])
            context["dataset_summary"] = cls._build_dataset_summary(analytics_dict)
            context["important_kpis"] = cls._extract_kpis(analytics_dict.get("kpis", []))
            context["important_metrics"] = analytics_dict.get("metrics", [])[:10]
            context["important_dimensions"] = analytics_dict.get("dimensions", [])[:10]
            context["top_risks"] = cls._extract_risks(analytics_dict.get("risks", []))
            context["top_opportunities"] = cls._extract_opportunities(analytics_dict.get("opportunities", []))
            context["forecast"] = cls._build_forecast_summary(analytics_dict.get("predictions", []))
            context["recommendations"] = cls._extract_recommendations(analytics_dict.get("recommendations", []))
            context["executive_summary"] = analytics_dict.get("executive_summary", "")
            context["business_findings"] = cls._build_findings(
                analytics_dict.get("critical_findings", []),
                analytics_dict.get("positive_findings", []),
                analytics_dict.get("negative_findings", []),
            )
            context["health_score"] = cls._extract_health_score(analytics_dict.get("health_score"))
            context["confidence_score"] = analytics_dict.get("confidence_score", 0.0)
            context["prediction_feasible"] = analytics_dict.get("prediction_feasible", False)
            context["prediction_limitation"] = analytics_dict.get("prediction_limitation")
            context["anomalies_detected"] = len(analytics_dict.get("anomalies", [])) + len(analytics_dict.get("outliers", []))
            context["drivers_identified"] = len(analytics_dict.get("drivers", [])) + len(analytics_dict.get("root_causes", []))
            context["kpi_count"] = len(analytics_dict.get("kpis", []))
            context["recommendation_count"] = len(analytics_dict.get("recommendations", []))
            context["forecast_available"] = any(
                p.get("feasible", True) for p in cls._normalize_predictions(analytics_dict.get("predictions", []))
            )
            context["relationships"] = analytics_dict.get("relationships", [])

        if semantic_model:
            try:
                sm_dict = semantic_model.to_dict() if hasattr(semantic_model, "to_dict") else {}
                if not sm_dict and hasattr(semantic_model, "__dict__"):
                    sm_dict = {k: v for k, v in semantic_model.__dict__.items() if not k.startswith("_")}
                context["domain"] = sm_dict.get("domain", context["domain"])
                context["dataset_type"] = sm_dict.get("dataset_type", analytics_dict.get("dataset_type", "Unknown") if analytics_dict else "Unknown")
                context["relationships"] = sm_dict.get("relationships", context["relationships"])
            except Exception:
                pass

        if not context["executive_summary"] and analytics_dict:
            context["executive_summary"] = cls._build_default_executive_summary(analytics_dict)

        return context

    @classmethod
    def build_context_prompt(cls, context: Dict[str, Any]) -> str:
        parts: List[str] = ["BUSINESS CONTEXT FOR DECISION INTELLIGENCE\n"]

        if context.get("domain"):
            parts.append(f"DOMAIN: {context['domain']}")
        if context.get("dataset_summary"):
            ds = context["dataset_summary"]
            parts.append(f"DATASET: {ds.get('dataset_name', 'Unknown')} | Records: {ds.get('volume', 0):,} | Health: {ds.get('health_score', 0):.0f}/100")
        if context.get("important_kpis"):
            parts.append("TOP KPIs:")
            for kpi in context["important_kpis"][:5]:
                parts.append(f"  - {kpi.get('name', '')}: {kpi.get('formatted_value', '')}")
        if context.get("important_metrics"):
            parts.append(f"METRICS: {', '.join(context['important_metrics'][:5])}")
        if context.get("important_dimensions"):
            parts.append(f"DIMENSIONS: {', '.join(context['important_dimensions'][:5])}")
        if context.get("top_risks"):
            parts.append("TOP RISKS:")
            for r in context["top_risks"][:3]:
                parts.append(f"  - [{r.get('severity', '')}] {r.get('title', '')}")
        if context.get("top_opportunities"):
            parts.append("TOP OPPORTUNITIES:")
            for o in context["top_opportunities"][:3]:
                parts.append(f"  - [{o.get('priority', '')}] {o.get('title', '')}")
        if context.get("forecast_available"):
            parts.append(f"FORECAST: Available | Feasible: {context.get('prediction_feasible')} | Limitation: {context.get('prediction_limitation', 'None')}")
        if context.get("recommendations"):
            parts.append("RECOMMENDATIONS:")
            for rec in context["recommendations"][:3]:
                parts.append(f"  - [{rec.get('priority', '')}] {rec.get('action', rec.get('title', ''))}")
        if context.get("business_findings"):
            parts.append("KEY FINDINGS:")
            for finding in context["business_findings"][:5]:
                parts.append(f"  - {finding}")
        if context.get("recent_conversation"):
            parts.append("RECENT CONVERSATION:")
            for turn in context["recent_conversation"][-3:]:
                role = turn.get("role", "user")
                content = turn.get("content", "")[:200]
                parts.append(f"  [{role}] {content}")
        if context.get("previous_decisions"):
            parts.append("PREVIOUS EXECUTIVE DECISIONS:")
            for d in context["previous_decisions"][:3]:
                parts.append(f"  - [{d.get('status', '')}] {d.get('title', '')} by {d.get('decision_maker', 'Unknown')}")
        if context.get("active_goals"):
            parts.append("ACTIVE BUSINESS GOALS:")
            for g in context["active_goals"][:3]:
                parts.append(f"  - {g.get('title', '')}: target={g.get('target_value', 'N/A')}, current={g.get('current_value', 'N/A')}")

        parts.append("\nEND OF BUSINESS CONTEXT\n")
        return "\n".join(parts)

    @classmethod
    def _build_dataset_summary(cls, analytics_dict: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "dataset_name": analytics_dict.get("dataset_type", "Unknown Dataset"),
            "volume": analytics_dict.get("volume", 0),
            "health_score": analytics_dict.get("health_score", {}).get("overall_score", 0.0) if isinstance(analytics_dict.get("health_score"), dict) else 0.0,
            "domain": analytics_dict.get("domain", "Generic Business"),
            "kpi_count": len(analytics_dict.get("kpis", [])),
            "anomaly_count": len(analytics_dict.get("anomalies", [])) + len(analytics_dict.get("outliers", [])),
            "prediction_count": len(analytics_dict.get("predictions", [])),
            "recommendation_count": len(analytics_dict.get("recommendations", [])),
        }

    @classmethod
    def _extract_kpis(cls, kpis: List[Any]) -> List[Dict[str, Any]]:
        result = []
        for kpi in kpis[:8]:
            if isinstance(kpi, dict):
                result.append({
                    "name": kpi.get("name", ""),
                    "formatted_value": kpi.get("formatted_value", ""),
                    "value": kpi.get("value", 0),
                    "confidence": kpi.get("confidence", 0.0),
                    "metric_type": kpi.get("metric_type", ""),
                })
            elif hasattr(kpi, "__dict__"):
                result.append({
                    "name": getattr(kpi, "name", ""),
                    "formatted_value": getattr(kpi, "formatted_value", ""),
                    "value": getattr(kpi, "value", 0),
                    "confidence": getattr(kpi, "confidence", 0.0),
                    "metric_type": getattr(kpi, "metric_type", ""),
                })
        return result

    @classmethod
    def _extract_risks(cls, risks: List[Any]) -> List[Dict[str, Any]]:
        result = []
        for r in risks[:5]:
            if isinstance(r, dict):
                result.append({
                    "id": r.get("id", ""),
                    "title": r.get("title", ""),
                    "severity": r.get("severity", ""),
                    "category": r.get("category", ""),
                    "description": r.get("description", ""),
                    "impact": r.get("impact", ""),
                })
            elif hasattr(r, "__dict__"):
                result.append({
                    "id": getattr(r, "id", ""),
                    "title": getattr(r, "title", ""),
                    "severity": getattr(r, "severity", ""),
                    "category": getattr(r, "category", ""),
                    "description": getattr(r, "description", ""),
                    "impact": getattr(r, "impact", ""),
                })
        return result

    @classmethod
    def _extract_opportunities(cls, opportunities: List[Any]) -> List[Dict[str, Any]]:
        result = []
        for o in opportunities[:5]:
            if isinstance(o, dict):
                result.append({
                    "id": o.get("id", ""),
                    "title": o.get("title", ""),
                    "priority": o.get("priority", ""),
                    "description": o.get("description", ""),
                    "impact": o.get("impact", ""),
                    "action": o.get("action", ""),
                })
            elif hasattr(o, "__dict__"):
                result.append({
                    "id": getattr(o, "id", ""),
                    "title": getattr(o, "title", ""),
                    "priority": getattr(o, "priority", ""),
                    "description": getattr(o, "description", ""),
                    "impact": getattr(o, "impact", ""),
                    "action": getattr(o, "action", ""),
                })
        return result

    @classmethod
    def _build_forecast_summary(cls, predictions: List[Any]) -> Dict[str, Any]:
        norm = cls._normalize_predictions(predictions)
        feasible = [p for p in norm if p.get("feasible", True)]
        return {
            "available": bool(feasible),
            "count": len(feasible),
            "prediction": feasible[0].get("prediction", "") if feasible else "",
            "confidence": feasible[0].get("confidence", 0.0) if feasible else 0.0,
            "limitation": next((p.get("limitation") for p in norm if p.get("limitation")), None),
        }

    @classmethod
    def _extract_recommendations(cls, recommendations: List[Any]) -> List[Dict[str, Any]]:
        result = []
        for r in recommendations[:5]:
            if isinstance(r, dict):
                result.append({
                    "id": r.get("id", ""),
                    "title": r.get("title", ""),
                    "priority": r.get("priority", ""),
                    "action": r.get("action", ""),
                    "expected_roi": r.get("expected_roi", ""),
                    "financial_impact": r.get("financial_impact", ""),
                    "confidence": r.get("confidence", 0.0),
                })
            elif hasattr(r, "__dict__"):
                result.append({
                    "id": getattr(r, "id", ""),
                    "title": getattr(r, "title", ""),
                    "priority": getattr(r, "priority", ""),
                    "action": getattr(r, "action", ""),
                    "expected_roi": getattr(r, "expected_roi", ""),
                    "financial_impact": getattr(r, "financial_impact", ""),
                    "confidence": getattr(r, "confidence", 0.0),
                })
        return result

    @classmethod
    def _extract_health_score(cls, health_score: Any) -> Dict[str, Any]:
        if isinstance(health_score, dict):
            return {
                "overall_score": health_score.get("overall_score", 0.0),
                "grade": health_score.get("grade", "N/A"),
                "status": health_score.get("status", "Unknown"),
            }
        elif hasattr(health_score, "__dict__"):
            return {
                "overall_score": getattr(health_score, "overall_score", 0.0),
                "grade": getattr(health_score, "grade", "N/A"),
                "status": getattr(health_score, "status", "Unknown"),
            }
        return {"overall_score": 0.0, "grade": "N/A", "status": "Unknown"}

    @classmethod
    def _build_findings(
        cls,
        critical: List[str],
        positive: List[str],
        negative: List[str],
    ) -> List[str]:
        findings: List[str] = []
        for f in critical[:3]:
            findings.append(f)
        for f in negative[:2]:
            findings.append(f)
        for f in positive[:2]:
            findings.append(f)
        return findings

    @classmethod
    def _build_default_executive_summary(cls, analytics_dict: Dict[str, Any]) -> str:
        domain = analytics_dict.get("domain", "Generic Business")
        volume = analytics_dict.get("volume", 0)
        kpis = analytics_dict.get("kpis", [])
        anomalies = analytics_dict.get("anomalies", [])
        recommendations = analytics_dict.get("recommendations", [])
        parts = [
            f"{domain} analysis of {volume:,} records.",
            f"{len(kpis)} KPIs computed.",
        ]
        if anomalies:
            parts.append(f"{len(anomalies)} anomalies detected.")
        if recommendations:
            parts.append(f"{len(recommendations)} recommendations generated.")
        return " ".join(parts)

    @classmethod
    def _normalize_predictions(cls, predictions: List[Any]) -> List[Dict[str, Any]]:
        norm = []
        for p in predictions:
            if isinstance(p, dict):
                norm.append(p)
            elif hasattr(p, "to_dict"):
                norm.append(p.to_dict())
            elif hasattr(p, "__dict__"):
                norm.append({k: v for k, v in p.__dict__.items()})
            else:
                norm.append({"prediction": str(p)})
        return norm
