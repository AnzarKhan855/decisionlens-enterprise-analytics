import math
from typing import Any, Dict, List, Optional

from app.dashboard.schema import (
    KPICard,
    HealthCard,
    TrendCard,
    RootCauseCard,
    PredictionCard,
    RiskCard,
    OpportunityCard,
    RecommendationCard,
    EvidenceCard,
    ExecutiveHeroCard,
    ChartSpec,
    ExplainabilityCard,
)


def _safe_str(val: Any, fallback: str = "N/A") -> str:
    if val is None:
        return fallback
    if isinstance(val, float):
        if math.isnan(val) or math.isinf(val):
            return fallback
        if val == 0.0:
            return "0"
    if isinstance(val, str):
        stripped = val.strip().lower()
        if stripped in ("undefined", "unknown", "null", "nan", "none", "na", ""):
            return fallback
    return str(val)


def _safe_float(val: Any, fallback: float = 0.0) -> float:
    if val is None:
        return fallback
    if isinstance(val, float):
        if math.isnan(val) or math.isinf(val):
            return fallback
        if val == 0.0:
            return 0.0
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return fallback
        if f == 0.0:
            return 0.0
        return f
    except (TypeError, ValueError):
        return fallback


def _get_val(obj: Any, attr: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


def _is_genuine_zero(val: Any) -> bool:
    if val is None:
        return False
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return False
    try:
        f = float(val)
        return f == 0.0 and not math.isnan(f) and not math.isinf(f)
    except (TypeError, ValueError):
        return False


def _kpi_display_value(k: Dict[str, Any] | Any, total_rows: int) -> tuple[str, str, bool]:
    raw_value = None
    formatted_value = None
    available = True

    if isinstance(k, dict):
        raw_value = k.get("value", None)
        formatted_value = k.get("formatted_value", None)
        available = k.get("available", True)
    else:
        raw_value = getattr(k, "value", None)
        formatted_value = getattr(k, "formatted_value", None)
        available = getattr(k, "available", True)

    if not available:
        return "N/A", "Calculation Disabled", False

    if formatted_value and _safe_str(formatted_value) != "N/A":
        display = _safe_str(formatted_value)
        if _safe_str(display) == "0" and not _is_genuine_zero(raw_value):
            return _safe_str(raw_value), _safe_str(raw_value), True
        return display, display, True

    if _is_genuine_zero(raw_value):
        return "0", "0", True

    return _safe_str(raw_value), _safe_str(raw_value), True


def build_hero_card(
    domain: str,
    dataset_type: str,
    dataset_id: str,
    workspace_id: str,
    total_records: int,
    total_columns: int,
    analytics_dict: Dict[str, Any],
) -> ExecutiveHeroCard:
    health_score = analytics_dict.get("health_score", {})
    if isinstance(health_score, dict):
        hs_val = _safe_float(health_score.get("overall_score", 0.0))
        hs_status = _safe_str(health_score.get("status", "No Data"), "No Data")
    else:
        hs_val = _safe_float(getattr(health_score, "overall_score", 0.0))
        hs_status = _safe_str(getattr(health_score, "status", "No Data"), "No Data")

    kpis = analytics_dict.get("kpis", []) or []
    primary_kpi = kpis[0] if kpis else {}
    if isinstance(primary_kpi, dict):
        primary_kpi_name = _safe_str(primary_kpi.get("name", "N/A"), "N/A")
        raw_pk_val = primary_kpi.get("value", "N/A")
        primary_kpi_value = _safe_str(raw_pk_val, "N/A")
        if primary_kpi_value == "N/A" and primary_kpi.get("formatted_value"):
            primary_kpi_value = _safe_str(primary_kpi.get("formatted_value"), "N/A")
    else:
        primary_kpi_name = _safe_str(getattr(primary_kpi, "name", "N/A"), "N/A")
        raw_pk_val = getattr(primary_kpi, "value", "N/A")
        primary_kpi_value = _safe_str(raw_pk_val, "N/A")
        if primary_kpi_value == "N/A" and getattr(primary_kpi, "formatted_value", None):
            primary_kpi_value = _safe_str(getattr(primary_kpi, "formatted_value"), "N/A")

    if primary_kpi_value in ("N/A", "undefined", "Unknown", "Null", "None", "", "unavailable"):
        primary_kpi_value = "Awaiting Analysis"

    anomalies = analytics_dict.get("anomalies", []) or []
    recommendations = analytics_dict.get("recommendations", []) or []
    predictions = analytics_dict.get("predictions", []) or []
    confidence_score = _safe_float(analytics_dict.get("confidence_score", 0.0))

    forecast = _safe_str(analytics_dict.get("prediction_strategy", "time_series_forecasting"), "time_series_forecasting")
    if not forecast or forecast.lower() in ("none", "null", "undefined"):
        forecast = "time_series_forecasting"

    return ExecutiveHeroCard(
        greeting=f"{domain} Executive Briefing",
        domain=domain,
        dataset_type=dataset_type,
        total_records=total_records if total_records is not None else 0,
        total_columns=total_columns if total_columns is not None else 0,
        health_score=hs_val,
        health_status=hs_status,
        primary_kpi=primary_kpi_name,
        primary_kpi_value=primary_kpi_value,
        anomaly_count=len(anomalies),
        recommendation_count=len(recommendations),
        prediction_count=len(predictions),
        ai_confidence=f"{confidence_score:.0f}%",
        forecast=forecast,
    )


def build_kpi_cards(kpis: List[Any], total_rows: int) -> List[KPICard]:
    cards = []
    for k in kpis:
        display_value, display_formatted, is_valid = _kpi_display_value(k, total_rows)
        if isinstance(k, dict):
            raw_val = k.get("value", None)
            change_pct = k.get("change_pct")
            comparison_period = k.get("comparison_period", "")
            data_source = k.get("data_source", "")
            trend_value = k.get("trend_value", "")
            if isinstance(change_pct, float) and (math.isnan(change_pct) or math.isinf(change_pct)):
                change_pct = None
            cards.append(KPICard(
                name=_safe_str(k.get("name", "Unknown"), "Unknown"),
                value=display_value,
                formatted_value=display_formatted,
                metric_type=_safe_str(k.get("metric_type", "Unknown"), "Unknown"),
                source_column=_safe_str(k.get("source_column", ""), ""),
                formula=_safe_str(k.get("formula", ""), ""),
                rows_analyzed=k.get("rows_analyzed", total_rows) or total_rows,
                confidence=_safe_float(k.get("confidence", 0.0)),
                available=k.get("available", True),
                status=_safe_str(k.get("status", "Derived from Dataset"), "Derived from Dataset"),
                insight=_safe_str(k.get("insight", ""), ""),
                trend_value=_safe_str(trend_value, ""),
                change_pct=change_pct,
                comparison_period=_safe_str(comparison_period, ""),
                data_source=_safe_str(data_source, ""),
            ))
        else:
            raw_val = getattr(k, "value", None)
            change_pct = getattr(k, "change_pct", None)
            comparison_period = getattr(k, "comparison_period", "") or ""
            data_source = getattr(k, "data_source", "") or ""
            trend_value = getattr(k, "trend_value", "") or ""
            if isinstance(change_pct, float) and (math.isnan(change_pct) or math.isinf(change_pct)):
                change_pct = None
            cards.append(KPICard(
                name=_safe_str(getattr(k, "name", "Unknown"), "Unknown"),
                value=display_value,
                formatted_value=display_formatted,
                metric_type=_safe_str(getattr(k, "metric_type", "Unknown"), "Unknown"),
                source_column=_safe_str(getattr(k, "source_column", ""), ""),
                formula=_safe_str(getattr(k, "formula", ""), ""),
                rows_analyzed=getattr(k, "rows_analyzed", total_rows) or total_rows,
                confidence=_safe_float(getattr(k, "confidence", 0.0)),
                available=getattr(k, "available", True),
                status=_safe_str(getattr(k, "status", "Derived from Dataset"), "Derived from Dataset"),
                insight=_safe_str(getattr(k, "insight", ""), ""),
                trend_value=_safe_str(trend_value, ""),
                change_pct=change_pct,
                comparison_period=_safe_str(comparison_period, ""),
                data_source=_safe_str(data_source, ""),
            ))
    return cards


def build_health_card(analytics_dict: Dict[str, Any]) -> Optional[HealthCard]:
    health_score = analytics_dict.get("health_score")
    if not health_score:
        return HealthCard(
            overall_score=0.0,
            grade="N/A",
            status="No Data",
            breakdown=[],
        )
    if isinstance(health_score, dict):
        return HealthCard(
            overall_score=_safe_float(health_score.get("overall_score", 0.0)),
            grade=_safe_str(health_score.get("grade", "N/A"), "N/A"),
            status=_safe_str(health_score.get("status", "No Data"), "No Data"),
            breakdown=health_score.get("breakdown", []) or [],
        )
    return HealthCard(
        overall_score=_safe_float(getattr(health_score, "overall_score", 0.0)),
        grade=_safe_str(getattr(health_score, "grade", "N/A"), "N/A"),
        status=_safe_str(getattr(health_score, "status", "No Data"), "No Data"),
        breakdown=getattr(health_score, "breakdown", []) or [],
    )


def build_trend_cards(trends: Dict[str, List[Any]]) -> List[TrendCard]:
    cards = []
    if not trends:
        return cards
    for measure, points in trends.items():
        if not points:
            continue
        vals = [float(_get_val(p, "value")) for p in points if _safe_float(_get_val(p, "value")) is not None]
        if not vals:
            continue
        up = sum(1 for p in points if _safe_float(_get_val(p, "change_pct")) > 0)
        down = sum(1 for p in points if _safe_float(_get_val(p, "change_pct")) < 0)
        latest = points[-1]
        latest_val = _safe_float(_get_val(latest, "value"), 0.0)
        chart_data = [
            {"period": _safe_str(_get_val(p, "period"), ""), "value": _safe_float(_get_val(p, "value"), 0.0)}
            for p in points
        ]
        cards.append(TrendCard(
            measure=_safe_str(measure, "Unknown"),
            data_points=len(points),
            latest_value=latest_val,
            latest_change_pct=_safe_float(getattr(latest, "change_pct", None)),
            direction="upward" if up > down else "downward" if down > up else "stable",
            up_periods=up,
            down_periods=down,
            chart_data=chart_data,
        ))
    return cards


def build_root_cause_cards(root_causes: List[Any]) -> List[RootCauseCard]:
    cards = []
    if not root_causes:
        return cards
    for rc in root_causes:
        rc_dict = rc.__dict__ if hasattr(rc, "__dict__") else (dict(rc) if not isinstance(rc, dict) else rc)
        drivers = []
        for d in rc_dict.get("drivers", []):
            drivers.append(d.__dict__ if hasattr(d, "__dict__") else (dict(d) if not isinstance(d, dict) else d))
        top_driver = rc_dict.get("top_driver")
        if top_driver and hasattr(top_driver, "__dict__"):
            top_driver = top_driver.__dict__
        elif top_driver and not isinstance(top_driver, dict):
            top_driver = dict(top_driver)
        cards.append(RootCauseCard(
            dimension=_safe_str(rc_dict.get("dimension", ""), ""),
            measure=_safe_str(rc_dict.get("measure", ""), ""),
            grand_total=_safe_float(rc_dict.get("grand_total", 0)),
            top_driver=top_driver,
            concentration_risk=bool(rc_dict.get("concentration_risk", False)),
            driver_count=len(rc_dict.get("drivers", [])),
            drivers=drivers,
        ))
    return cards


def build_prediction_cards(predictions: List[Any]) -> List[PredictionCard]:
    cards = []
    if not predictions:
        return cards
    for p in predictions:
        if hasattr(p, "__dict__"):
            pdict = p.__dict__
        else:
            pdict = dict(p) if not isinstance(p, dict) else p
        scenarios = []
        risks = pdict.get("risks", []) or []
        opportunities = pdict.get("opportunities", []) or []
        if risks:
            scenarios.append({"type": "worst_case", "description": "; ".join(r for r in risks if r)})
        if opportunities:
            scenarios.append({"type": "best_case", "description": "; ".join(o for o in opportunities if o)})
        if not scenarios:
            pred_text = _safe_str(pdict.get("prediction", ""), "")
            scenarios.append({"type": "most_likely", "description": pred_text})
        drivers = pdict.get("drivers", []) or []
        if not drivers:
            drivers = [{"name": "Empirical record distribution", "impact": "Moderate"}]
        cards.append(PredictionCard(
            model_type=_safe_str(pdict.get("model_type", "Unknown"), "Unknown"),
            model_used=_safe_str(pdict.get("model_used", ""), ""),
            prediction=_safe_str(pdict.get("prediction", ""), ""),
            confidence=_safe_float(pdict.get("confidence", 0.0)),
            evidence=_safe_str(pdict.get("evidence", ""), ""),
            business_impact=_safe_str(pdict.get("business_impact", ""), ""),
            time_horizon=_safe_str(pdict.get("time_horizon", ""), ""),
            risk_level=_safe_str(pdict.get("risk_level", "MEDIUM"), "MEDIUM"),
            recommended_action=_safe_str(pdict.get("recommended_action", ""), ""),
            feasible=pdict.get("feasible", True),
            limitation=_safe_str(pdict.get("limitation"), None) if pdict.get("limitation") else None,
            scenarios=scenarios,
            metric=_safe_str(pdict.get("metric", ""), ""),
            predicted_value=_safe_float(pdict.get("predicted_value", 0.0)),
            current_value=_safe_float(pdict.get("current_value", 0.0)),
            expected_change_pct=_safe_float(pdict.get("expected_change_pct", 0.0)),
            model_name=_safe_str(pdict.get("model_name", pdict.get("model_used", "")), ""),
            horizon=_safe_str(pdict.get("horizon", ""), ""),
            drivers=drivers,
            time_series_points=pdict.get("time_series_points", []) or [],
        ))
    return cards


def build_risk_cards(risks: List[Any]) -> List[RiskCard]:
    cards = []
    if not risks:
        return cards
    for r in risks:
        if hasattr(r, "__dict__"):
            rdict = r.__dict__
        else:
            rdict = dict(r) if not isinstance(r, dict) else r
        causes = rdict.get("causes", [])
        if isinstance(causes, str):
            causes = [causes]
        cards.append(RiskCard(
            id=_safe_str(rdict.get("id", f"RISK-{len(cards)+1}"), f"RISK-{len(cards)+1}"),
            title=_safe_str(rdict.get("title", "Unknown Risk"), "Unknown Risk"),
            category=_safe_str(rdict.get("category", "General"), "General"),
            severity=_safe_str(rdict.get("severity", "LOW"), "LOW"),
            description=_safe_str(rdict.get("description", ""), ""),
            impact=_safe_str(rdict.get("impact", ""), ""),
            causes=[_safe_str(c, "") for c in (causes or [])],
            mitigation=_safe_str(rdict.get("mitigation", ""), ""),
        ))
    return cards


def build_opportunity_cards(opportunities: List[Any]) -> List[OpportunityCard]:
    cards = []
    if not opportunities:
        return cards
    for o in opportunities:
        if hasattr(o, "__dict__"):
            odict = o.__dict__
        else:
            odict = dict(o) if not isinstance(o, dict) else o
        cards.append(OpportunityCard(
            id=_safe_str(odict.get("id", f"OPP-{len(cards)+1}"), f"OPP-{len(cards)+1}"),
            title=_safe_str(odict.get("title", "Unknown Opportunity"), "Unknown Opportunity"),
            category=_safe_str(odict.get("category", "General"), "General"),
            priority=_safe_str(odict.get("priority", "MEDIUM"), "MEDIUM"),
            description=_safe_str(odict.get("description", ""), ""),
            impact=_safe_str(odict.get("impact", ""), ""),
            action=_safe_str(odict.get("action", ""), ""),
            timeline=_safe_str(odict.get("timeline", "90 Days"), "90 Days"),
        ))
    return cards


def build_recommendation_cards(recommendations: List[Any]) -> List[RecommendationCard]:
    cards = []
    if not recommendations:
        return cards
    for r in recommendations:
        if hasattr(r, "__dict__"):
            rdict = r.__dict__
        else:
            rdict = dict(r) if not isinstance(r, dict) else r
        title = _safe_str(rdict.get("title", rdict.get("action", "Unknown Action")), "Unknown Action")
        if title.lower() in ("undefined", "unknown", "null", "nan", ""):
            title = _safe_str(rdict.get("action", "Unknown Action"), "Unknown Action")
        cards.append(RecommendationCard(
            id=_safe_str(rdict.get("id", f"REC-{len(cards)+1}"), f"REC-{len(cards)+1}"),
            title=title,
            category=_safe_str(rdict.get("category", "Strategy"), "Strategy"),
            priority=_safe_str(rdict.get("priority", "MEDIUM"), "MEDIUM"),
            reason=_safe_str(rdict.get("reason", rdict.get("business_rationale", "")), ""),
            action=_safe_str(rdict.get("action", ""), ""),
            expected_roi=_safe_str(rdict.get("expected_roi", "Empirical ROI"), "Empirical ROI"),
            financial_impact=_safe_str(rdict.get("financial_impact", "Estimated from dataset metrics"), "Estimated from dataset metrics"),
            investment_required=_safe_str(rdict.get("investment_required", "Data-driven estimate"), "Data-driven estimate"),
            timeline=_safe_str(rdict.get("timeline", "30 Days"), "30 Days"),
            confidence=_safe_float(rdict.get("confidence", 0.0)),
            risk_level=_safe_str(rdict.get("risk_level", "LOW"), "LOW"),
            owner=_safe_str(rdict.get("owner", "Data Team"), "Data Team"),
            implementation_difficulty=_safe_str(rdict.get("implementation_difficulty", "Medium"), "Medium"),
            evidence=_safe_str(rdict.get("evidence", ""), ""),
        ))
    return cards


def build_evidence_cards(
    sql_query: str,
    tables_used: List[str],
    columns_used: List[str],
    rows_returned: int,
    evidence_items: List[str],
    confidence: float = 0.9,
) -> List[EvidenceCard]:
    if not evidence_items:
        evidence_items = [sql_query] if sql_query else ["No SQL evidence captured for this analysis."]
    return [
        EvidenceCard(
            source="duckdb_sql",
            query=sql_query or "N/A",
            rows_returned=rows_returned if rows_returned is not None else 0,
            columns_used=columns_used or [],
            tables_used=tables_used or [],
            snippet=_safe_str(evidence_items[0], ""),
            confidence=_safe_float(confidence),
        )
    ]


def build_chart_specs(
    charts: List[Dict[str, Any]],
    profile: Dict[str, Any],
    kpi_measures: Optional[List[str]] = None,
) -> List[ChartSpec]:
    specs = []
    if not charts:
        return specs

    col_categories = (profile or {}).get("column_categories", {})
    available_measures = set(kpi_measures or col_categories.get("measures", []) or [])
    available_dimensions = set(col_categories.get("dimensions", []) or [])

    for c in charts:
        if not isinstance(c, dict):
            continue
        if not c.get("available", True):
            continue

        chart_type = _safe_str(c.get("type", "chart"), "bar")
        title = _safe_str(c.get("title", "Untitled Chart"), "Untitled Chart")
        business_interpretation = c.get("business_interpretation", "")
        if not business_interpretation or business_interpretation.lower() in ("undefined", "unknown", "null", "nan", ""):
            business_interpretation = f"Visualizes {title.lower()} to support executive decision-making."

        source_col = _safe_str(c.get("source_column", ""), "")
        dimension_col = _safe_str(c.get("dimension_column", ""), "")
        x_axis = _safe_str(c.get("x_axis", dimension_col or source_col), dimension_col or source_col)
        y_axis = _safe_str(c.get("y_axis", source_col), source_col)
        x_field = _safe_str(c.get("x_field", x_axis), x_axis)
        y_field = _safe_str(c.get("y_field", y_axis), y_axis)

        if available_measures and source_col and source_col not in available_measures and y_axis not in available_measures:
            y_axis = list(available_measures)[0] if available_measures else y_axis
        if available_dimensions and dimension_col and dimension_col not in available_dimensions and x_axis not in available_dimensions:
            x_axis = list(available_dimensions)[0] if available_dimensions else x_axis

        chart_confidence = c.get("confidence", 0.9)
        if not isinstance(chart_confidence, (int, float)) or _safe_float(chart_confidence) != chart_confidence:
            chart_confidence = 0.9
        chart_confidence = max(0.0, min(1.0, float(chart_confidence)))

        required_columns = c.get("required_columns", []) or []
        if not isinstance(required_columns, list):
            required_columns = []

        chart_data = c.get("data", []) or []
        if not isinstance(chart_data, list):
            chart_data = []

        canonical_data = []
        for d in chart_data:
            if not isinstance(d, dict):
                continue
            label = _safe_str(d.get("label") or d.get("x_field") or d.get("category") or d.get("period", ""), "")
            raw_value = d.get("value") or d.get("y_field")
            if label and raw_value is not None:
                try:
                    val = float(raw_value)
                    if math.isnan(val) or math.isinf(val):
                        continue
                    canonical_data.append({
                        "label": label,
                        "value": val,
                        "x_field": label,
                        "y_field": val,
                    })
                except (TypeError, ValueError):
                    continue

        if not canonical_data:
            continue

        specs.append(ChartSpec(
            id=_safe_str(c.get("id", f"chart-{len(specs)}"), f"chart-{len(specs)}"),
            type=chart_type,
            title=title,
            available=True,
            reason=_safe_str(c.get("reason", ""), ""),
            required_columns=required_columns,
            x_axis=x_axis,
            y_axis=y_axis,
            source_column=source_col,
            dimension_column=dimension_col,
            data=canonical_data,
            business_interpretation=business_interpretation,
            confidence=chart_confidence,
            evidence=_safe_str(c.get("query", c.get("source_column", "")), ""),
        ))
    return specs


def build_explainability_card(analytics_dict: Dict[str, Any]) -> ExplainabilityCard:
    confidence_score = _safe_float(analytics_dict.get("confidence_score", 0.0))
    confidence_factors = analytics_dict.get("confidence_factors", {}) or {}
    evidence = analytics_dict.get("evidence", {}) or {}
    predictions = analytics_dict.get("predictions", []) or []
    recommendations = analytics_dict.get("recommendations", []) or []
    anomalies = analytics_dict.get("anomalies", []) or []

    pred_score = _safe_float(confidence_factors.get("prediction_quality", 0.5))
    rec_score = _safe_float(confidence_factors.get("recommendation_quality", 0.5))
    risk_score = _safe_float(confidence_factors.get("outlier_ratio", 0.5))
    evidence_score = _safe_float(confidence_factors.get("evidence_strength", 0.5))

    pred_text = ""
    if predictions:
        p = predictions[0]
        if isinstance(p, dict):
            pred_text = _safe_str(p.get("prediction", ""), "")
        else:
            pred_text = _safe_str(getattr(p, "prediction", ""), "")

    rec_text = ""
    if recommendations:
        r = recommendations[0]
        if isinstance(r, dict):
            rec_text = _safe_str(r.get("reason", "") or r.get("action", ""), "")
        else:
            rec_text = _safe_str(getattr(r, "reason", "") or getattr(r, "action", ""), "")

    total_rows = _safe_float(evidence.get("total_rows", 0))
    why_parts = [
        f"Analysis executed via UniversalAnalyticsEngine against {int(total_rows):,} records."
    ]
    if pred_text:
        why_parts.append(pred_text[:100])
    if rec_text:
        why_parts.append(rec_text[:100])
    why_generated = " ".join(why_parts).strip()

    measures_analyzed = evidence.get("measures_analyzed", []) or []
    dimensions_analyzed = evidence.get("dimensions_analyzed", []) or []
    models_used = evidence.get("models_used", []) or []
    evidence_support = [
        f"Analysis completed on {int(total_rows):,} records",
        f"Measures analyzed: {', '.join(_safe_str(m, '') for m in measures_analyzed[:5])}",
        f"Dimensions analyzed: {', '.join(_safe_str(d, '') for d in dimensions_analyzed[:5])}",
        f"Models used: {', '.join(_safe_str(m, '') for m in models_used[:5])}",
    ]

    assumptions = []
    limitations = []
    if predictions:
        p = predictions[0]
        if isinstance(p, dict):
            assumptions = p.get("assumptions", []) or []
            lim = p.get("limitation")
            if lim:
                limitations.append(_safe_str(lim, ""))
        else:
            assumptions = getattr(p, "assumptions", []) or []
            lim = getattr(p, "limitation", None)
            if lim:
                limitations.append(_safe_str(lim, ""))
    if not assumptions:
        assumptions = ["Historical patterns are predictive of near-term outcomes"]
    if not limitations:
        limitations = ["Prediction accuracy depends on data completeness and absence of regime changes"]

    overall_confidence = round(confidence_score / 100.0, 2) if confidence_score > 1 else round(confidence_score, 2)

    return ExplainabilityCard(
        overall_confidence=overall_confidence,
        evidence_score=round(evidence_score, 2),
        prediction_score=round(pred_score, 2),
        recommendation_score=round(rec_score, 2),
        risk_score=round(risk_score, 2),
        confidence_factors=confidence_factors,
        why_generated=why_generated,
        evidence_support=evidence_support,
        columns_used=evidence.get("columns_used", []) or [],
        tables_used=evidence.get("tables_used", []) or [],
        statistical_methods=models_used,
        assumptions=assumptions,
        limitations=limitations,
    )
