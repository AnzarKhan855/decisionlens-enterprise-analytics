from typing import Any, Dict, List, Optional

from app.schemas.analytics import AnalyticsResult
from app.dashboard.schema import (
    DashboardResponse,
    ExecutiveHeroCard,
    DashboardSection,
    ChartSpec,
    EvidenceCard,
    HealthCard,
)
from app.dashboard.cards import (
    build_hero_card,
    build_kpi_cards,
    build_health_card,
    build_trend_cards,
    build_root_cause_cards,
    build_prediction_cards,
    build_risk_cards,
    build_opportunity_cards,
    build_recommendation_cards,
    build_evidence_cards,
    build_chart_specs,
    build_explainability_card,
    _safe_str,
)
from app.dashboard.layout import build_sections


class UniversalDashboardStoryteller:
    """
    Universal Dashboard Storytelling Engine.

    Transforms AnalyticsResult + PredictionResult + ExecutiveReport
    into a single unified DashboardResponse that answers the four
    executive questions for ANY industry domain.

    This is the ONLY entry point for dashboard generation.
    All dashboard views MUST flow through this engine.
    """

    @classmethod
    def generate(
        cls,
        analytics_result: AnalyticsResult,
        prediction_result: Optional[List[Any]] = None,
        executive_report: Optional[Dict[str, Any]] = None,
        parquet_path: Optional[Any] = None,
        profile: Optional[Dict[str, Any]] = None,
        dataset_id: str = "latest",
        workspace_id: str = "",
        sql_query: str = "",
        tables_used: List[str] = None,
        columns_used: List[str] = None,
        evidence_items: List[str] = None,
        rows_returned: int = 0,
    ) -> DashboardResponse:
        analytics_dict = analytics_result.to_dict() if hasattr(analytics_result, "to_dict") else analytics_result
        if not analytics_dict:
            analytics_dict = {}

        domain = _safe_str(analytics_dict.get("domain", "Generic Business"), "Generic Business")
        dataset_type = _safe_str(analytics_dict.get("dataset_type", "Unknown Dataset"), "Unknown Dataset")
        total_records = analytics_dict.get("volume", 0) or 0
        total_columns = 0
        if profile:
            total_columns = profile.get("total_columns", 0) or 0

        tables_used = tables_used or []
        columns_used = columns_used or []
        evidence_items = evidence_items or []

        kpis_raw = analytics_dict.get("kpis", []) or []
        kpi_measures = []
        for k in kpis_raw:
            src = k.get("source_column") if isinstance(k, dict) else getattr(k, "source_column", None)
            if src and src != "*":
                kpi_measures.append(src)

        hero = build_hero_card(
            domain=domain,
            dataset_type=dataset_type,
            dataset_id=dataset_id,
            workspace_id=workspace_id,
            total_records=total_records,
            total_columns=total_columns,
            analytics_dict=analytics_dict,
        )

        kpi_cards = build_kpi_cards(kpis_raw, total_records)
        health_card = build_health_card(analytics_dict)
        trend_cards = build_trend_cards(analytics_dict.get("trends", {}) or {})
        root_cause_cards = build_root_cause_cards(analytics_dict.get("root_causes", []) or [])
        prediction_cards = build_prediction_cards(prediction_result or analytics_dict.get("predictions", []) or [])
        risk_cards = build_risk_cards(analytics_dict.get("risks", []) or [])
        opportunity_cards = build_opportunity_cards(analytics_dict.get("opportunities", []) or [])
        recommendation_cards = build_recommendation_cards(analytics_dict.get("recommendations", []) or [])
        evidence_cards = build_evidence_cards(
            sql_query=sql_query or "",
            tables_used=tables_used,
            columns_used=columns_used,
            rows_returned=rows_returned if rows_returned is not None else 0,
            evidence_items=evidence_items,
        )

        anomaly_cards = cls._build_anomaly_cards(analytics_dict.get("anomalies", []) or [])
        segment_cards = cls._build_segment_cards(
            analytics_dict.get("segment_comparisons", []) or [],
            analytics_dict.get("rankings", {}) or {},
            analytics_dict.get("root_causes", []) or [],
        )
        insight_cards = cls._build_insight_cards(
            analytics_dict,
            kpi_cards,
            trend_cards,
            anomaly_cards,
            root_cause_cards,
        )
        forecast_cards = prediction_cards[:1] if prediction_cards else []

        charts: List[ChartSpec] = []
        canonical_charts = analytics_dict.get("charts", []) or []
        if canonical_charts:
            try:
                charts = build_chart_specs(canonical_charts, profile, kpi_measures=kpi_measures)
            except Exception as e:
                charts = []
        elif profile and parquet_path:
            try:
                from app.analytics.chart_engine import ChartEngine
                from pathlib import Path
                raw_charts = ChartEngine.generate_from_parquet(Path(str(parquet_path)), profile)
                charts = build_chart_specs(raw_charts or [], profile, kpi_measures=kpi_measures)
            except Exception as e:
                charts = []

        sections = build_sections(
            kpi_cards=kpi_cards,
            health_card=health_card,
            trend_cards=trend_cards,
            root_cause_cards=root_cause_cards,
            prediction_cards=prediction_cards,
            risk_cards=risk_cards,
            opportunity_cards=opportunity_cards,
            recommendation_cards=recommendation_cards,
            charts=charts,
            evidence_cards=evidence_cards,
            analytics_dict=analytics_dict,
            anomaly_cards=anomaly_cards,
            segment_cards=segment_cards,
            insight_cards=insight_cards,
            forecast_cards=forecast_cards,
        )

        explainability_card = build_explainability_card(analytics_dict)

        intelligence = {
            "domain": domain,
            "entities": analytics_dict.get("entities", []) or [],
            "measures": analytics_dict.get("measures", []) or [],
            "dimensions": analytics_dict.get("dimensions", []) or [],
            "capability_matrix": analytics_dict.get("capability_matrix", {}) or {},
            "detection_panel": analytics_dict.get("detection_panel", {}) or {},
            "business_questions": analytics_dict.get("business_questions", []) or [],
        }

        prediction_list = prediction_result or analytics_dict.get("predictions", []) or []
        pred_dicts = []
        for p in prediction_list:
            pred_dicts.append(p.to_dict() if hasattr(p, "to_dict") else (p.__dict__ if hasattr(p, "__dict__") else dict(p)))

        forecast_summary = analytics_dict.get("forecast_summary", {}) or {}
        if not forecast_summary and pred_dicts:
            primary = pred_dicts[0]
            pct = primary.get("expected_change_pct", 0.0) or 0.0
            forecast_summary = {
                "outlook": "Growing" if pct > 5 else "Declining" if pct < -5 else "Stable",
                "expected_change_pct": pct,
                "main_driver": "",
                "risk": primary.get("risk_level", "Low") or "Low",
                "management_action": primary.get("recommended_action", "") or "Continue monitoring key metrics.",
                "primary_metric": primary.get("metric", "") or "",
                "has_temporal_data": bool(analytics_dict.get("trends")),
                "forecast_models_count": len(pred_dicts),
                "feasible_forecasts_count": sum(1 for p in pred_dicts if p.get("feasible", False)),
                "model_used": primary.get("model_used", ""),
                "confidence": round(primary.get("confidence", 0.0), 2),
            }

        return DashboardResponse(
            generated_at=_safe_str(analytics_dict.get("generated_at", ""), ""),
            domain=domain,
            dataset_type=dataset_type,
            dataset_id=dataset_id,
            workspace_id=workspace_id,
            total_records=total_records if total_records is not None else 0,
            total_columns=total_columns if total_columns is not None else 0,
            hero=hero,
            sections=sections,
            kpi_cards=kpi_cards,
            kpis=[k.model_dump() if hasattr(k, "model_dump") else (k.__dict__ if hasattr(k, "__dict__") else dict(k)) for k in kpi_cards],
            health_card=health_card,
            charts=charts,
            evidence=evidence_cards,
            copilot_suggestion=cls._build_copilot_suggestion(analytics_dict),
            errors=analytics_dict.get("errors", []) or [],
            predictions=pred_dicts,
            ml_forecast=pred_dicts,
            ml_segmentation=analytics_dict.get("segment_comparisons", []) or [],
            explainability=explainability_card,
            intelligence=intelligence,
            forecast_summary=forecast_summary,
        )

    @staticmethod
    def _build_anomaly_cards(anomalies: List[Any]) -> List[Dict[str, Any]]:
        cards = []
        for a in anomalies:
            if hasattr(a, "__dict__"):
                adict = a.__dict__
            else:
                adict = dict(a) if not isinstance(a, dict) else a
            cards.append({
                "id": _safe_str(adict.get("id", adict.get("period", f"ANOMALY-{len(cards)+1}")), f"ANOMALY-{len(cards)+1}"),
                "title": _safe_str(adict.get("title", adict.get("category", "Anomaly Detected")), "Anomaly Detected"),
                "category": _safe_str(adict.get("category", "General"), "General"),
                "severity": _safe_str(adict.get("severity", "MEDIUM"), "MEDIUM"),
                "description": _safe_str(adict.get("explanation", adict.get("description", "")), ""),
                "impact": _safe_str(adict.get("business_impact", ""), ""),
                "actual_value": adict.get("actual_value", 0),
                "expected_value": adict.get("expected_value", 0),
                "z_score": adict.get("z_score", 0),
                "period": _safe_str(adict.get("period", ""), ""),
                "metric": _safe_str(adict.get("category", ""), ""),
            })
        return cards

    @staticmethod
    def _build_segment_cards(
        segment_comparisons: List[Any],
        rankings: Dict[str, Any],
        root_causes: List[Any],
    ) -> List[Dict[str, Any]]:
        cards: List[Dict[str, Any]] = []

        for sc in segment_comparisons:
            if hasattr(sc, "__dict__"):
                sdict = sc.__dict__
            else:
                sdict = dict(sc) if not isinstance(sc, dict) else sc
            cards.append({
                "id": _safe_str(sdict.get("id", f"SEG-{len(cards)+1}"), f"SEG-{len(cards)+1}"),
                "type": "segment_comparison",
                "title": f"{_safe_str(sdict.get('metric', 'Metric'), 'Metric')} Comparison: {_safe_str(sdict.get('segment_a', ''), '')} vs {_safe_str(sdict.get('segment_b', ''), '')}",
                "segment_a": _safe_str(sdict.get("segment_a", ""), ""),
                "segment_b": _safe_str(sdict.get("segment_b", ""), ""),
                "metric": _safe_str(sdict.get("metric", ""), ""),
                "value_a": sdict.get("value_a", 0),
                "value_b": sdict.get("value_b", 0),
                "difference_pct": sdict.get("difference_pct", 0),
                "winner": _safe_str(sdict.get("winner", ""), ""),
                "description": f"{_safe_str(sdict.get('winner', ''), '')} leads in {_safe_str(sdict.get('metric', ''), '')} by {abs(sdict.get('difference_pct', 0) or 0):.1f}%.",
            })

        for dim, items in rankings.items():
            if not items or len(items) < 2:
                continue
            top = items[0]
            bottom = items[-1]
            cards.append({
                "id": _safe_str(f"RANK-{dim}", f"RANK-{dim}"),
                "type": "ranking",
                "title": f"{dim.replace('_', ' ').title()} Rankings",
                "dimension": dim,
                "top": {
                    "category": _safe_str(getattr(top, "category", str(top)), ""),
                    "value": getattr(top, "value", 0),
                    "percentage": getattr(top, "percentage", None),
                },
                "bottom": {
                    "category": _safe_str(getattr(bottom, "category", str(bottom)), ""),
                    "value": getattr(bottom, "value", 0),
                    "percentage": getattr(bottom, "percentage", None),
                },
                "description": f"Top segment: {_safe_str(getattr(top, 'category', ''), '')}. Bottom segment: {_safe_str(getattr(bottom, 'category', ''), '')}.",
            })

        for rc in root_causes:
            if hasattr(rc, "__dict__"):
                rdict = rc.__dict__
            else:
                rdict = dict(rc) if not isinstance(rc, dict) else rc
            td = rdict.get("top_driver")
            if td and hasattr(td, "__dict__"):
                td = td.__dict__
            elif td and not isinstance(td, dict):
                td = dict(td)
            if td:
                cards.append({
                    "id": _safe_str(f"ROOT-{rdict.get('dimension', 'unknown')}", f"ROOT-{rdict.get('dimension', 'unknown')}"),
                    "type": "root_cause_summary",
                    "title": f"Key Driver: {_safe_str(rdict.get('measure', ''), '')} by {_safe_str(rdict.get('dimension', ''), '')}",
                    "dimension": _safe_str(rdict.get("dimension", ""), ""),
                    "measure": _safe_str(rdict.get("measure", ""), ""),
                    "top_driver": td,
                    "concentration_risk": bool(rdict.get("concentration_risk", False)),
                    "description": f"{_safe_str(td.get('category', ''), '')} contributes {td.get('contribution_percentage', 0)}% to {_safe_str(rdict.get('measure', ''), '')}.",
                })

        return cards

    @staticmethod
    def _build_insight_cards(
        analytics_dict: Dict[str, Any],
        kpi_cards: List[Any],
        trend_cards: List[Any],
        anomaly_cards: List[Any],
        root_cause_cards: List[Any],
    ) -> List[Dict[str, Any]]:
        insights: List[Dict[str, Any]] = []
        domain = _safe_str(analytics_dict.get("domain", "Generic Business"), "Generic Business")

        critical_findings = analytics_dict.get("critical_findings", []) or []
        positive_findings = analytics_dict.get("positive_findings", []) or []
        negative_findings = analytics_dict.get("negative_findings", []) or []

        for i, f in enumerate(critical_findings[:3], 1):
            if isinstance(f, str):
                insights.append({
                    "id": f"INSIGHT-CRITICAL-{i}",
                    "type": "critical",
                    "title": f"Critical Finding {i}",
                    "description": f,
                    "severity": "CRITICAL",
                })
            elif isinstance(f, dict):
                insights.append({
                    "id": _safe_str(f.get("id", f"INSIGHT-CRITICAL-{i}"), f"INSIGHT-CRITICAL-{i}"),
                    "type": "critical",
                    "title": _safe_str(f.get("title", f.get("category", f"Critical Finding {i}")), f"Critical Finding {i}"),
                    "description": _safe_str(f.get("description", f.get("explanation", "")), ""),
                    "severity": "CRITICAL",
                })

        for i, f in enumerate(negative_findings[:2], len(insights) + 1):
            if isinstance(f, str):
                insights.append({
                    "id": f"INSIGHT-WARN-{i}",
                    "type": "warning",
                    "title": f"Warning {i}",
                    "description": f,
                    "severity": "HIGH",
                })
            elif isinstance(f, dict):
                insights.append({
                    "id": _safe_str(f.get("id", f"INSIGHT-WARN-{i}"), f"INSIGHT-WARN-{i}"),
                    "type": "warning",
                    "title": _safe_str(f.get("title", f.get("category", f"Warning {i}")), f"Warning {i}"),
                    "description": _safe_str(f.get("description", f.get("explanation", "")), ""),
                    "severity": "HIGH",
                })

        for i, f in enumerate(positive_findings[:2], len(insights) + 1):
            if isinstance(f, str):
                insights.append({
                    "id": f"INSIGHT-POS-{i}",
                    "type": "positive",
                    "title": f"Positive Signal {i}",
                    "description": f,
                    "severity": "LOW",
                })
            elif isinstance(f, dict):
                insights.append({
                    "id": _safe_str(f.get("id", f"INSIGHT-POS-{i}"), f"INSIGHT-POS-{i}"),
                    "type": "positive",
                    "title": _safe_str(f.get("title", f.get("category", f"Positive Signal {i}")), f"Positive Signal {i}"),
                    "description": _safe_str(f.get("description", f.get("explanation", "")), ""),
                    "severity": "LOW",
                })

        if trend_cards and not insights:
            top_trend = trend_cards[0]
            insights.append({
                "id": "INSIGHT-TREND-1",
                "type": "info",
                "title": f"{top_trend.measure.replace('_', ' ').title()} Trend",
                "description": f"{top_trend.measure.replace('_', ' ').title()} shows a {top_trend.direction} trend across {top_trend.data_points} periods.",
                "severity": "INFO",
            })

        if anomaly_cards and not insights:
            top_anomaly = anomaly_cards[0]
            insights.append({
                "id": "INSIGHT-ANOMALY-1",
                "type": "warning",
                "title": _safe_str(top_anomaly.get("title", "Anomaly Detected"), "Anomaly Detected"),
                "description": _safe_str(top_anomaly.get("description", ""), ""),
                "severity": "HIGH",
            })

        return insights

    @classmethod
    def _build_copilot_suggestion(cls, analytics_dict: Dict[str, Any]) -> str:
        domain = _safe_str(analytics_dict.get("domain", "Generic Business"), "Generic Business")
        anomalies = analytics_dict.get("anomalies", []) or []
        recommendations = analytics_dict.get("recommendations", []) or []
        predictions = analytics_dict.get("predictions", []) or []

        parts = [f"Ask about {domain} performance trends, key drivers, and strategic actions."]
        if anomalies:
            parts.append(f"Review {len(anomalies)} detected anomaly/anomalies.")
        if recommendations:
            parts.append(f"Explore {len(recommendations)} executive recommendation(s).")
        if predictions:
            parts.append(f"Analyze {len(predictions)} prediction model(s).")
        return " ".join(parts)
