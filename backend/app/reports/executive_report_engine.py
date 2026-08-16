from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.schemas.analytics import (
    AnalyticsResult,
    KPIMetric,
    RiskItem,
    OpportunityItem,
    Recommendation,
    HealthScore,
    BusinessAnomaly,
    RootCause,
    DistributionItem,
    TrendPoint,
    Prediction,
    SegmentComparison,
)
from app.semantic_model.core import SemanticModel
from app.ai.explainable_ai_engine import ExplainableAIEngine
from app.logging.logger import get_logger
logger = get_logger(__name__)


class UniversalExecutiveReportEngine:
    """
    Universal Executive Report Engine.

    Input:  SemanticModel + AnalyticsResult + optional Prediction list
    Output: Structured ExecutiveReport dict

    Produces 13+ adaptive sections for ANY industry.
    No retail-specific assumptions. No hardcoded magic financial values.
    """

    @classmethod
    def _normalize_analytics(cls, res: Any) -> AnalyticsResult:
        if isinstance(res, AnalyticsResult):
            return cls._coerce_nested(res)
        if isinstance(res, dict) and res:
            try:
                ar = AnalyticsResult()
                for k, v in res.items():
                    if hasattr(ar, k):
                        setattr(ar, k, v)
                return cls._coerce_nested(ar)
            except Exception:
                pass
        return AnalyticsResult(health_score=HealthScore())

    @classmethod
    def _coerce_nested(cls, ar: AnalyticsResult) -> AnalyticsResult:
        try:
            if isinstance(ar.health_score, dict):
                ar.health_score = HealthScore(
                    overall_score=float(ar.health_score.get("overall_score", 78.0)),
                    grade=str(ar.health_score.get("grade", "B")),
                    status=str(ar.health_score.get("status", "Good")),
                )

            if ar.kpis and not isinstance(ar.kpis[0], KPIMetric):
                ar.kpis = [KPIMetric(**k) if isinstance(k, dict) else k for k in ar.kpis]

            if ar.risks and not isinstance(ar.risks[0], RiskItem):
                ar.risks = [RiskItem(**r) if isinstance(r, dict) else r for r in ar.risks]

            if ar.opportunities and not isinstance(ar.opportunities[0], OpportunityItem):
                ar.opportunities = [OpportunityItem(**o) if isinstance(o, dict) else o for o in ar.opportunities]

            if ar.recommendations and not isinstance(ar.recommendations[0], Recommendation):
                ar.recommendations = [Recommendation(**r) if isinstance(r, dict) else r for r in ar.recommendations]

            if ar.anomalies and not isinstance(ar.anomalies[0], BusinessAnomaly):
                ar.anomalies = [BusinessAnomaly(**a) if isinstance(a, dict) else a for a in ar.anomalies]

            if ar.root_causes and not isinstance(ar.root_causes[0], RootCause):
                ar.root_causes = [RootCause(**rc) if isinstance(rc, dict) else rc for rc in ar.root_causes]

            if ar.predictions and not isinstance(ar.predictions[0], Prediction):
                ar.predictions = [Prediction(**p) if isinstance(p, dict) else p for p in ar.predictions]

            if ar.segment_comparisons and not isinstance(ar.segment_comparisons[0], SegmentComparison):
                ar.segment_comparisons = [SegmentComparison(**sc) if isinstance(sc, dict) else sc for sc in ar.segment_comparisons]

            if ar.distributions:
                norm_dist = {}
                for dim, items in ar.distributions.items():
                    if items and not isinstance(items[0], DistributionItem):
                        norm_dist[dim] = [DistributionItem(**it) if isinstance(it, dict) else it for it in items]
                    else:
                        norm_dist[dim] = items
                ar.distributions = norm_dist

            if ar.trends:
                norm_trends = {}
                for measure, points in ar.trends.items():
                    if points and not isinstance(points[0], TrendPoint):
                        norm_trends[measure] = [TrendPoint(**p) if isinstance(p, dict) else p for p in points]
                    else:
                        norm_trends[measure] = points
                ar.trends = norm_trends
        except Exception:
            pass
        return ar

    @classmethod
    def generate_report(
        cls,
        analytics_result: AnalyticsResult,
        semantic_model: SemanticModel,
        prediction_result: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        analytics_result = cls._normalize_analytics(analytics_result)
        domain = getattr(semantic_model, "domain", None) or analytics_result.domain or "Generic Business"
        dataset_type = analytics_result.dataset_type or getattr(semantic_model, "dataset_type", None) or "Unknown Dataset"
        generated_at = datetime.now(timezone.utc).isoformat()
        errors: List[str] = []

        section_builders = {
            "executive_summary": lambda: cls._build_executive_summary(analytics_result, domain, dataset_type),
            "business_health": lambda: cls._build_business_health(analytics_result),
            "kpi_summary": lambda: cls._build_kpi_summary(analytics_result),
            "kpi_overview": lambda: cls._build_kpi_summary(analytics_result),
            "trend_analysis": lambda: cls._build_trend_analysis(analytics_result, domain),
            "forecast": lambda: cls._build_forecast_section(analytics_result, prediction_result, domain),
            "root_cause_analysis": lambda: cls._build_root_cause_analysis(analytics_result, domain),
            "risks": lambda: cls._build_risks_section(analytics_result, domain),
            "opportunities": lambda: cls._build_opportunities_section(analytics_result, domain),
            "recommendations": lambda: cls._build_recommendations_section(analytics_result, domain),
            "evidence": lambda: cls._build_evidence_section(analytics_result),
            "charts": lambda: cls._build_charts_section(analytics_result),
            "what_if_analysis": lambda: cls._build_what_if_analysis(analytics_result, semantic_model, domain),
            "recommended_actions": lambda: cls._build_recommended_actions(analytics_result, domain),
            "business_impact": lambda: cls._build_business_impact(analytics_result, domain),
            "key_findings": lambda: cls._build_key_findings(analytics_result, domain),
            "confidence_evidence": lambda: cls._build_confidence_evidence(analytics_result),
            "roadmap_30_90_180": lambda: cls._build_action_plan_section(analytics_result, domain),
            "domain_specific": lambda: cls._build_domain_specific(analytics_result, domain, dataset_type),
            "primary_metrics": lambda: cls._build_primary_metrics_section(analytics_result),
            "dimension_analysis": lambda: cls._build_dimension_analysis_section(analytics_result),
            "dimension_distributions": lambda: cls._build_dimension_distributions_section(analytics_result),
            "measure_rankings": lambda: cls._build_measure_rankings_section(analytics_result),
        }

        sections: Dict[str, Any] = {}
        for section_name, builder in section_builders.items():
            try:
                sections[section_name] = builder()
            except Exception as e:
                logger.error(f"Report generation stage '{section_name}' failed: {str(e)}")
                errors.append(f"Stage '{section_name}' failed: {str(e)}")
                sections[section_name] = {"error": str(e), "stage": section_name}

        return {
            "generated_at": generated_at,
            "domain": domain,
            "dataset_type": dataset_type,
            "sections": sections,
            "report_sections": sections,
            "errors": errors,
            "generation_status": "partial" if errors else "complete",
        }

    @staticmethod
    def _build_executive_summary(result: AnalyticsResult, domain: str, dataset_type: str) -> Dict[str, Any]:
        health = result.health_score if isinstance(result.health_score, HealthScore) else HealthScore()
        available_kpis = [k for k in result.kpis if k.available]
        primary_kpi = available_kpis[0] if available_kpis else None
        volume = result.volume or 0

        if volume == 0 and not available_kpis:
            return {
                "text": f"{domain} workspace initialized. No data has been ingested yet. Upload a dataset to generate a full executive report for {dataset_type}.",
                "health_score": 0,
                "health_status": "No Data",
                "total_records": 0,
                "domain": domain,
                "dataset_type": dataset_type,
                "primary_kpi": "N/A",
                "available_kpis_count": 0,
                "anomalies_detected": 0,
                "predictions_available": 0,
                "recommendations_available": 0,
            }

        parts = []
        if volume > 0:
            parts.append(f"{domain} workspace analyzed with {volume:,} verified records.")
        else:
            parts.append(f"{domain} workspace is active with {dataset_type} context.")

        if primary_kpi:
            parts.append(f"Primary metric: {primary_kpi.name} = {primary_kpi.formatted_value}.")
        elif available_kpis:
            parts.append(f"Primary metric: {available_kpis[0].name} = {available_kpis[0].formatted_value}.")
        else:
            parts.append("No KPIs computed yet for this dataset.")

        parts.append(f"Business health score: {health.overall_score:.0f}/100 ({health.status}).")
        parts.append(f"{len(available_kpis)} KPIs available for review.")

        if result.anomalies:
            parts.append(f"{len(result.anomalies)} anomalies detected.")
        if result.predictions:
            feasible_preds = [p for p in result.predictions if getattr(p, 'feasible', False)]
            if feasible_preds:
                parts.append(f"{len(feasible_preds)} predictive models generated.")
        if result.recommendations:
            parts.append(f"{len(result.recommendations)} recommendations generated.")

        text = " ".join(parts)

        return {
            "text": text,
            "health_score": round(health.overall_score, 1),
            "health_status": health.status,
            "total_records": volume,
            "domain": domain,
            "dataset_type": dataset_type,
            "primary_kpi": primary_kpi.name if primary_kpi else (available_kpis[0].name if available_kpis else "N/A"),
            "available_kpis_count": len(available_kpis),
            "anomalies_detected": len(result.anomalies),
            "predictions_available": len([p for p in result.predictions if getattr(p, 'feasible', False)]) if result.predictions else 0,
            "recommendations_available": len(result.recommendations),
        }

    @staticmethod
    def _build_dataset_overview(result: AnalyticsResult, semantic_model: SemanticModel) -> Dict[str, Any]:
        profile = result.evidence or {}
        measures = profile.get("measures_analyzed", [])
        dimensions = profile.get("dimensions_analyzed", [])
        total_rows = profile.get("total_rows", result.volume)
        temporal_count = 0
        for t_key, t_vals in (result.trends or {}).items():
            if t_vals:
                temporal_count = max(temporal_count, len(t_vals))

        overview = {
            "total_records": total_rows,
            "total_columns": len(measures) + len(dimensions),
            "measures": measures,
            "dimensions": dimensions,
            "temporal_periods": temporal_count,
            "dataset_type": result.dataset_type,
            "domain": result.domain,
            "data_completeness": "Not computed",
        }

        if semantic_model.business_entities:
            overview["entities_detected"] = list(semantic_model.business_entities)

        return overview

    @staticmethod
    def _val(obj: Any, key: str, default: Any = "") -> Any:
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    @staticmethod
    def _build_kpi_summary(result: AnalyticsResult) -> List[Dict[str, Any]]:
        kpi_list = []
        for k in (result.kpis or []):
            if not UniversalExecutiveReportEngine._val(k, "available", True):
                continue
            kpi_list.append({
                "name": UniversalExecutiveReportEngine._val(k, "name", "KPI"),
                "value": UniversalExecutiveReportEngine._val(k, "formatted_value", "N/A"),
                "source_column": UniversalExecutiveReportEngine._val(k, "source_column", ""),
                "calculation": UniversalExecutiveReportEngine._val(k, "formula", ""),
                "confidence": f"{float(UniversalExecutiveReportEngine._val(k, 'confidence', 95)):.0f}%",
                "status": UniversalExecutiveReportEngine._val(k, "status", "STABLE"),
                "insight": UniversalExecutiveReportEngine._val(k, "insight", "") or f"Aggregate {UniversalExecutiveReportEngine._val(k, 'source_column')} computed across records.",
            })
        return kpi_list

    @staticmethod
    def _build_trend_analysis(result: AnalyticsResult, domain: str) -> Dict[str, Any]:
        trends_summary = {
            "growth_periods": len(result.growth or []),
            "decline_periods": len(result.decline or []),
            "trends_by_measure": {},
            "patterns": result.patterns or [],
            "forecast_available": bool(result.predictions),
        }

        for measure, points in (result.trends or {}).items():
            if not points:
                continue
            vals = [float(UniversalExecutiveReportEngine._val(p, "value")) for p in points if UniversalExecutiveReportEngine._val(p, "value") is not None]
            if not vals:
                continue
            up = sum(1 for p in points if UniversalExecutiveReportEngine._val(p, "change_pct") and UniversalExecutiveReportEngine._val(p, "change_pct") > 0)
            down = sum(1 for p in points if UniversalExecutiveReportEngine._val(p, "change_pct") and UniversalExecutiveReportEngine._val(p, "change_pct") < 0)
            latest = points[-1]
            trends_summary["trends_by_measure"][measure] = {
                "data_points": len(points),
                "latest_value": UniversalExecutiveReportEngine._val(latest, "value"),
                "latest_change_pct": UniversalExecutiveReportEngine._val(latest, "change_pct"),
                "up_periods": up,
                "down_periods": down,
                "direction": "upward" if up > down else "downward" if down > up else "stable",
            }

        return trends_summary

    @staticmethod
    def _build_root_cause_analysis(result: AnalyticsResult, domain: str) -> Dict[str, Any]:
        drivers_summary = []
        for rc in (result.root_causes or []):
            drivers_summary.append({
                "dimension": UniversalExecutiveReportEngine._val(rc, "dimension", ""),
                "measure": UniversalExecutiveReportEngine._val(rc, "measure", ""),
                "grand_total": UniversalExecutiveReportEngine._val(rc, "grand_total", 0),
                "top_driver": UniversalExecutiveReportEngine._val(rc, "top_driver", {}),
                "concentration_risk": UniversalExecutiveReportEngine._val(rc, "concentration_risk", False),
                "driver_count": len(UniversalExecutiveReportEngine._val(rc, "drivers", []) or []),
            })

        return {
            "dimensions_analyzed": len(result.root_causes or []),
            "drivers": drivers_summary,
            "segment_comparisons": [
                {
                    "segment_a": UniversalExecutiveReportEngine._val(sc, "segment_a", ""),
                    "segment_b": UniversalExecutiveReportEngine._val(sc, "segment_b", ""),
                    "metric": UniversalExecutiveReportEngine._val(sc, "metric", ""),
                    "value_a": UniversalExecutiveReportEngine._val(sc, "value_a", 0),
                    "value_b": UniversalExecutiveReportEngine._val(sc, "value_b", 0),
                    "difference_pct": UniversalExecutiveReportEngine._val(sc, "difference_pct", 0),
                    "winner": UniversalExecutiveReportEngine._val(sc, "winner", ""),
                }
                for sc in (result.segment_comparisons or [])
            ],
            "correlations": [
                {
                    "columns": f"{UniversalExecutiveReportEngine._val(c, 'column_a', '')} vs {UniversalExecutiveReportEngine._val(c, 'column_b', '')}",
                    "coefficient": UniversalExecutiveReportEngine._val(c, "coefficient", 0),
                    "strength": UniversalExecutiveReportEngine._val(c, "strength", "MODERATE"),
                }
                for c in (result.correlations or [])
            ],
        }

    @staticmethod
    def _build_risks(result: AnalyticsResult, domain: str) -> List[Dict[str, Any]]:
        risks = []
        for idx, r in enumerate(result.risks or [], 1):
            risks.append({
                "id": UniversalExecutiveReportEngine._val(r, "id", f"RSK-{idx:03d}"),
                "title": UniversalExecutiveReportEngine._val(r, "title", f"Risk #{idx}"),
                "type": UniversalExecutiveReportEngine._val(r, "category", "Operational Risk"),
                "severity": UniversalExecutiveReportEngine._val(r, "severity", "MEDIUM"),
                "period": "Latest Period",
                "actual": "N/A",
                "expected": "Baseline",
                "z_score": None,
                "pct_change": 0.0,
                "explanation": UniversalExecutiveReportEngine._val(r, "description", ""),
                "business_impact": UniversalExecutiveReportEngine._val(r, "impact", ""),
                "possible_causes": UniversalExecutiveReportEngine._val(r, "causes", []),
                "recommendation": UniversalExecutiveReportEngine._val(r, "mitigation", ""),
            })

        for a in (result.anomalies or [])[:5]:
            risks.append({
                "id": f"RSK-{len(risks)+1:03d}",
                "title": UniversalExecutiveReportEngine._val(a, "title", "Anomaly"),
                "type": UniversalExecutiveReportEngine._val(a, "type", "Anomaly"),
                "severity": UniversalExecutiveReportEngine._val(a, "severity", "HIGH"),
                "period": UniversalExecutiveReportEngine._val(a, "period", "N/A"),
                "actual": UniversalExecutiveReportEngine._val(a, "actual_value", 0),
                "expected": UniversalExecutiveReportEngine._val(a, "expected_value", 0),
                "z_score": UniversalExecutiveReportEngine._val(a, "z_score", None),
                "pct_change": UniversalExecutiveReportEngine._val(a, "pct_change", 0.0),
                "explanation": UniversalExecutiveReportEngine._val(a, "explanation", ""),
                "business_impact": UniversalExecutiveReportEngine._val(a, "business_impact", ""),
                "possible_causes": UniversalExecutiveReportEngine._val(a, "possible_causes", []),
                "recommendation": UniversalExecutiveReportEngine._val(a, "recommendation", ""),
            })

        return risks

    @staticmethod
    def _build_opportunities(result: AnalyticsResult, domain: str) -> List[Dict[str, Any]]:
        opps = []
        confidence_result = ExplainableAIEngine.compute_confidence(
            profile=result.evidence or {},
            recommendations=result.recommendations or [],
        )
        opp_confidence = round(confidence_result.overall_score * 100.0, 1)
        for idx, o in enumerate(result.opportunities or [], 1):
            opps.append({
                "id": UniversalExecutiveReportEngine._val(o, "id", f"OPP-{idx:03d}"),
                "title": UniversalExecutiveReportEngine._val(o, "title", f"Opportunity #{idx}"),
                "metric": UniversalExecutiveReportEngine._val(o, "category", "Growth"),
                "value": "N/A",
                "description": UniversalExecutiveReportEngine._val(o, "description", ""),
                "confidence": opp_confidence,
                "evidence": f"{UniversalExecutiveReportEngine._val(o, 'category', 'Growth')} opportunity detected in {domain} analysis.",
            })

        for d in result.key_drivers:
            td = d.get("top_driver") if isinstance(d, dict) else None
            if td and not d.get("concentration_risk"):
                cat_name = td.get("category", "Top Segment") if isinstance(td, dict) else "Top Segment"
                contrib = td.get("contribution_percentage", 0.0) if isinstance(td, dict) else 0.0
                opps.append({
                    "id": f"OPP-{len(opps)+1:03d}",
                    "title": f"Expand '{cat_name}' Presence",
                    "metric": d.get("measure", "Performance"),
                    "value": f"{contrib:.1f}%",
                    "description": f"Top segment '{cat_name}' leads contribution at {contrib:.1f}%.",
                    "confidence": opp_confidence,
                    "evidence": f"Highest contributor in dimension '{d.get('dimension', 'N/A')}'",
                })

        if not opps:
            return opps

        return opps

    @staticmethod
    def _build_predictions(result: AnalyticsResult, prediction_result: Optional[List[Any]], domain: str) -> List[Dict[str, Any]]:
        preds = prediction_result or result.predictions or []
        pred_list = []
        for p in preds[:8]:
            if isinstance(p, dict):
                pred_list.append({
                    "model_type": p.get("model_type", "Unknown"),
                    "model_used": p.get("model_used", ""),
                    "prediction": p.get("prediction", ""),
                    "confidence": p.get("confidence", 0.0),
                    "time_horizon": p.get("time_horizon", ""),
                    "risk_level": p.get("risk_level", "LOW"),
                    "recommended_action": p.get("recommended_action", ""),
                    "feasible": p.get("feasible", True),
                    "limitation": p.get("limitation"),
                })
            else:
                pred_list.append({
                    "model_type": getattr(p, "model_type", "Unknown"),
                    "model_used": getattr(p, "model_used", ""),
                    "prediction": getattr(p, "prediction", ""),
                    "confidence": getattr(p, "confidence", 0.0),
                    "time_horizon": getattr(p, "time_horizon", ""),
                    "risk_level": getattr(p, "risk_level", "LOW"),
                    "recommended_action": getattr(p, "recommended_action", ""),
                    "feasible": getattr(p, "feasible", True),
                    "limitation": getattr(p, "limitation", None),
                })
        return pred_list

    @staticmethod
    def _build_what_if_analysis(result: AnalyticsResult, semantic_model: SemanticModel, domain: str) -> Dict[str, Any]:
        what_if = {
            "available": False,
            "baseline_metric_sum": 0.0,
            "scenarios": [],
            "assumptions": [],
        }

        measures = (result.evidence or {}).get("measures_analyzed", [])
        if measures:
            primary_measure = measures[0]
            what_if["baseline_metric_sum"] = float(result.summary_statistics.get(primary_measure, {}).get("sum", 0.0))
            what_if["primary_measure"] = primary_measure
            what_if["available"] = True

        if not what_if["available"]:
            what_if["note"] = "What-if analysis requires numeric measures. Add numeric columns to enable scenario modeling."

        return what_if

    @staticmethod
    def _build_recommended_actions(result: AnalyticsResult, domain: str) -> List[Dict[str, Any]]:
        actions = []
        seen = set()

        for r in result.recommendations:
            key = r.title
            if key in seen:
                continue
            seen.add(key)
            actions.append({
                "id": r.id,
                "title": r.title,
                "priority": r.priority,
                "rationale": r.reason,
                "action": r.action,
                "confidence": f"{r.confidence:.0f}%",
                "owner": r.owner,
                "timeline": r.timeline,
                "expected_roi": r.expected_roi,
                "financial_impact": r.financial_impact,
                "investment_required": r.investment_required,
            })

        if not actions:
            return actions

        return actions

    @staticmethod
    def _build_business_impact(result: AnalyticsResult, domain: str) -> Dict[str, Any]:
        impact = {
            "critical_findings_count": len(result.critical_findings),
            "positive_findings_count": len(result.positive_findings),
            "negative_findings_count": len(result.negative_findings),
            "key_findings": result.critical_findings + result.positive_findings + result.negative_findings,
            "key_drivers": result.key_drivers,
        }

        if result.growth:
            impact["growth_summary"] = f"{len(result.growth)} significant growth periods identified."
        if result.decline:
            impact["decline_summary"] = f"{len(result.decline)} significant decline periods identified."
        if result.outliers:
            impact["outliers_summary"] = f"{len(result.outliers)} statistical outliers detected."

        return impact

    @staticmethod
    def _build_confidence_evidence(result: AnalyticsResult) -> Dict[str, Any]:
        evidence = result.evidence or {}
        return {
            "confidence_score": round(result.confidence_score, 1),
            "health_breakdown": result.health_score.breakdown if hasattr(result.health_score, "breakdown") else [],
            "dataset_path": evidence.get("dataset_path", ""),
            "measures_analyzed": evidence.get("measures_analyzed", []),
            "dimensions_analyzed": evidence.get("dimensions_analyzed", []),
            "models_used": evidence.get("models_used", []),
            "traceability": evidence.get("traceability", ""),
            "errors": result.errors,
        }

    @staticmethod
    def _build_roadmap(result: AnalyticsResult, domain: str) -> Dict[str, Any]:
        actions_30 = []
        actions_90 = []
        actions_180 = []

        confidence_result = ExplainableAIEngine.compute_confidence(
            profile=result.evidence or {},
            recommendations=result.recommendations,
        )
        base_confidence = round(confidence_result.overall_score * 100.0, 1)

        for r in result.recommendations:
            item = {"title": r.title, "priority": r.priority, "confidence": r.confidence}
            timeline = (r.timeline or "").lower()
            if "30" in timeline or "immediate" in timeline or "14" in timeline or "short" in timeline:
                actions_30.append(item)
            elif "90" in timeline or "medium" in timeline:
                actions_90.append(item)
            elif "180" in timeline or "long" in timeline:
                actions_180.append(item)
            else:
                actions_90.append(item)

        for r in result.risks:
            if r.severity in ("CRITICAL", "HIGH"):
                actions_30.append({"title": f"Mitigate: {r.title}", "priority": "HIGH", "confidence": base_confidence})

        return {
            "next_30_days": actions_30,
            "next_90_days": actions_90,
            "next_180_days": actions_180,
        }

    @staticmethod
    def _build_key_findings(result: AnalyticsResult, domain: str) -> List[Dict[str, Any]]:
        findings = []
        confidence_result = ExplainableAIEngine.compute_confidence(
            profile=result.evidence or {},
            kpis=result.kpis,
        )
        base_confidence = round(confidence_result.overall_score * 100.0, 1)

        for insight in (result.critical_findings or [])[:5]:
            findings.append({
                "type": "insight",
                "title": "Critical Finding",
                "detail": insight,
                "finding": insight,
                "severity": "HIGH",
                "agent": "Executive Analytics Platform",
                "focus": domain,
                "confidence": f"{base_confidence:.0f}%",
                "recommendation": "",
                "impact": "",
            })

        for insight in (result.positive_findings or [])[:3]:
            findings.append({
                "type": "insight",
                "title": "Positive Finding",
                "detail": insight,
                "finding": insight,
                "severity": "LOW",
                "agent": "Executive Analytics Platform",
                "focus": domain,
                "confidence": f"{base_confidence:.0f}%",
                "recommendation": "",
                "impact": "",
            })

        for anomaly in (result.anomalies or [])[:3]:
            findings.append({
                "type": "anomaly",
                "title": anomaly.title,
                "detail": anomaly.explanation,
                "finding": anomaly.explanation,
                "severity": anomaly.severity,
                "agent": "Anomaly Detection System",
                "focus": anomaly.type,
                "confidence": f"{anomaly.confidence_score:.0f}%",
                "recommendation": anomaly.recommendation,
                "impact": anomaly.business_impact,
            })

        return findings

    @staticmethod
    def _build_domain_specific(result: AnalyticsResult, domain: str, dataset_type: str) -> Dict[str, Any]:
        specific = {"domain": domain, "dataset_type": dataset_type, "sections": []}

        if result.root_causes:
            specific["sections"].append({
                "title": f"{domain} Key Drivers",
                "items": [
                    f"Primary dimension analyzed: {rc.dimension} on {rc.measure}."
                    for rc in result.root_causes[:2]
                ]
                + [
                    f"Top driver: {rc.top_driver.get('category', 'N/A')} contributing "
                    f"{rc.top_driver.get('contribution_percentage', 0):.1f}% of total."
                    for rc in result.root_causes[:2]
                    if rc.top_driver
                ],
            })

        if result.anomalies:
            specific["sections"].append({
                "title": "Anomaly Analysis",
                "items": [
                    f"{a.title}: {a.explanation}"
                    for a in result.anomalies[:3]
                ],
            })

        if result.predictions:
            specific["sections"].append({
                "title": "Predictive Insights",
                "items": [
                    p.prediction for p in result.predictions[:2]
                    if p.prediction
                ],
            })

        if result.recommendations:
            specific["sections"].append({
                "title": "Strategic Recommendations",
                "items": [
                    r.action for r in result.recommendations[:3]
                ],
            })

        if not specific["sections"]:
            specific["sections"].append({
                "title": f"{domain} Dataset Analysis",
                "items": [
                    f"Analyzed {result.volume:,} records with {len(result.kpis)} KPIs.",
                    f"Health score: {result.health_score.overall_score:.0f}/100 ({result.health_score.status}).",
                ],
            })

        return specific

    @staticmethod
    def _build_business_health(result: AnalyticsResult) -> Dict[str, Any]:
        health = result.health_score if isinstance(result.health_score, HealthScore) else HealthScore()
        breakdown = health.breakdown if isinstance(health.breakdown, list) else []
        grade = health.grade if hasattr(health, 'grade') and health.grade else "N/A"
        status = health.status if hasattr(health, 'status') and health.status else "Unknown"

        if not breakdown:
            breakdown = [
                {"component": "Data Completeness", "score": round(result.confidence_score, 1), "weight": "25%"},
                {"component": "KPI Coverage", "score": round(min(100, len([k for k in result.kpis if k.available]) * 10), 1), "weight": "25%"},
                {"component": "Anomaly Control", "score": round(max(0, 100 - len(result.anomalies) * 5), 1), "weight": "25%"},
                {"component": "Forecast Readiness", "score": round(80 if result.predictions else 40, 1), "weight": "25%"},
            ]

        overall = round(health.overall_score, 1)
        if overall >= 90:
            grade = "A"
            status = "Excellent"
        elif overall >= 80:
            grade = "B"
            status = "Good"
        elif overall >= 70:
            grade = "C"
            status = "Fair"
        elif overall >= 60:
            grade = "D"
            status = "At Risk"
        else:
            grade = "F"
            status = "Critical"

        return {
            "score": overall,
            "grade": grade,
            "status": status,
            "breakdown": breakdown,
            "summary": f"Business health is {status.lower()} with a score of {overall:.0f}/100 (Grade {grade}).",
        }

    @staticmethod
    def _build_kpis_section(result: AnalyticsResult) -> Dict[str, Any]:
        available = [k for k in result.kpis if k.available]
        unavailable = [k for k in result.kpis if not k.available]
        kpi_list = []
        for k in available:
            kpi_list.append({
                "name": k.name,
                "value": k.formatted_value,
                "source_column": k.source_column,
                "calculation": k.formula,
                "confidence": f"{k.confidence:.0f}%",
                "status": k.status,
                "insight": getattr(k, "insight", "") or f"Aggregate {k.source_column} computed across {k.rows_analyzed:,} rows.",
            })
        return {
            "total_kpis": len(result.kpis),
            "available_kpis": len(available),
            "unavailable_kpis": len(unavailable),
            "kpis": kpi_list,
        }

    @staticmethod
    def _build_primary_metrics_section(result: AnalyticsResult) -> Dict[str, Any]:
        primary_kpis = []
        for k in result.kpis[:8]:
            if not k.available:
                continue
            primary_kpis.append({
                "name": k.name,
                "value": k.formatted_value,
                "source_column": k.source_column,
                "calculation": k.formula,
                "confidence": f"{k.confidence:.0f}%",
                "status": k.status,
                "insight": getattr(k, "insight", "") or f"Aggregate {k.source_column} computed across {k.rows_analyzed:,} rows.",
            })

        primary_trends = {}
        for measure, points in (result.trends or {}).items():
            if not points:
                continue
            vals = [float(p.value) for p in points if p.value is not None]
            if not vals:
                continue
            primary_trends[measure] = {
                "data_points": len(points),
                "latest_value": points[-1].value if points else 0,
                "latest_change_pct": points[-1].change_pct if points and points[-1].change_pct else 0,
                "min": min(vals),
                "max": max(vals),
                "avg": round(sum(vals) / len(vals), 2),
            }

        growth_periods = [g for g in (result.growth or []) if getattr(g, 'change_pct', 0) > 0]
        decline_periods = [d for d in (result.decline or []) if getattr(d, 'change_pct', 0) < 0]

        return {
            "kpis": primary_kpis[:8],
            "trends": primary_trends,
            "growth_periods_count": len(growth_periods),
            "decline_periods_count": len(decline_periods),
            "note": "Primary metrics are derived from available KPIs and trends. Missing metrics indicate the dataset lacks the corresponding columns.",
        }

    @staticmethod
    def _build_dimension_analysis_section(result: AnalyticsResult) -> Dict[str, Any]:
        dimension_kpis = []
        for k in result.kpis[:6]:
            if not k.available:
                continue
            dimension_kpis.append({
                "name": k.name,
                "value": k.formatted_value,
                "status": k.status,
                "confidence": f"{k.confidence:.0f}%",
            })

        segments = []
        for dim, items in (result.distributions or {}).items():
            if not isinstance(items, list) or not items:
                continue
            top = items[0]
            segments.append({
                "dimension": dim,
                "top_category": top.category if hasattr(top, "category") else str(top.get("category", "")),
                "top_value": top.value if hasattr(top, "value") else top.get("value", 0),
                "top_percentage": top.percentage if hasattr(top, "percentage") else top.get("percentage", 0),
            })

        return {
            "kpis": dimension_kpis[:6],
            "segments": segments[:5],
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
                for sc in result.segment_comparisons[:3]
            ],
        }

    @staticmethod
    def _build_dimension_distributions_section(result: AnalyticsResult) -> Dict[str, Any]:
        distributions = []
        for dim, items in (result.distributions or {}).items():
            if not isinstance(items, list) or not items:
                continue
            values = [it.value if hasattr(it, "value") else it.get("value", 0) for it in items]
            total = sum(values) if values else 0
            distributions.append({
                "dimension": dim,
                "categories_count": len(items),
                "total_value": total,
                "top_category": items[0].category if hasattr(items[0], "category") else items[0].get("category", ""),
                "top_value": values[0] if values else 0,
                "top_percentage": (values[0] / total * 100) if total > 0 else 0,
                "concentration_pct": (max(values) / total * 100) if total > 0 else 0,
            })

        def _get(obj: Any, attr: str, default: Any = "") -> Any:
            if isinstance(obj, dict):
                return obj.get(attr, default)
            return getattr(obj, attr, default)

        return {
            "distributions": distributions[:5],
            "dimension_kpis": [
                {
                    "name": _get(k, "name", ""),
                    "value": _get(k, "formatted_value", ""),
                    "status": _get(k, "status", "Derived from Dataset"),
                }
                for k in result.kpis[:5]
            ],
        }

    @staticmethod
    def _build_measure_rankings_section(result: AnalyticsResult) -> Dict[str, Any]:
        def _get(obj: Any, attr: str, default: Any = "") -> Any:
            if isinstance(obj, dict):
                return obj.get(attr, default)
            return getattr(obj, attr, default)

        rankings_list = []
        for measure, ranks in (result.rankings or {}).items():
            if not ranks:
                continue
            rankings_list.append({
                "measure": measure,
                "top_3": [
                    {
                        "rank": _get(r, "rank", 1),
                        "category": _get(r, "category", ""),
                        "value": _get(r, "value", 0.0),
                        "percentage": _get(r, "percentage", 0.0),
                    }
                    for r in ranks[:3]
                ],
            })

        return {
            "rankings": rankings_list[:3],
            "root_cause_insights": [
                {
                    "dimension": _get(rc, "dimension", ""),
                    "measure": _get(rc, "measure", ""),
                    "top_driver": _get(rc, "top_driver", ""),
                    "concentration_risk": _get(rc, "concentration_risk", ""),
                }
                for rc in result.root_causes
            ][:3],
        }

    @staticmethod
    def _build_forecast_section(result: AnalyticsResult, prediction_result: Optional[List[Any]], domain: str) -> Dict[str, Any]:
        preds = prediction_result or result.predictions or []
        pred_list = []
        for p in preds[:8]:
            if isinstance(p, dict):
                pred_list.append({
                    "model_type": p.get("model_type", "Unknown"),
                    "model_used": p.get("model_used", ""),
                    "prediction": p.get("prediction", ""),
                    "confidence": p.get("confidence", 0.0),
                    "time_horizon": p.get("time_horizon", ""),
                    "risk_level": p.get("risk_level", "LOW"),
                    "recommended_action": p.get("recommended_action", ""),
                    "metric": p.get("metric", ""),
                    "predicted_value": p.get("predicted_value", 0.0),
                    "current_value": p.get("current_value", 0.0),
                    "expected_change_pct": p.get("expected_change_pct", 0.0),
                    "model_name": p.get("model_name", p.get("model_used", "")),
                    "horizon": p.get("horizon", ""),
                    "drivers": p.get("drivers", []),
                    "time_series_points": p.get("time_series_points", []),
                    "feasible": p.get("feasible", True),
                    "limitation": p.get("limitation"),
                    "assumptions": p.get("assumptions", []),
                    "risks": p.get("risks", []),
                    "opportunities": p.get("opportunities", []),
                    "prediction_interval": p.get("prediction_interval"),
                })
            else:
                pred_list.append({
                    "model_type": getattr(p, "model_type", "Unknown"),
                    "model_used": getattr(p, "model_used", ""),
                    "prediction": getattr(p, "prediction", ""),
                    "confidence": getattr(p, "confidence", 0.0),
                    "time_horizon": getattr(p, "time_horizon", ""),
                    "risk_level": getattr(p, "risk_level", "LOW"),
                    "recommended_action": getattr(p, "recommended_action", ""),
                    "metric": getattr(p, "metric", ""),
                    "predicted_value": getattr(p, "predicted_value", 0.0),
                    "current_value": getattr(p, "current_value", 0.0),
                    "expected_change_pct": getattr(p, "expected_change_pct", 0.0),
                    "model_name": getattr(p, "model_name", getattr(p, "model_used", "")),
                    "horizon": getattr(p, "horizon", ""),
                    "drivers": getattr(p, "drivers", []),
                    "time_series_points": getattr(p, "time_series_points", []),
                    "feasible": getattr(p, "feasible", True),
                    "limitation": getattr(p, "limitation", None),
                    "assumptions": getattr(p, "assumptions", []),
                    "risks": getattr(p, "risks", []),
                    "opportunities": getattr(p, "opportunities", []),
                    "prediction_interval": getattr(p, "prediction_interval", None),
                })
        feasible = [p for p in pred_list if p.get("feasible", True)]
        strategy = result.prediction_strategy or ("Ensemble" if feasible else "none")
        limitation = result.prediction_limitation or ("No prediction limitation specified." if feasible else "Insufficient temporal data for reliable forecasting.")

        forecast_summary = {}
        if hasattr(result, "forecast_summary") and result.forecast_summary:
            forecast_summary = result.forecast_summary
        elif feasible:
            primary = feasible[0]
            pct = primary.get("expected_change_pct", 0.0) or 0.0
            forecast_summary = {
                "outlook": "Growing" if pct > 5 else "Declining" if pct < -5 else "Stable",
                "expected_change_pct": pct,
                "main_driver": "",
                "risk": primary.get("risk_level", "Low"),
                "management_action": primary.get("recommended_action", ""),
                "primary_metric": primary.get("metric", ""),
                "has_temporal_data": bool(result.trends),
                "forecast_models_count": len(pred_list),
                "feasible_forecasts_count": len(feasible),
                "model_used": primary.get("model_used", ""),
                "confidence": round(primary.get("confidence", 0.0), 2),
            }

        return {
            "total_predictions": len(pred_list),
            "feasible_predictions": len(feasible),
            "prediction_feasible": result.prediction_feasible,
            "prediction_strategy": strategy,
            "prediction_limitation": limitation,
            "predictions": pred_list,
            "forecast_summary": forecast_summary,
            "trends_available": bool(result.trends),
        }

    @staticmethod
    def _build_risks_section(result: AnalyticsResult, domain: str) -> Dict[str, Any]:
        risks = []
        for idx, r in enumerate(result.risks, 1):
            risks.append({
                "id": r.id,
                "title": r.title,
                "type": r.category,
                "severity": r.severity,
                "period": "Latest Period",
                "actual": "N/A",
                "expected": "Baseline",
                "z_score": None,
                "pct_change": 0.0,
                "explanation": r.description,
                "business_impact": r.impact,
                "possible_causes": r.causes,
                "recommendation": r.mitigation,
            })

        for a in result.anomalies[:5]:
            risks.append({
                "id": f"RSK-{len(risks)+1:03d}",
                "title": a.title,
                "type": a.type,
                "severity": a.severity,
                "period": a.period,
                "actual": a.actual_value,
                "expected": a.expected_value,
                "z_score": a.z_score,
                "pct_change": a.pct_change,
                "explanation": a.explanation,
                "business_impact": a.business_impact,
                "possible_causes": a.possible_causes,
                "recommendation": a.recommendation,
            })

        high_risks = [r for r in risks if isinstance(r, dict) and r.get("severity") in ("HIGH", "CRITICAL")]
        medium_risks = [r for r in risks if isinstance(r, dict) and r.get("severity") == "MEDIUM"]
        low_risks = [r for r in risks if isinstance(r, dict) and r.get("severity") not in ("HIGH", "CRITICAL", "MEDIUM")]

        return {
            "total_risks": len(risks),
            "high_risks": len(high_risks),
            "medium_risks": len(medium_risks),
            "low_risks": len(low_risks),
            "risk_register": risks,
            "top_5": risks[:5],
        }

    @staticmethod
    def _build_opportunities_section(result: AnalyticsResult, domain: str) -> Dict[str, Any]:
        opps = []
        confidence_result = ExplainableAIEngine.compute_confidence(
            profile=result.evidence or {},
            recommendations=result.recommendations,
        )
        opp_confidence = round(confidence_result.overall_score * 100.0, 1)
        for idx, o in enumerate(result.opportunities, 1):
            opps.append({
                "id": o.id,
                "title": o.title,
                "metric": o.category,
                "value": "N/A",
                "description": o.description,
                "confidence": opp_confidence,
                "evidence": f"{o.category} opportunity detected in {domain} analysis.",
            })

        for d in result.key_drivers:
            td = d.get("top_driver") if isinstance(d, dict) else None
            if td and not d.get("concentration_risk"):
                cat_name = td.get("category", "Top Segment") if isinstance(td, dict) else "Top Segment"
                contrib = td.get("contribution_percentage", 0.0) if isinstance(td, dict) else 0.0
                opps.append({
                    "id": f"OPP-{len(opps)+1:03d}",
                    "title": f"Expand '{cat_name}' Presence",
                    "metric": d.get("measure", "Performance"),
                    "value": f"{contrib:.1f}%",
                    "description": f"Top segment '{cat_name}' leads contribution at {contrib:.1f}%.",
                    "confidence": opp_confidence,
                    "evidence": f"Highest contributor in dimension '{d.get('dimension', 'N/A')}'",
                })

        high_opps = [o for o in opps if isinstance(o, dict) and o.get("confidence", 0) >= 80]
        medium_opps = [o for o in opps if isinstance(o, dict) and 50 <= o.get("confidence", 0) < 80]

        return {
            "total_opportunities": len(opps),
            "high_confidence": len(high_opps),
            "medium_confidence": len(medium_opps),
            "opportunity_portfolio": opps,
            "top_5": opps[:5],
        }

    @staticmethod
    def _build_recommendations_section(result: AnalyticsResult, domain: str) -> Dict[str, Any]:
        actions = []
        seen = set()

        for r in result.recommendations:
            key = r.title
            if key in seen:
                continue
            seen.add(key)
            actions.append({
                "id": r.id,
                "title": r.title,
                "priority": r.priority,
                "rationale": r.reason,
                "action": r.action,
                "confidence": f"{r.confidence:.0f}%",
                "owner": r.owner,
                "timeline": r.timeline,
                "expected_roi": r.expected_roi,
                "financial_impact": r.financial_impact,
                "investment_required": r.investment_required,
                "risk_level": r.risk_level,
                "implementation_difficulty": r.implementation_difficulty,
                "evidence": r.evidence,
                "problem": r.problem,
                "root_cause": r.root_cause,
                "business_impact": r.business_impact,
            })

        high = [a for a in actions if a.get("priority") in ("HIGH", "CRITICAL")]
        medium = [a for a in actions if a.get("priority") == "MEDIUM"]
        low = [a for a in actions if a.get("priority") not in ("HIGH", "CRITICAL", "MEDIUM")]

        return {
            "total_recommendations": len(actions),
            "high_priority": len(high),
            "medium_priority": len(medium),
            "low_priority": len(low),
            "action_plan": actions,
            "top_5": actions[:5],
        }

    @staticmethod
    def _build_evidence_section(result: AnalyticsResult) -> Dict[str, Any]:
        evidence = result.evidence or {}
        health = result.health_score if isinstance(result.health_score, HealthScore) else HealthScore()
        return {
            "confidence_score": round(result.confidence_score, 1),
            "health_breakdown": health.breakdown if hasattr(health, "breakdown") else [],
            "dataset_path": evidence.get("dataset_path", ""),
            "measures_analyzed": evidence.get("measures_analyzed", []),
            "dimensions_analyzed": evidence.get("dimensions_analyzed", []),
            "models_used": evidence.get("models_used", []),
            "traceability": evidence.get("traceability", ""),
            "errors": result.errors,
            "total_records": evidence.get("total_rows", result.volume),
            "kpis_count": len(result.kpis),
            "anomalies_count": len(result.anomalies),
            "predictions_count": len(result.predictions),
            "recommendations_count": len(result.recommendations),
        }

    @staticmethod
    def _build_charts_section(result: AnalyticsResult) -> Dict[str, Any]:
        charts = []
        chart_id = 1

        if result.trends:
            for measure, points in result.trends.items():
                if points:
                    charts.append({
                        "id": f"CHART-{chart_id:03d}",
                        "type": "line",
                        "title": f"{measure.replace('_', ' ').title()} Over Time",
                        "subtitle": "Trend analysis across temporal periods",
                        "x_axis": "Period",
                        "y_axis": measure,
                        "data_points": len(points),
                        "status": "available",
                        "spec": {
                            "measure": measure,
                            "points": [
                                {
                                    "period": p.period,
                                    "value": p.value,
                                    "change_pct": p.change_pct,
                                }
                                for p in points
                            ],
                        },
                    })
                    chart_id += 1

        if result.distributions:
            for dim, items in result.distributions.items():
                if isinstance(items, list) and items:
                    charts.append({
                        "id": f"CHART-{chart_id:03d}",
                        "type": "bar",
                        "title": f"{dim.replace('_', ' ').title()} Distribution",
                        "subtitle": "Category breakdown",
                        "x_axis": dim,
                        "y_axis": "Value",
                        "data_points": len(items),
                        "status": "available",
                        "spec": {
                            "dimension": dim,
                            "categories": [
                                {
                                    "category": it.category if hasattr(it, "category") else it.get("category", ""),
                                    "value": it.value if hasattr(it, "value") else it.get("value", 0),
                                    "percentage": it.percentage if hasattr(it, "percentage") else it.get("percentage", 0),
                                }
                                for it in items[:10]
                            ],
                        },
                    })
                    chart_id += 1

        if result.root_causes:
            for rc in result.root_causes[:3]:
                if rc.drivers:
                    charts.append({
                        "id": f"CHART-{chart_id:03d}",
                        "type": "pie",
                        "title": f"{rc.dimension.replace('_', ' ').title()} by {rc.measure.replace('_', ' ').title()}",
                        "subtitle": "Root cause driver breakdown",
                        "data_points": len(rc.drivers),
                        "status": "available",
                        "spec": {
                            "dimension": rc.dimension,
                            "measure": rc.measure,
                            "drivers": [
                                {
                                    "category": d.category,
                                    "contribution_pct": d.contribution_percentage,
                                }
                                for d in rc.drivers[:8]
                            ],
                        },
                    })
                    chart_id += 1

        if result.predictions:
            charts.append({
                "id": f"CHART-{chart_id:03d}",
                "type": "line",
                "title": "Forecast Projection",
                "subtitle": "Predictive model output",
                "x_axis": "Time Horizon",
                "y_axis": "Predicted Value",
                "data_points": len(result.predictions),
                "status": "available",
                "spec": {
                    "predictions": [
                        {
                            "model_type": p.model_type if hasattr(p, "model_type") else (p.get("model_type") if isinstance(p, dict) else "Unknown"),
                            "prediction": p.prediction if hasattr(p, "prediction") else (p.get("prediction") if isinstance(p, dict) else ""),
                            "confidence": p.confidence if hasattr(p, "confidence") else (p.get("confidence", 0.0) if isinstance(p, dict) else 0.0),
                            "time_horizon": p.time_horizon if hasattr(p, "time_horizon") else (p.get("time_horizon") if isinstance(p, dict) else ""),
                        }
                        for p in result.predictions[:5]
                    ],
                },
            })
            chart_id += 1

        if not charts:
            charts.append({
                "id": "CHART-001",
                "type": "text",
                "title": "Data Overview",
                "subtitle": "No chartable trends detected",
                "data_points": 0,
                "status": "no_data",
                "spec": {"message": "Add temporal and numeric columns to enable charting."},
            })

        return {
            "total_charts": len(charts),
            "charts": charts,
        }

    @staticmethod
    def _build_action_plan_section(result: AnalyticsResult, domain: str) -> Dict[str, Any]:
        actions_30 = []
        actions_90 = []
        actions_180 = []

        confidence_result = ExplainableAIEngine.compute_confidence(
            profile=result.evidence or {},
            recommendations=result.recommendations,
        )
        base_confidence = round(confidence_result.overall_score * 100.0, 1)

        for r in result.recommendations:
            item = {
                "title": r.title,
                "priority": r.priority,
                "confidence": r.confidence,
                "action": r.action,
                "expected_roi": r.expected_roi,
                "timeline": r.timeline,
                "owner": r.owner,
                "investment_required": r.investment_required,
            }
            timeline = (r.timeline or "").lower()
            if "30" in timeline or "immediate" in timeline or "14" in timeline or "short" in timeline or r.priority in ("CRITICAL",):
                actions_30.append(item)
            elif "90" in timeline or "medium" in timeline:
                actions_90.append(item)
            elif "180" in timeline or "long" in timeline:
                actions_180.append(item)
            else:
                if r.priority == "HIGH":
                    actions_30.append(item)
                else:
                    actions_90.append(item)

        for r in result.risks:
            if r.severity in ("CRITICAL", "HIGH"):
                actions_30.append({
                    "title": f"Mitigate: {r.title}",
                    "priority": "HIGH",
                    "confidence": base_confidence,
                    "action": r.mitigation,
                    "expected_roi": "Risk reduction",
                    "timeline": "30 days",
                    "owner": "Risk Owner",
                    "investment_required": "TBD",
                })

        if not actions_30 and not actions_90 and not actions_180:
            actions_30.append({
                "title": "Review Analytics Dashboard",
                "priority": "MEDIUM",
                "confidence": base_confidence,
                "action": "Review detailed analytics and identify top improvement areas.",
                "expected_roi": "TBD",
                "timeline": "30 days",
                "owner": "Executive Team",
                "investment_required": "None",
            })

        return {
            "next_30_days": actions_30,
            "next_90_days": actions_90,
            "next_180_days": actions_180,
            "total_actions": len(actions_30) + len(actions_90) + len(actions_180),
        }
