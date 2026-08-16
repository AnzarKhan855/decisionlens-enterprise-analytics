from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.schemas.analytics import AnalyticsResult, KPIMetric, RiskItem, OpportunityItem, Recommendation, HealthScore
from app.semantic_model.core import SemanticModel
from app.reports.executive_report_engine import UniversalExecutiveReportEngine
from app.logging.logger import get_logger

logger = get_logger(__name__)


def _ensure_list(value: Any) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    if value is None:
        return []
    return [value]


class RoleBasedReportEngine:
    """
    Generates professional role-specific reports from the SAME AnalyticsResult.

    Each report uses identical underlying data but applies a different business lens:
      - CEO: Strategic growth, market position, long-term health
      - CFO: Financial performance, forecast accuracy, ROI, budget risks
      - COO: Operational efficiency, anomalies, process health
      - CMO: Customer segments, growth opportunities, market trends
      - Sales Director: Revenue performance, pipeline health, top performers, conversion
      - Supply Chain Head: Operational efficiency, inventory, anomalies, process health
      - Board: Comprehensive governance view, risks, opportunities, decisions
    """

    @classmethod
    def generate_report(
        cls,
        analytics_result: AnalyticsResult,
        semantic_model: SemanticModel,
        audience: str = "CEO",
        predictions: Optional[List[Any]] = None,
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        audience = audience.upper()
        base_report = UniversalExecutiveReportEngine.generate_report(
            analytics_result=analytics_result,
            semantic_model=semantic_model,
            prediction_result=predictions,
        )

        sections = base_report.get("sections", {})
        tailored: Dict[str, Any] = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "audience": audience,
            "domain": analytics_result.domain or semantic_model.domain or "Generic Business",
            "dataset_type": analytics_result.dataset_type or "Unknown Dataset",
            "health_score": analytics_result.health_score.overall_score if isinstance(analytics_result.health_score, HealthScore) else 0,
            "health_status": analytics_result.health_score.status if isinstance(analytics_result.health_score, HealthScore) else "Unknown",
        }

        if audience == "CEO":
            tailored["report_title"] = f"CEO Strategic Briefing - {tailored['domain']}"
            tailored["sections"] = cls._build_ceo_report(sections, analytics_result, extra_context)
        elif audience == "CFO":
            tailored["report_title"] = f"CFO Financial Review - {tailored['domain']}"
            tailored["sections"] = cls._build_cfo_report(sections, analytics_result, extra_context)
        elif audience == "COO":
            tailored["report_title"] = f"COO Operations Review - {tailored['domain']}"
            tailored["sections"] = cls._build_coo_report(sections, analytics_result, extra_context)
        elif audience == "CMO":
            tailored["report_title"] = f"CMO Marketing & Growth Review - {tailored['domain']}"
            tailored["sections"] = cls._build_cmo_report(sections, analytics_result, extra_context)
        elif audience == "SALES DIRECTOR":
            tailored["report_title"] = f"Sales Director Performance Report - {tailored['domain']}"
            tailored["sections"] = cls._build_sales_director_report(sections, analytics_result, extra_context)
        elif audience == "SUPPLY CHAIN HEAD":
            tailored["report_title"] = f"Supply Chain Operations Report - {tailored['domain']}"
            tailored["sections"] = cls._build_supply_chain_report(sections, analytics_result, extra_context)
        elif audience == "BOARD":
            tailored["report_title"] = f"Board Governance Report - {tailored['domain']}"
            tailored["sections"] = cls._build_board_report(sections, analytics_result, extra_context)
        else:
            tailored["report_title"] = f"Executive Report - {tailored['domain']}"
            tailored["sections"] = sections

        return tailored

    # =====================================================================
    # CEO: Strategic growth, market position, long-term health
    # =====================================================================
    @classmethod
    def _build_ceo_report(cls, sections: Dict[str, Any], result: AnalyticsResult, ctx: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        exec_sum = sections.get("executive_summary", {})
        kpi_sum = _ensure_list(sections.get("kpi_summary", []))
        trends = sections.get("trend_analysis", {})
        root_cause = sections.get("root_cause_analysis", {})
        predictions = _ensure_list(sections.get("predictions", []))
        recommendations = _ensure_list(sections.get("recommended_actions", []))
        opps = _ensure_list(sections.get("opportunities", []))
        risks = _ensure_list(sections.get("risks", []))

        top_growth = [g for g in (result.growth or []) if getattr(g, "change_pct", 0) > 0][:3]
        top_decline = [d for d in (result.decline or []) if getattr(d, "change_pct", 0) < 0][:3]

        strategic_metrics = []
        for kpi in kpi_sum[:5]:
            if isinstance(kpi, dict):
                strategic_metrics.append({
                    "name": kpi.get("name", ""),
                    "value": kpi.get("value", "N/A"),
                    "status": kpi.get("status", ""),
                    "strategic_importance": "HIGH" if kpi.get("confidence", "0%") in ("95%", "96%", "97%", "98%", "99%") else "MEDIUM",
                })

        market_position = {
            "total_records": result.volume,
            "growth_periods": len(top_growth),
            "decline_periods": len(top_decline),
            "trend_direction": cls._get_trend_direction(trends),
            "key_drivers": root_cause.get("drivers", [])[:3],
        }

        strategic_recommendations = []
        for rec in recommendations[:5]:
            if isinstance(rec, dict):
                priority = rec.get("priority", "MEDIUM")
                if priority in ("HIGH", "CRITICAL"):
                    strategic_recommendations.append({
                        "title": rec.get("title", ""),
                        "action": rec.get("action", ""),
                        "priority": priority,
                        "expected_roi": rec.get("expected_roi", ""),
                        "timeline": rec.get("timeline", ""),
                    })

        forward_look = []
        for pred in predictions[:3]:
            if isinstance(pred, dict):
                forward_look.append({
                    "model": pred.get("model_type", ""),
                    "prediction": pred.get("prediction", ""),
                    "confidence": pred.get("confidence", 0),
                    "time_horizon": pred.get("time_horizon", ""),
                    "risk_level": pred.get("risk_level", "LOW"),
                })

        return {
            "executive_snapshot": exec_sum,
            "strategic_kpis": strategic_metrics,
            "market_position": market_position,
            "growth_trajectory": {
                "growth_periods": len(top_growth),
                "decline_periods": len(top_decline),
                "details": [
                    {"period": getattr(g, "period", ""), "change_pct": getattr(g, "change_pct", 0)}
                    for g in top_growth
                ] + [
                    {"period": getattr(d, "period", ""), "change_pct": getattr(d, "change_pct", 0)}
                    for d in top_decline
                ],
            },
            "key_drivers": root_cause.get("drivers", [])[:3],
            "forward_look": forward_look,
            "strategic_recommendations": strategic_recommendations,
            "opportunities": opps[:3] if isinstance(opps, list) else [],
            "strategic_risks": [r for r in risks[:5] if isinstance(r, dict) and r.get("severity") in ("HIGH", "CRITICAL")],
            "board_highlights": cls._build_ceo_highlights(result, sections),
        }

    @staticmethod
    def _build_ceo_highlights(result: AnalyticsResult, sections: Dict[str, Any]) -> List[str]:
        highlights = []
        if result.critical_findings:
            highlights.append(f"{len(result.critical_findings)} critical findings require executive attention.")
        if result.positive_findings:
            highlights.append(f"{len(result.positive_findings)} positive trends to leverage.")
        if result.predictions:
            highlights.append(f"{len(result.predictions)} forecast models generated for strategic planning.")
        if result.health_score:
            hs = result.health_score.overall_score if isinstance(result.health_score, HealthScore) else 0
            highlights.append(f"Business health score: {hs:.0f}/100.")
        return highlights

    # =====================================================================
    # CFO: Financial performance, forecast accuracy, ROI, budget risks
    # =====================================================================
    @classmethod
    def _build_cfo_report(cls, sections: Dict[str, Any], result: AnalyticsResult, ctx: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        exec_sum = sections.get("executive_summary", {})
        kpi_sum = _ensure_list(sections.get("kpi_summary", []))
        predictions = _ensure_list(sections.get("predictions", []))
        recommendations = _ensure_list(sections.get("recommended_actions", []))
        risks = _ensure_list(sections.get("risks", []))

        financial_kpis = []
        financial_keywords = ["revenue", "profit", "margin", "cost", "expense", "income", "roi", "budget", "cash", "sales"]
        for kpi in kpi_sum:
            if not isinstance(kpi, dict):
                continue
            name = kpi.get("name", "").lower()
            if any(fk in name for fk in financial_keywords):
                financial_kpis.append({
                    "name": kpi.get("name", ""),
                    "value": kpi.get("value", "N/A"),
                    "status": kpi.get("status", ""),
                    "financial_impact": kpi.get("insight", ""),
                })

        if not financial_kpis:
            financial_kpis = kpi_sum[:5]

        forecast_accuracy_summary = cls._summarize_forecast_accuracy(ctx)
        roi_analysis = cls._analyze_roi(recommendations)

        budget_risks = []
        for r in risks:
            if not isinstance(r, dict):
                continue
            risk_cat = r.get("type", "").lower()
            if any(fk in risk_cat for fk in ["financial", "budget", "cost", "revenue", "margin"]):
                budget_risks.append(r)

        cashflow_outlook = []
        for pred in predictions[:3]:
            if isinstance(pred, dict):
                cashflow_outlook.append({
                    "model": pred.get("model_type", ""),
                    "prediction": pred.get("prediction", ""),
                    "confidence": pred.get("confidence", 0),
                    "financial_impact": pred.get("business_impact", ""),
                })

        return {
            "executive_snapshot": exec_sum,
            "financial_kpis": financial_kpis,
            "revenue_trends": sections.get("trend_analysis", {}),
            "forecast_accuracy": forecast_accuracy_summary,
            "cashflow_outlook": cashflow_outlook,
            "roi_analysis": roi_analysis,
            "budget_risks": budget_risks[:5],
            "cost_drivers": sections.get("root_cause_analysis", {}).get("drivers", [])[:5],
            "investment_recommendations": [
                r for r in recommendations[:5]
                if isinstance(r, dict) and r.get("priority") in ("HIGH", "CRITICAL")
            ],
            "financial_opportunities": cls._extract_financial_opportunities(sections.get("opportunities", [])),
        }

    @staticmethod
    def _summarize_forecast_accuracy(ctx: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not ctx:
            return {"message": "No forecast accuracy data available."}
        forecasts = ctx.get("previous_forecasts", [])
        if not forecasts:
            return {"message": "No forecast accuracy data available."}
        return {
            "total_forecasts": len(forecasts),
            "recent_forecasts": forecasts[:5],
        }

    @staticmethod
    def _analyze_roi(recommendations: List[Any]) -> Dict[str, Any]:
        roi_items = []
        for rec in recommendations:
            if not isinstance(rec, dict):
                continue
            roi = rec.get("expected_roi", "")
            if roi:
                roi_items.append({
                    "title": rec.get("title", ""),
                    "expected_roi": roi,
                    "financial_impact": rec.get("financial_impact", ""),
                    "investment": rec.get("investment_required", ""),
                    "timeline": rec.get("timeline", ""),
                })
        return {
            "recommendations_with_roi": roi_items[:5],
            "total_analyzed": len(roi_items),
        }

    @staticmethod
    def _extract_financial_opportunities(opportunities: List[Any]) -> List[Dict[str, Any]]:
        financial_keywords = ["revenue", "profit", "cost", "margin", "budget", "savings", "efficiency"]
        result = []
        for opp in opportunities:
            if not isinstance(opp, dict):
                continue
            text = (opp.get("description", "") + " " + opp.get("title", "")).lower()
            if any(fk in text for fk in financial_keywords):
                result.append(opp)
        return result[:5]

    # =====================================================================
    # COO: Operational efficiency, anomalies, process health
    # =====================================================================
    @classmethod
    def _build_coo_report(cls, sections: Dict[str, Any], result: AnalyticsResult, ctx: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        exec_sum = sections.get("executive_summary", {})
        anomalies = result.anomalies or []
        outliers = result.outliers or []
        root_cause = sections.get("root_cause_analysis", {})
        recommendations = _ensure_list(sections.get("recommended_actions", []))
        risks = _ensure_list(sections.get("risks", []))

        operational_anomalies = []
        for a in anomalies:
            operational_anomalies.append({
                "period": a.period if hasattr(a, "period") else "",
                "title": a.title if hasattr(a, "title") else "",
                "severity": a.severity if hasattr(a, "severity") else "",
                "explanation": a.explanation if hasattr(a, "explanation") else "",
                "recommendation": a.recommendation if hasattr(a, "recommendation") else "",
                "business_impact": a.business_impact if hasattr(a, "business_impact") else "",
            })

        process_health = {
            "total_anomalies": len(anomalies),
            "high_severity": sum(1 for a in anomalies if str(getattr(a, "severity", "")).upper() in ("HIGH", "CRITICAL")),
            "outliers_detected": len(outliers),
            "dimensions_analyzed": root_cause.get("dimensions_analyzed", 0),
            "data_completeness": result.evidence.get("data_completeness", "Not computed") if result.evidence else "Not computed",
        }

        efficiency_drivers = []
        for rc in result.root_causes or []:
            if rc.concentration_risk:
                efficiency_drivers.append({
                    "dimension": rc.dimension,
                    "measure": rc.measure,
                    "grand_total": rc.grand_total,
                    "top_driver": rc.top_driver,
                    "risk": "Concentration risk detected",
                })
            else:
                for driver in rc.drivers[:2]:
                    efficiency_drivers.append({
                        "dimension": rc.dimension,
                        "measure": rc.measure,
                        "driver": driver.category,
                        "contribution_pct": driver.contribution_percentage,
                    })

        operational_recommendations = []
        for rec in recommendations:
            if not isinstance(rec, dict):
                continue
            operational_recommendations.append({
                "title": rec.get("title", ""),
                "action": rec.get("action", ""),
                "priority": rec.get("priority", ""),
                "owner": rec.get("owner", ""),
                "timeline": rec.get("timeline", ""),
            })

        return {
            "executive_snapshot": exec_sum,
            "operational_anomalies": operational_anomalies[:10],
            "process_health": process_health,
            "efficiency_drivers": efficiency_drivers[:5],
            "operational_recommendations": operational_recommendations[:5],
            "capacity_utilization": result.utilization,
            "volume_metrics": {
                "total_records": result.volume,
                "performance": result.performance,
            },
            "operational_risks": [r for r in risks[:5] if isinstance(r, dict)],
            "resource_allocation": sections.get("dimension_impact", [])[:5],
        }

    # =====================================================================
    # Sales Director: Revenue performance, pipeline, top performers, conversion
    # =====================================================================
    @classmethod
    def _build_sales_director_report(cls, sections: Dict[str, Any], result: AnalyticsResult, ctx: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        exec_sum = sections.get("executive_summary", {})
        kpi_sum = _ensure_list(sections.get("kpi_summary", []))
        trends = sections.get("trend_analysis", {})
        predictions = _ensure_list(sections.get("predictions", []))
        recommendations = _ensure_list(sections.get("recommended_actions", []))
        risks = _ensure_list(sections.get("risks", []))
        opportunities = sections.get("opportunities", [])

        sales_kpis = []
        sales_keywords = ["revenue", "sales", "conversion", "pipeline", "deal", "close", "quota", "target", "win", "loss", "opportunity"]
        for kpi in kpi_sum:
            if not isinstance(kpi, dict):
                continue
            name = kpi.get("name", "").lower()
            if any(sk in name for sk in sales_keywords):
                sales_kpis.append({
                    "name": kpi.get("name", ""),
                    "value": kpi.get("value", "N/A"),
                    "status": kpi.get("status", ""),
                    "insight": kpi.get("insight", ""),
                })
        if not sales_kpis:
            sales_kpis = kpi_sum[:5]

        revenue_trend = sections.get("revenue", {})
        top_performers = []
        for measure, ranks in (result.rankings or {}).items():
            if isinstance(ranks, list):
                top_performers.extend([
                    {
                        "measure": measure,
                        "rank": r.rank,
                        "category": r.category,
                        "value": r.value,
                        "percentage": r.percentage,
                    }
                    for r in ranks[:5]
                ])

        conversion_insights = []
        for sc in result.segment_comparisons or []:
            if any(sk in sc.metric.lower() for sk in ["conversion", "close", "win", "success"]):
                conversion_insights.append({
                    "segment_a": sc.segment_a,
                    "segment_b": sc.segment_b,
                    "metric": sc.metric,
                    "value_a": sc.value_a,
                    "value_b": sc.value_b,
                    "difference_pct": sc.difference_pct,
                    "winner": sc.winner,
                })

        pipeline_health = {
            "growth_periods": len([g for g in (result.growth or []) if getattr(g, 'change_pct', 0) > 0]),
            "decline_periods": len([d for d in (result.decline or []) if getattr(d, 'change_pct', 0) < 0]),
            "anomalies_detected": len(result.anomalies),
            "forecast_available": len(predictions) > 0,
        }

        sales_recommendations = []
        for rec in recommendations[:5]:
            if isinstance(rec, dict):
                sales_recommendations.append({
                    "title": rec.get("title", ""),
                    "action": rec.get("action", ""),
                    "priority": rec.get("priority", ""),
                    "expected_roi": rec.get("expected_roi", ""),
                    "timeline": rec.get("timeline", ""),
                    "owner": rec.get("owner", ""),
                })

        return {
            "executive_snapshot": exec_sum,
            "sales_kpis": sales_kpis,
            "revenue_trends": revenue_trend,
            "top_performers": top_performers[:10],
            "pipeline_health": pipeline_health,
            "conversion_insights": conversion_insights[:5],
            "forecast_outlook": predictions[:3],
            "sales_recommendations": sales_recommendations,
            "strategic_opportunities": opportunities[:5],
            "risk_register": [r for r in risks[:5] if isinstance(r, dict)],
        }

    # =====================================================================
    # Supply Chain Head: Efficiency, inventory, anomalies, process health
    # =====================================================================
    @classmethod
    def _build_supply_chain_report(cls, sections: Dict[str, Any], result: AnalyticsResult, ctx: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        exec_sum = sections.get("executive_summary", {})
        kpi_sum = _ensure_list(sections.get("kpi_summary", []))
        anomalies = result.anomalies or []
        outliers = result.outliers or []
        root_cause = sections.get("root_cause_analysis", {})
        recommendations = _ensure_list(sections.get("recommended_actions", []))
        risks = _ensure_list(sections.get("risks", []))
        categories = sections.get("categories", {})

        supply_chain_kpis = []
        sc_keywords = ["inventory", "stock", "ship", "deliver", "lead time", "throughput", "supply", "procure", "warehous", "logistics", "fulfill", "order"]
        for kpi in kpi_sum:
            if not isinstance(kpi, dict):
                continue
            name = kpi.get("name", "").lower()
            if any(sk in name for sk in sc_keywords):
                supply_chain_kpis.append({
                    "name": kpi.get("name", ""),
                    "value": kpi.get("value", "N/A"),
                    "status": kpi.get("status", ""),
                    "insight": kpi.get("insight", ""),
                })
        if not supply_chain_kpis:
            supply_chain_kpis = kpi_sum[:5]

        supply_anomalies = []
        for a in anomalies:
            a_type = getattr(a, 'type', '').lower()
            if any(sk in a_type for sk in ["supply", "inventory", "ship", "deliver", "stock", "operational"]):
                supply_anomalies.append({
                    "period": a.period if hasattr(a, "period") else "",
                    "title": a.title if hasattr(a, "title") else "",
                    "severity": a.severity if hasattr(a, "severity") else "",
                    "explanation": a.explanation if hasattr(a, "explanation") else "",
                    "recommendation": a.recommendation if hasattr(a, "recommendation") else "",
                    "business_impact": a.business_impact if hasattr(a, "business_impact") else "",
                })

        process_health = {
            "total_anomalies": len(anomalies),
            "supply_chain_specific_anomalies": len(supply_anomalies),
            "high_severity": sum(1 for a in anomalies if str(getattr(a, "severity", "")).upper() in ("HIGH", "CRITICAL")),
            "outliers_detected": len(outliers),
            "dimensions_analyzed": root_cause.get("dimensions_analyzed", 0),
            "data_completeness": result.evidence.get("data_completeness", "Not computed") if result.evidence else "Not computed",
        }

        efficiency_drivers = []
        for rc in result.root_causes or []:
            if rc.concentration_risk:
                efficiency_drivers.append({
                    "dimension": rc.dimension,
                    "measure": rc.measure,
                    "grand_total": rc.grand_total,
                    "top_driver": rc.top_driver,
                    "risk": "Concentration risk detected",
                })
            else:
                for driver in rc.drivers[:2]:
                    efficiency_drivers.append({
                        "dimension": rc.dimension,
                        "measure": rc.measure,
                        "driver": driver.category,
                        "contribution_pct": driver.contribution_percentage,
                    })

        category_breakdown = categories.get("distributions", [])[:5] if isinstance(categories, dict) else []

        sc_recommendations = []
        for rec in recommendations:
            if not isinstance(rec, dict):
                continue
            sc_recommendations.append({
                "title": rec.get("title", ""),
                "action": rec.get("action", ""),
                "priority": rec.get("priority", ""),
                "owner": rec.get("owner", ""),
                "timeline": rec.get("timeline", ""),
            })

        forecast_outlook = []
        for p in (sections.get("forecast", {}).get("predictions", []) or [])[:3]:
            if isinstance(p, dict):
                forecast_outlook.append({
                    "model": p.get("model_type", ""),
                    "prediction": p.get("prediction", ""),
                    "confidence": p.get("confidence", 0),
                    "time_horizon": p.get("time_horizon", ""),
                    "risk_level": p.get("risk_level", "LOW"),
                })

        return {
            "executive_snapshot": exec_sum,
            "supply_chain_kpis": supply_chain_kpis,
            "category_breakdown": category_breakdown,
            "supply_chain_anomalies": supply_anomalies[:10],
            "process_health": process_health,
            "efficiency_drivers": efficiency_drivers[:5],
            "sc_recommendations": sc_recommendations[:5],
            "forecast_outlook": forecast_outlook,
            "volume_metrics": {
                "total_records": result.volume,
                "performance": result.performance,
            },
            "operational_risks": [r for r in risks[:5] if isinstance(r, dict)],
            "resource_allocation": sections.get("dimension_impact", [])[:5],
        }

    # =====================================================================
    # CMO: Customer segments, growth opportunities, market trends
    # =====================================================================
    @classmethod
    def _build_cmo_report(cls, sections: Dict[str, Any], result: AnalyticsResult, ctx: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        exec_sum = sections.get("executive_summary", {})
        kpi_sum = _ensure_list(sections.get("kpi_summary", []))
        trends = sections.get("trend_analysis", {})
        distributions = result.distributions or {}
        rankings = result.rankings or {}
        segment_comparisons = result.segment_comparisons or []
        opportunities = _ensure_list(sections.get("opportunities", []))
        recommendations = _ensure_list(sections.get("recommended_actions", []))
        growth = result.growth or []
        decline = result.decline or []

        customer_segments = cls._extract_segments(distributions, rankings, segment_comparisons)

        marketing_kpis = []
        marketing_keywords = ["customer", "conversion", "churn", "retention", "lead", "click", "engagement", "reach", "impression"]
        for kpi in kpi_sum:
            if not isinstance(kpi, dict):
                continue
            name = kpi.get("name", "").lower()
            if any(mk in name for mk in marketing_keywords):
                marketing_kpis.append({
                    "name": kpi.get("name", ""),
                    "value": kpi.get("value", "N/A"),
                    "status": kpi.get("status", ""),
                })
        if not marketing_kpis:
            marketing_kpis = kpi_sum[:5]

        growth_opportunities = []
        for opp in opportunities:
            if not isinstance(opp, dict):
                continue
            growth_opportunities.append({
                "title": opp.get("title", ""),
                "description": opp.get("description", ""),
                "priority": opp.get("priority", "MEDIUM"),
                "impact": opp.get("impact", ""),
                "action": opp.get("action", ""),
            })

        trend_insights = []
        for measure, pts in (trends.get("trends_by_measure", {}) or {}).items():
            if isinstance(pts, dict):
                trend_insights.append({
                    "metric": measure,
                    "direction": pts.get("direction", "stable"),
                    "latest_value": pts.get("latest_value"),
                    "latest_change_pct": pts.get("latest_change_pct"),
                    "data_points": pts.get("data_points", 0),
                })

        campaign_recommendations = []
        for rec in recommendations[:5]:
            if isinstance(rec, dict):
                campaign_recommendations.append({
                    "title": rec.get("title", ""),
                    "action": rec.get("action", ""),
                    "priority": rec.get("priority", ""),
                    "expected_roi": rec.get("expected_roi", ""),
                    "timeline": rec.get("timeline", ""),
                })

        return {
            "executive_snapshot": exec_sum,
            "marketing_kpis": marketing_kpis,
            "customer_segments": customer_segments,
            "growth_opportunities": growth_opportunities[:5],
            "trend_insights": trend_insights,
            "campaign_recommendations": campaign_recommendations,
            "market_trends": {
                "growth_periods": len(growth),
                "decline_periods": len(decline),
                "patterns": result.patterns or [],
            },
            "segment_comparisons": [
                {
                    "segment_a": sc.segment_a,
                    "segment_b": sc.segment_b,
                    "metric": sc.metric,
                    "value_a": sc.value_a,
                    "value_b": sc.value_b,
                    "difference_pct": sc.difference_pct,
                    "winner": sc.winner,
                }
                for sc in segment_comparisons[:5]
            ],
            "distribution_analysis": cls._summarize_distributions(distributions),
        }

    @staticmethod
    def _extract_segments(distributions, rankings, segment_comparisons) -> List[Dict[str, Any]]:
        segments = []
        for dim, items in (distributions or {}).items():
            if isinstance(items, list) and items:
                top = items[0]
                segments.append({
                    "dimension": dim,
                    "top_category": top.category if hasattr(top, "category") else str(top.get("category", "")),
                    "top_value": top.value if hasattr(top, "value") else top.get("value", 0),
                    "top_percentage": top.percentage if hasattr(top, "percentage") else top.get("percentage", 0),
                })
        for sc in segment_comparisons[:3]:
            segments.append({
                "dimension": "comparison",
                "segment_a": sc.segment_a,
                "segment_b": sc.segment_b,
                "winner": sc.winner,
                "difference_pct": sc.difference_pct,
            })
        return segments[:10]

    @staticmethod
    def _summarize_distributions(distributions) -> List[Dict[str, Any]]:
        summary = []
        for dim, items in (distributions or {}).items():
            if not isinstance(items, list) or not items:
                continue
            values = [it.value if hasattr(it, "value") else it.get("value", 0) for it in items]
            summary.append({
                "dimension": dim,
                "categories_count": len(items),
                "top_value": max(values) if values else 0,
                "concentration_pct": (max(values) / sum(values) * 100) if sum(values) > 0 else 0,
            })
        return summary[:5]

    # =====================================================================
    # Board: Comprehensive governance view
    # =====================================================================
    @classmethod
    def _build_board_report(cls, sections: Dict[str, Any], result: AnalyticsResult, ctx: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        exec_sum = sections.get("executive_summary", {})
        kpi_sum = _ensure_list(sections.get("kpi_summary", []))
        trends = sections.get("trend_analysis", {})
        root_cause = sections.get("root_cause_analysis", {})
        predictions = _ensure_list(sections.get("predictions", []))
        recommendations = _ensure_list(sections.get("recommended_actions", []))
        risks = _ensure_list(sections.get("risks", []))
        opps = _ensure_list(sections.get("opportunities", []))
        key_findings = _ensure_list(sections.get("key_findings", []))

        governance_kpis = []
        for kpi in kpi_sum[:8]:
            if isinstance(kpi, dict):
                governance_kpis.append({
                    "name": kpi.get("name", ""),
                    "value": kpi.get("value", "N/A"),
                    "status": kpi.get("status", ""),
                    "confidence": kpi.get("confidence", "0%"),
                })

        critical_decisions = []
        if ctx:
            for d in ctx.get("previous_decisions", [])[:5]:
                critical_decisions.append({
                    "title": d.get("title", ""),
                    "decision_maker": d.get("decision_maker", ""),
                    "status": d.get("status", ""),
                    "expected_impact": d.get("expected_impact", ""),
                })

        risk_register = []
        for r in risks[:10]:
            if isinstance(r, dict):
                risk_register.append({
                    "id": r.get("id", ""),
                    "title": r.get("title", ""),
                    "severity": r.get("severity", ""),
                    "type": r.get("type", ""),
                    "impact": r.get("business_impact", ""),
                    "mitigation": r.get("recommendation", ""),
                })

        return {
            "executive_snapshot": exec_sum,
            "governance_kpis": governance_kpis,
            "business_health": {
                "score": result.health_score.overall_score if isinstance(result.health_score, HealthScore) else 0,
                "grade": result.health_score.grade if isinstance(result.health_score, HealthScore) else "N/A",
                "status": result.health_score.status if isinstance(result.health_score, HealthScore) else "Unknown",
                "breakdown": result.health_score.breakdown if isinstance(result.health_score, HealthScore) else [],
            },
            "strategic_trends": trends,
            "key_drivers": root_cause.get("drivers", [])[:5],
            "predictive_outlook": predictions[:5],
            "strategic_recommendations": recommendations[:5],
            "risk_register": risk_register,
            "opportunity_portfolio": opps[:5] if isinstance(opps, list) else [],
            "key_findings": key_findings[:10],
            "critical_decisions": critical_decisions,
            "forecast_confidence": cls._summarize_forecast_accuracy(ctx),
        }

    @staticmethod
    def _get_trend_direction(trends: Dict[str, Any]) -> str:
        trends_by_measure = trends.get("trends_by_measure", {})
        if not trends_by_measure:
            return "stable"
        directions = [v.get("direction", "stable") for v in trends_by_measure.values() if isinstance(v, dict)]
        if not directions:
            return "stable"
        up = directions.count("upward")
        down = directions.count("downward")
        if up > down:
            return "upward"
        elif down > up:
            return "downward"
        return "stable"

    @classmethod
    def generate_role_specific_report(
        cls,
        analytics_result: AnalyticsResult,
        semantic_model: SemanticModel,
        audience: str,
        predictions: Optional[List[Any]] = None,
        extra_context: Optional[Dict[str, Any]] = None,
        format: str = "json",
    ) -> Dict[str, Any]:
        report = cls.generate_report(
            analytics_result=analytics_result,
            semantic_model=semantic_model,
            audience=audience,
            predictions=predictions,
            extra_context=extra_context,
        )
        if format == "markdown":
            report["markdown"] = cls._render_markdown(report, audience)
        return report

    @staticmethod
    def _render_markdown(report: Dict[str, Any], audience: str) -> str:
        lines = [
            f"# {report.get('report_title', 'Executive Report')}",
            f"**Generated:** {report.get('generated_at', '')[:19]}",
            f"**Audience:** {audience}",
            f"**Domain:** {report.get('domain', 'N/A')}",
            f"**Dataset Type:** {report.get('dataset_type', 'N/A')}",
            f"**Health Score:** {report.get('health_score', 0):.0f}/100 ({report.get('health_status', 'Unknown')})",
            "",
            "---",
            "",
        ]

        sections = report.get("sections", {})
        for section_name, section_data in sections.items():
            lines.append(f"## {section_name.replace('_', ' ').title()}")
            lines.append("")
            lines.append(cls._render_section_markdown(section_data))
            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _render_section_markdown(data: Any, indent: int = 0) -> str:
        if data is None:
            return ""
        if isinstance(data, str):
            return data
        if isinstance(data, (int, float)):
            return str(data)
        if isinstance(data, list):
            lines = []
            for item in data:
                if isinstance(item, dict):
                    lines.append(RoleBasedReportEngine._render_dict_markdown(item, indent))
                else:
                    lines.append(f"- {item}")
            return "\n".join(lines)
        if isinstance(data, dict):
            return RoleBasedReportEngine._render_dict_markdown(data, indent)
        return str(data)

    @staticmethod
    def _render_dict_markdown(d: Dict[str, Any], indent: int = 0) -> str:
        lines = []
        prefix = "  " * indent
        for key, value in d.items():
            if value is None:
                continue
            if isinstance(value, (dict, list)):
                lines.append(f"{prefix}**{key}:**")
                lines.append(RoleBasedReportEngine._render_section_markdown(value, indent + 1))
            else:
                lines.append(f"{prefix}**{key}:** {value}")
        return "\n".join(lines)
