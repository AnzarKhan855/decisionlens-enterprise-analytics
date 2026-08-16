from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.schemas.analytics import (
    AnalyticsResult,
    KPIMetric,
    TrendPoint,
    GrowthDecline,
    Correlation,
    RootCause,
    BusinessAnomaly,
    HealthScore,
    Recommendation,
    RiskItem,
    OpportunityItem,
    RankItem,
)
from app.semantic_model.core import SemanticModel
from app.schemas.dynamic_kpi import (
    DynamicKPIResult,
    DynamicKPICard,
    ExecutiveSummary,
    BusinessFinding,
    ChartRecommendation,
)
from app.analytics.recommendation_engine import MetricDetector
from app.analytics.derived_metrics import discover_derived_metrics, discover_transaction_identifier
from app.logging.logger import get_logger

logger = get_logger(__name__)


class DynamicKPIEngine:
    """
    Dynamic KPI Intelligence Engine.

    Consumes ONLY:
      - AnalyticsResult (from UniversalAnalyticsEngine)
      - SemanticModel  (from Dataset Intelligence Layer)

    Produces:
      - DynamicKPIResult with ranked KPI cards, executive summary,
        chart recommendations, and business findings.

    No CSV reads. No hardcoded business terms. Domain-agnostic.
    """

    @classmethod
    def analyze(
        cls,
        analytics_result: AnalyticsResult,
        semantic_model: SemanticModel,
        profile: Optional[Dict[str, Any]] = None,
    ) -> DynamicKPIResult:
        errors: List[str] = []
        workspace_id = getattr(analytics_result, "workspace_id", "") or getattr(semantic_model, "workspace_id", "")
        domain = getattr(analytics_result, "domain", "") or getattr(semantic_model, "domain", "Generic Business")
        dataset_type = getattr(analytics_result, "dataset_type", "") or getattr(semantic_model, "dataset_type", "Unknown")
        generated_at = datetime.now(timezone.utc).isoformat()
        profile = profile or {}

        try:
            candidates = cls._discover_kpis(analytics_result, semantic_model, profile)
        except Exception as exc:
            logger.error("[DynamicKPI] KPI discovery failed: %s", exc)
            errors.append(f"KPI discovery failed: {str(exc)}")
            candidates = []

        try:
            ranked = cls._rank_kpis(candidates, analytics_result, profile)
        except Exception as exc:
            logger.error("[DynamicKPI] KPI ranking failed: %s", exc)
            errors.append(f"KPI ranking failed: {str(exc)}")
            ranked = candidates

        try:
            top, secondary, supporting = cls._generate_kpi_cards(ranked, analytics_result)
        except Exception as exc:
            logger.error("[DynamicKPI] KPI card generation failed: %s", exc)
            errors.append(f"KPI card generation failed: {str(exc)}")
            top, secondary, supporting = [], [], []

        try:
            executive_summary = cls._generate_executive_summary(analytics_result, semantic_model, top)
        except Exception as exc:
            logger.error("[DynamicKPI] Executive summary failed: %s", exc)
            errors.append(f"Executive summary failed: {str(exc)}")
            executive_summary = ExecutiveSummary()

        try:
            chart_recommendations = cls._recommend_charts(analytics_result, semantic_model, profile)
        except Exception as exc:
            logger.error("[DynamicKPI] Chart recommendations failed: %s", exc)
            errors.append(f"Chart recommendations failed: {str(exc)}")
            chart_recommendations = []

        try:
            business_findings = cls._generate_business_findings(analytics_result, semantic_model)
        except Exception as exc:
            logger.error("[DynamicKPI] Business findings failed: %s", exc)
            errors.append(f"Business findings failed: {str(exc)}")
            business_findings = []

        try:
            dashboard_metadata = cls._build_dashboard_metadata(analytics_result, top, secondary, supporting)
        except Exception as exc:
            logger.error("[DynamicKPI] Dashboard metadata failed: %s", exc)
            errors.append(f"Dashboard metadata failed: {str(exc)}")
            dashboard_metadata = {}

        return DynamicKPIResult(
            workspace_id=workspace_id,
            domain=domain,
            dataset_type=dataset_type,
            generated_at=generated_at,
            kpi_cards={"top": top, "secondary": secondary, "supporting": supporting},
            executive_summary=executive_summary,
            chart_recommendations=chart_recommendations,
            business_findings=business_findings,
            dashboard_metadata=dashboard_metadata,
            errors=errors,
        )

    # =========================================================================
    # KPI Discovery
    # =========================================================================
    @staticmethod
    def _discover_kpis(analytics_result: AnalyticsResult, semantic_model: SemanticModel, profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        candidates: List[Dict[str, Any]] = []

        measures = getattr(analytics_result, "metrics", []) or []
        dimensions = getattr(analytics_result, "dimensions", []) or []
        temporal = []
        try:
            temporal = [t.column for t in (semantic_model.time_columns or [])]
        except Exception:
            pass
        entities = getattr(analytics_result, "entities", []) or []
        volume = getattr(analytics_result, "volume", 0) or 0
        total_rows = profile.get("total_rows", volume)
        summary_stats = getattr(analytics_result, "summary_statistics", {}) or {}
        column_classifications = []
        try:
            column_classifications = getattr(semantic_model, "column_classifications", []) or []
        except Exception:
            pass

        existing_kpis = getattr(analytics_result, "kpis", []) or []
        for kpi in existing_kpis:
            if isinstance(kpi, dict):
                candidates.append({
                    "type": "existing",
                    "name": kpi.get("name", ""),
                    "value": kpi.get("value"),
                    "formatted_value": kpi.get("formatted_value", ""),
                    "metric_type": kpi.get("metric_type", ""),
                    "source_column": kpi.get("source_column", ""),
                    "formula": kpi.get("formula", ""),
                    "rows_analyzed": kpi.get("rows_analyzed", total_rows),
                    "confidence": kpi.get("confidence", 0.0),
                    "available": kpi.get("available", True),
                    "status": kpi.get("status", "Derived from Dataset"),
                    "evidence": kpi.get("evidence", ""),
                    "business_meaning": kpi.get("business_meaning", ""),
                    "business_impact": kpi.get("business_impact", ""),
                })
            else:
                candidates.append({
                    "type": "existing",
                    "name": getattr(kpi, "name", ""),
                    "value": getattr(kpi, "value", None),
                    "formatted_value": getattr(kpi, "formatted_value", ""),
                    "metric_type": getattr(kpi, "metric_type", ""),
                    "source_column": getattr(kpi, "source_column", ""),
                    "formula": getattr(kpi, "formula", ""),
                    "rows_analyzed": getattr(kpi, "rows_analyzed", total_rows),
                    "confidence": getattr(kpi, "confidence", 0.0),
                    "available": getattr(kpi, "available", True),
                    "status": getattr(kpi, "status", "Derived from Dataset"),
                    "evidence": getattr(kpi, "evidence", ""),
                    "business_meaning": getattr(kpi, "business_meaning", ""),
                    "business_impact": getattr(kpi, "business_impact", ""),
                })

        tx_info = discover_transaction_identifier(
            list(profile.get("columns", {}).keys()),
            column_classifications,
            profile,
        )
        if tx_info:
            tx_col = tx_info["column"]
            distinct_count = tx_info.get("distinct_count", 0) or volume
            candidates.append({
                "type": "transaction_count",
                "name": "Total Orders",
                "value": distinct_count,
                "formatted_value": f"{distinct_count:,}",
                "metric_type": "Order Count",
                "source_column": tx_col,
                "formula": f"COUNT(DISTINCT {tx_col})",
                "rows_analyzed": total_rows,
                "confidence": round(tx_info.get("confidence", 0.8), 2),
                "available": True,
                "status": "Derived from Dataset",
                "evidence": tx_info.get("evidence", ""),
                "business_meaning": f"Number of unique transactions identified by '{tx_col}'.",
                "business_impact": "Indicates total transaction volume.",
            })

        for ent in entities[:3]:
            candidates.append({
                "type": "entity_count",
                "name": f"Unique {ent.replace('_', ' ').title()}s",
                "value": volume,
                "formatted_value": f"{volume:,}",
                "metric_type": "Entity Count",
                "source_column": ent,
                "formula": f"COUNT(DISTINCT {ent})",
                "rows_analyzed": total_rows,
                "confidence": 0.8,
                "available": True,
                "status": "Derived from Dataset",
                "evidence": f"Entity count from column '{ent}'",
                "business_meaning": f"Number of unique {ent.replace('_', ' ').title()}s in the dataset.",
                "business_impact": "Indicates dataset scope and entity coverage.",
            })

        for i, m_a in enumerate(measures[:4]):
            for m_b in measures[i + 1:min(i + 4, len(measures))]:
                m_a_type = MetricDetector.detect_metric_type(m_a)
                m_b_type = MetricDetector.detect_metric_type(m_b)
                if m_a_type in ("Revenue", "Profit", "Cost", "Quantity", "Value", "Rate", "Score") and \
                   m_b_type in ("Revenue", "Profit", "Cost", "Quantity", "Value", "Rate", "Score", "Count"):
                    avg_a = summary_stats.get(m_a, {}).get("avg", 0)
                    avg_b = summary_stats.get(m_b, {}).get("avg", 0)
                    ratio_val = None
                    if avg_b != 0:
                        ratio_val = round(avg_a / avg_b, 2)
                    candidates.append({
                        "type": "ratio",
                        "name": f"Average {m_a.replace('_', ' ').title()} per {m_b.replace('_', ' ').title()}",
                        "value": ratio_val,
                        "formatted_value": f"{ratio_val:,.2f}" if ratio_val is not None else "N/A",
                        "metric_type": "Ratio",
                        "source_column": f"{m_a}/{m_b}",
                        "formula": f"AVG({m_a} / {m_b})",
                        "rows_analyzed": total_rows,
                        "confidence": 0.7 if ratio_val is not None else 0.3,
                        "available": ratio_val is not None,
                        "status": "Computed Ratio",
                        "evidence": f"Derived from columns '{m_a}' and '{m_b}' using summary statistics",
                        "business_meaning": f"Average ratio of {m_a.replace('_', ' ').title()} to {m_b.replace('_', ' ').title()} across records.",
                        "business_impact": "Provides normalized comparison across business units.",
                    })

        derived_metrics = discover_derived_metrics(
            measures=measures,
            dimensions=dimensions,
            column_classifications=column_classifications,
            profile=profile,
        )
        for dm in derived_metrics[:4]:
            dm_name = dm.get("metric_name", "Derived Metric")
            dm_formula = dm.get("formula", "")
            dm_sources = dm.get("source_columns", [])
            dm_confidence = dm.get("confidence", 0.7)
            dm_meaning = dm.get("business_meaning", "")
            dm_evidence = dm.get("evidence", "")

            computed_value = None
            if len(dm_sources) == 2:
                src_a, src_b = dm_sources[0], dm_sources[1]
                stats_a = summary_stats.get(src_a, {})
                stats_b = summary_stats.get(src_b, {})
                sum_a = stats_a.get("sum", 0)
                sum_b = stats_b.get("sum", 0)
                if sum_a is not None and sum_b is not None and sum_a > 0 and sum_b > 0:
                    computed_value = round(sum_a * sum_b, 2)

            if computed_value is None:
                computed_value = 0.0

            is_currency = any(
                col_profiles.get(s, {}).get("semantic_type", "").lower() in ("currency", "percentage")
                for s in dm_sources
            )
            candidates.append({
                "type": "derived_metric",
                "name": dm_name,
                "value": computed_value,
                "formatted_value": f"{computed_value:,.2f}" if is_currency else f"{computed_value:,.0f}",
                "metric_type": MetricDetector.detect_metric_type(dm_name),
                "source_column": " | ".join(dm_sources),
                "formula": dm_formula,
                "rows_analyzed": total_rows,
                "confidence": round(dm_confidence, 2),
                "available": True,
                "status": "Derived Metric",
                "evidence": dm_evidence,
                "business_meaning": dm_meaning,
                "business_impact": f"Derived metric: {dm_meaning}",
            })

        for dim in dimensions[:3]:
            distinct_count = profile.get("columns", {}).get(dim, {}).get("distinct_count", 0)
            candidates.append({
                "type": "cardinality",
                "name": f"Distinct {dim.replace('_', ' ').title()}s",
                "value": distinct_count,
                "formatted_value": f"{distinct_count:,}",
                "metric_type": "Cardinality",
                "source_column": dim,
                "formula": f"COUNT(DISTINCT {dim})",
                "rows_analyzed": total_rows,
                "confidence": 0.85,
                "available": True,
                "status": "Derived from Dataset",
                "evidence": f"Distinct count from column '{dim}'",
                "business_meaning": f"Number of unique {dim.replace('_', ' ').title()} values in the dataset.",
                "business_impact": "Indicates segmentation depth and categorical diversity.",
            })

        trends = getattr(analytics_result, "trends", {}) or {}
        for m, pts in trends.items():
            if len(pts) >= 2:
                first_val = pts[0].value if pts[0].value is not None else 0
                last_val = pts[-1].value if pts[-1].value is not None else 0
                if first_val != 0:
                    growth_pct = round(((last_val - first_val) / first_val) * 100, 2)
                    candidates.append({
                        "type": "growth_rate",
                        "name": f"{m.replace('_', ' ').title()} Growth Rate",
                        "value": growth_pct,
                        "formatted_value": f"{growth_pct:+.2f}%",
                        "metric_type": "Growth Rate",
                        "source_column": m,
                        "formula": "((Latest - First) / First) * 100",
                        "rows_analyzed": len(pts),
                        "confidence": 0.75,
                        "available": True,
                        "status": "Computed from Trends",
                        "evidence": f"Computed from {len(pts)} trend periods for {m}",
                        "business_meaning": f"Percentage change in {m.replace('_', ' ').title()} from first to last period.",
                        "business_impact": "Shows directional momentum for this metric.",
                    })

        seen = set()
        unique_candidates: List[Dict[str, Any]] = []
        for c in candidates:
            key = c.get("name", "")
            if key and key not in seen:
                seen.add(key)
                unique_candidates.append(c)

        return unique_candidates

    # =========================================================================
    # KPI Ranking
    # =========================================================================
    @staticmethod
    def _rank_kpis(candidates: List[Dict[str, Any]], analytics_result: AnalyticsResult, profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        measures = getattr(analytics_result, "metrics", []) or []
        volume = getattr(analytics_result, "volume", 0) or 0
        anomalies = getattr(analytics_result, "anomalies", []) or []
        correlations = getattr(analytics_result, "correlations", []) or []
        trends = getattr(analytics_result, "trends", {}) or {}

        anomaly_columns = set()
        for a in anomalies:
            col = getattr(a, "category", "") or ""
            if col:
                anomaly_columns.add(col.lower())

        correlation_map: Dict[str, float] = {}
        for corr in correlations:
            a = getattr(corr, "column_a", "")
            b = getattr(corr, "column_b", "")
            coef = abs(getattr(corr, "coefficient", 0.0) or 0.0)
            if a:
                correlation_map[a.lower()] = max(correlation_map.get(a.lower(), 0.0), coef)
            if b:
                correlation_map[b.lower()] = max(correlation_map.get(b.lower(), 0.0), coef)

        trend_variance_map: Dict[str, float] = {}
        for m, pts in trends.items():
            if len(pts) >= 2:
                vals = [p.value for p in pts if p.value is not None]
                if vals:
                    mean = sum(vals) / len(vals)
                    variance = sum((v - mean) ** 2 for v in vals) / len(vals)
                    trend_variance_map[m.lower()] = variance

        domain_importance: Dict[str, float] = {}
        for m in measures:
            m_lower = m.lower()
            base_score = 0.5
            if any(k in m_lower for k in ["revenue", "sales", "amount", "total", "income"]):
                base_score = 0.95
            elif any(k in m_lower for k in ["profit", "margin", "net", "earnings"]):
                base_score = 0.9
            elif any(k in m_lower for k in ["cost", "expense", "cogs", "overhead"]):
                base_score = 0.85
            elif any(k in m_lower for k in ["quantity", "qty", "units", "volume", "count"]):
                base_score = 0.8
            elif any(k in m_lower for k in ["customer", "patient", "employee", "user", "client"]):
                base_score = 0.8
            elif any(k in m_lower for k in ["order", "transaction", "invoice", "ticket"]):
                base_score = 0.75
            elif any(k in m_lower for k in ["price", "rate", "premium"]):
                base_score = 0.7
            elif any(k in m_lower for k in ["score", "rating", "index", "nps", "grade"]):
                base_score = 0.65
            elif any(k in m_lower for k in ["duration", "time", "interval"]):
                base_score = 0.6
            elif any(k in m_lower for k in ["risk", "probability", "likelihood"]):
                base_score = 0.7
            domain_importance[m_lower] = base_score

        TYPE_IMPORTANCE_BONUS = {
            "transaction_count": 0.15,
            "derived_metric": 0.10,
            "entity_count": 0.05,
            "existing": 0.0,
            "ratio": 0.0,
            "cardinality": 0.0,
            "growth_rate": 0.0,
        }

        for c in candidates:
            src = c.get("source_column", "")
            src_lower = src.lower() if src else ""
            split_src = [s.strip() for s in src_lower.split("/") if s.strip()] if "/" in src_lower else [src_lower]

            business_impact = 0.5
            for s in split_src:
                if s in domain_importance:
                    business_impact = max(business_impact, domain_importance[s])

            col_profiles = profile.get("columns", {})
            coverage = 0.8
            for s in split_src:
                if s in col_profiles:
                    null_pct = col_profiles[s].get("null_percentage", 0.0)
                    coverage = min(coverage, max(0.0, 1.0 - (null_pct / 100.0)))

            confidence = c.get("confidence", 0.0) or 0.0
            confidence = max(0.0, min(1.0, confidence))

            variance_score = 0.7
            for s in split_src:
                if s in trend_variance_map:
                    variance_score = min(variance_score, max(0.0, 1.0 - min(trend_variance_map[s] / 1000000, 1.0)))

            corr_score = 0.5
            for s in split_src:
                if s in correlation_map:
                    corr_score = max(corr_score, correlation_map[s])

            trend_strength = 0.5
            for s in split_src:
                if s in trends and len(trends[s]) >= 2:
                    pts = trends[s]
                    ups = sum(1 for p in pts if p.change_pct and p.change_pct > 0)
                    downs = sum(1 for p in pts if p.change_pct and p.change_pct < 0)
                    total = ups + downs
                    if total > 0:
                        trend_strength = max(ups, downs) / total

            anomaly_score = 0.8
            for s in split_src:
                if s in anomaly_columns:
                    anomaly_score = 0.3
                    break

            score = (
                business_impact * 0.30 +
                coverage * 0.20 +
                confidence * 0.20 +
                (1.0 - variance_score) * 0.10 +
                corr_score * 0.05 +
                trend_strength * 0.10 +
                anomaly_score * 0.05
            )
            type_bonus = TYPE_IMPORTANCE_BONUS.get(c.get("type", ""), 0.0)
            score = min(1.0, score + type_bonus)
            c["rank_score"] = round(score, 4)
            c["business_impact_score"] = round(business_impact, 4)
            c["data_coverage_score"] = round(coverage, 4)
            c["variance_score"] = round(variance_score, 4)
            c["trend_strength_score"] = round(trend_strength, 4)
            c["anomaly_score"] = round(anomaly_score, 4)
            c["correlation_score"] = round(corr_score, 4)

        ranked = sorted(candidates, key=lambda x: x.get("rank_score", 0.0), reverse=True)
        return ranked

    # =========================================================================
    # KPI Card Generation
    # =========================================================================
    @staticmethod
    def _generate_kpi_cards(ranked: List[Dict[str, Any]], analytics_result: AnalyticsResult) -> Tuple[List[DynamicKPICard], List[DynamicKPICard], List[DynamicKPICard]]:
        top: List[DynamicKPICard] = []
        secondary: List[DynamicKPICard] = []
        supporting: List[DynamicKPICard] = []

        trends = getattr(analytics_result, "trends", {}) or {}
        growth = getattr(analytics_result, "growth", []) or []
        decline = getattr(analytics_result, "decline", []) or []
        anomalies = getattr(analytics_result, "anomalies", []) or []

        for c in ranked:
            name = c.get("name", "")
            value = c.get("value")
            formatted = c.get("formatted_value", "")
            metric_type = c.get("metric_type", "")
            src = c.get("source_column", "") or ""
            confidence = c.get("confidence", 0.0) or 0.0

            trend_str = "Stable"
            trend_direction = "stable"
            trend_value_str = ""
            change_pct = None
            comparison_period = ""

            if src and src in trends:
                pts = trends[src]
                if len(pts) >= 2:
                    ups = sum(1 for p in pts if p.change_pct and p.change_pct > 0)
                    downs = sum(1 for p in pts if p.change_pct and p.change_pct < 0)
                    if ups > downs:
                        trend_str = f"Upward ({ups} up periods)"
                        trend_direction = "up"
                    elif downs > ups:
                        trend_str = f"Downward ({downs} down periods)"
                        trend_direction = "down"
                    first_val = pts[0].value if pts[0].value is not None else 0
                    last_val = pts[-1].value if pts[-1].value is not None else 0
                    if first_val and first_val != 0:
                        change_pct = round(((last_val - first_val) / first_val) * 100, 2)
                        trend_value_str = f"{change_pct:+.1f}%"
                    comparison_period = f"{pts[0].period} to {pts[-1].period}"

            for g in growth:
                g_measure = getattr(g, "measure", "") or ""
                if g_measure and (g_measure == src or g_measure.lower() == src.lower()):
                    trend_str = "Growing"
                    trend_direction = "up"
                    g_pct = getattr(g, "change_pct", None)
                    if g_pct is not None:
                        change_pct = round(g_pct, 2)
                        trend_value_str = f"{change_pct:+.1f}%"
                    comparison_period = getattr(g, "period", comparison_period) or comparison_period
                    break

            for d in decline:
                d_measure = getattr(d, "measure", "") or ""
                if d_measure and (d_measure == src or d_measure.lower() == src.lower()):
                    trend_str = "Declining"
                    trend_direction = "down"
                    d_pct = getattr(d, "change_pct", None)
                    if d_pct is not None:
                        change_pct = round(d_pct, 2)
                        trend_value_str = f"{change_pct:+.1f}%"
                    comparison_period = getattr(d, "period", comparison_period) or comparison_period
                    break

            has_anomaly = False
            for a in anomalies:
                a_cat = getattr(a, "category", "") or ""
                if a_cat and (a_cat.lower() == src.lower() or src.lower() in a_cat.lower()):
                    has_anomaly = True
                    break

            if has_anomaly:
                status = "Anomalous"
            elif trend_direction == "up":
                status = "Growing"
            elif trend_direction == "down":
                status = "Declining"
            else:
                status = "Stable"

            business_meaning = c.get("business_meaning", "")
            if not business_meaning:
                business_meaning = DynamicKPIEngine._generate_business_meaning(name, metric_type, value, formatted, trend_direction, has_anomaly, change_pct)

            why_it_matters = DynamicKPIEngine._generate_why_it_matters(name, metric_type, value, trend_direction, has_anomaly, change_pct)

            evidence = c.get("evidence", "")
            if not evidence:
                evidence = f"Computed from {c.get('source_column', 'dataset columns')} across {c.get('rows_analyzed', 0):,} rows."

            score = c.get("rank_score", 0.0)
            if score >= 0.7:
                importance = "Critical"
                priority = "HIGH"
            elif score >= 0.4:
                importance = "Important"
                priority = "MEDIUM"
            else:
                importance = "Supporting"
                priority = "LOW"

            display_value = value
            display_formatted = formatted
            available = c.get("available", True)
            if not available or display_value is None or (isinstance(display_value, str) and display_value.strip().lower() in ("nan", "none", "null", "")):
                display_value = "N/A"
                display_formatted = "N/A"
                available = False
            if isinstance(display_value, str) and display_value.strip().lower() in ("undefined", "nan", "infinity", "-infinity"):
                display_value = "unavailable"
                display_formatted = "unavailable"
                available = False

            data_source = c.get("source_column", src) or src
            if not data_source:
                data_source = "Dataset"

            card = DynamicKPICard(
                title=name,
                value=display_value,
                formatted_value=display_formatted,
                confidence=round(confidence, 2),
                business_meaning=business_meaning,
                evidence=evidence,
                why_it_matters=why_it_matters,
                trend=trend_str,
                status=status,
                importance=importance,
                priority=priority,
                metric_type=metric_type,
                source_column=src,
                formula=c.get("formula", ""),
                rows_analyzed=c.get("rows_analyzed", 0),
                category=c.get("type", ""),
                rank_score=score,
                trend_value=trend_value_str,
                change_pct=change_pct,
                comparison_period=comparison_period,
                data_source=data_source,
            )

            if score >= 0.7:
                top.append(card)
            elif score >= 0.4:
                secondary.append(card)
            else:
                supporting.append(card)

        if not top and not secondary and not supporting and ranked:
            c = ranked[0]
            card = DynamicKPICard(
                title=c.get("name", "Primary KPI"),
                value=c.get("value", "N/A") if c.get("value") is not None else "N/A",
                formatted_value=c.get("formatted_value", "N/A") if c.get("formatted_value") else "N/A",
                confidence=round(c.get("confidence", 0.0), 2),
                business_meaning=c.get("business_meaning", "Key business metric derived from dataset."),
                evidence=c.get("evidence", ""),
                why_it_matters="Primary indicator of business performance.",
                trend="Stable",
                status="Stable",
                importance="Critical",
                priority="HIGH",
                metric_type=c.get("metric_type", ""),
                source_column=c.get("source_column", ""),
                formula=c.get("formula", ""),
                rows_analyzed=c.get("rows_analyzed", 0),
                category=c.get("type", ""),
                rank_score=c.get("rank_score", 0.0),
                trend_value="",
                change_pct=None,
                comparison_period="",
                data_source=c.get("source_column", "") or "Dataset",
            )
            top.append(card)

        return top, secondary, supporting

    @staticmethod
    def _generate_business_meaning(name: str, metric_type: str, value: Any, formatted: str, trend: str, has_anomaly: bool, change_pct: Optional[float] = None) -> str:
        name_clean = name.replace("_", " ").title()
        if metric_type == "Record Count":
            return f"The dataset contains {formatted if formatted else value} records."
        elif metric_type == "Entity Count":
            return f"There are {formatted if formatted else value} unique {name_clean.lower()} in the dataset."
        elif metric_type == "Growth Rate":
            direction = "increased" if trend == "up" else "decreased" if trend == "down" else "changed"
            pct_str = f" by {abs(change_pct):.1f}%" if change_pct is not None else ""
            return f"{name_clean} has {direction}{pct_str} over the observed period."
        elif metric_type == "Cardinality":
            return f"The {name_clean.lower()} dimension contains {formatted if formatted else value} distinct values."
        elif metric_type == "Ratio":
            return f"The ratio of {name_clean} provides a normalized business comparison."
        else:
            if has_anomaly:
                return f"{name_clean} shows anomalous behavior requiring investigation."
            return f"{name_clean} is a key business metric tracked across the dataset."

    @staticmethod
    def _generate_why_it_matters(name: str, metric_type: str, value: Any, trend: str, has_anomaly: bool, change_pct: Optional[float] = None) -> str:
        name_clean = name.replace("_", " ").title()
        if has_anomaly:
            return f"Anomalies detected in {name_clean} may indicate operational issues or data quality problems."
        if trend == "up":
            pct_str = f" by {abs(change_pct):.1f}%" if change_pct is not None else ""
            return f"Positive momentum in {name_clean} suggests favorable business conditions{pct_str}."
        elif trend == "down":
            pct_str = f" by {abs(change_pct):.1f}%" if change_pct is not None else ""
            return f"Negative trend in {name_clean} requires attention to prevent further decline{pct_str}."
        return f"{name_clean} is a foundational indicator for business health and performance."

    # =========================================================================
    # Executive Summary
    # =========================================================================
    @staticmethod
    def _generate_executive_summary(analytics_result: AnalyticsResult, semantic_model: SemanticModel, top_kpis: List[DynamicKPICard]) -> ExecutiveSummary:
        critical_findings = getattr(analytics_result, "critical_findings", []) or []
        positive_findings = getattr(analytics_result, "positive_findings", []) or []
        negative_findings = getattr(analytics_result, "negative_findings", []) or []
        risks = getattr(analytics_result, "risks", []) or []
        opportunities = getattr(analytics_result, "opportunities", []) or []
        root_causes = getattr(analytics_result, "root_causes", []) or []
        growth = getattr(analytics_result, "growth", []) or []
        decline = getattr(analytics_result, "decline", []) or []
        rankings = getattr(analytics_result, "rankings", {}) or {}

        findings: List[BusinessFinding] = []
        for i, f in enumerate(critical_findings[:5], 1):
            findings.append(BusinessFinding(
                id=f"FIND-CRITICAL-{i}",
                title=f"Critical Finding {i}",
                category="Critical",
                severity="CRITICAL",
                description=f,
                evidence="From anomaly and root cause analysis",
            ))
        for i, f in enumerate(negative_findings[:3], len(findings) + 1):
            findings.append(BusinessFinding(
                id=f"FIND-NEG-{i}",
                title=f"Warning {i}",
                category="Warning",
                severity="HIGH",
                description=f,
                evidence="From trend and anomaly analysis",
            ))
        for i, f in enumerate(positive_findings[:2], len(findings) + 1):
            findings.append(BusinessFinding(
                id=f"FIND-POS-{i}",
                title=f"Positive Signal {i}",
                category="Positive",
                severity="LOW",
                description=f,
                evidence="From growth and opportunity analysis",
            ))
        top_5_findings = findings[:5]

        top_5_risks = []
        for i, r in enumerate(risks[:5], 1):
            top_5_risks.append(BusinessFinding(
                id=f"RISK-{i}",
                title=getattr(r, "title", f"Risk {i}"),
                category=getattr(r, "category", "Business Risk"),
                severity=getattr(r, "severity", "MEDIUM"),
                description=getattr(r, "description", ""),
                evidence=getattr(r, "impact", ""),
            ))

        top_5_opportunities = []
        for i, o in enumerate(opportunities[:5], 1):
            top_5_opportunities.append(BusinessFinding(
                id=f"OPP-{i}",
                title=getattr(o, "title", f"Opportunity {i}"),
                category=getattr(o, "category", "Growth"),
                severity=getattr(o, "priority", "MEDIUM"),
                description=getattr(o, "description", ""),
                evidence=getattr(o, "impact", ""),
            ))

        critical_metrics = []
        for kpi in top_kpis:
            if kpi.status in ("Anomalous", "Declining") or kpi.confidence < 0.5:
                critical_metrics.append(kpi.title)
        if not critical_metrics and top_kpis:
            critical_metrics = [top_kpis[0].title]
        critical_metrics = critical_metrics[:5]

        fastest_growing = "N/A"
        if growth:
            fastest_growing = getattr(growth[0], "period", "N/A")
        elif rankings:
            for dim, items in rankings.items():
                if items:
                    fastest_growing = f"{dim}: {items[0].category}"
                    break

        weakest = "N/A"
        if decline:
            weakest = getattr(decline[0], "period", "N/A")
        elif rankings:
            for dim, items in rankings.items():
                if len(items) >= 2:
                    weakest = f"{dim}: {items[-1].category}"
                    break

        largest_contributor = "N/A"
        if root_causes:
            rc = root_causes[0]
            td = getattr(rc, "top_driver", None)
            if td:
                largest_contributor = f"{td.get('category', 'N/A')} ({td.get('contribution_percentage', 0)}%)"

        most_stable = "N/A"
        stable_kpis = [k for k in top_kpis if k.status == "Stable" and k.confidence >= 0.7]
        if stable_kpis:
            most_stable = stable_kpis[0].title
        elif top_kpis:
            most_stable = top_kpis[0].title

        return ExecutiveSummary(
            top_5_findings=top_5_findings,
            top_5_risks=top_5_risks,
            top_5_opportunities=top_5_opportunities,
            critical_metrics=critical_metrics,
            fastest_growing_segment=fastest_growing,
            weakest_segment=weakest,
            largest_contributor=largest_contributor,
            most_stable_indicator=most_stable,
        )

    # =========================================================================
    # Chart Recommendations
    # =========================================================================
    @staticmethod
    def _recommend_charts(analytics_result: AnalyticsResult, semantic_model: SemanticModel, profile: Dict[str, Any]) -> List[ChartRecommendation]:
        recommendations: List[ChartRecommendation] = []
        measures = getattr(analytics_result, "metrics", []) or []
        dimensions = getattr(analytics_result, "dimensions", []) or []
        temporal = []
        try:
            temporal = [t.column for t in (semantic_model.time_columns or [])]
        except Exception:
            pass

        primary_measure = measures[0] if measures else None
        primary_dimension = dimensions[0] if dimensions else None
        secondary_dimension = dimensions[1] if len(dimensions) > 1 else None

        if not primary_measure:
            return recommendations

        if temporal and primary_measure:
            recommendations.append(ChartRecommendation(
                chart_type="line",
                title=f"Trend: {primary_measure.replace('_', ' ').title()} Over Time",
                x_axis=temporal[0],
                y_axis=primary_measure,
                reason="Temporal dimension detected with numeric measure - ideal for trend visualization.",
                required_columns=[temporal[0], primary_measure],
                confidence=0.9,
                priority="HIGH",
            ))

        if primary_dimension and primary_measure:
            cardinality = 0
            if primary_dimension in profile.get("columns", {}):
                cardinality = profile["columns"][primary_dimension].get("distinct_count", 0)
            chart_type = "bar" if cardinality > 6 else "pie"
            recommendations.append(ChartRecommendation(
                chart_type=chart_type,
                title=f"Distribution: {primary_measure.replace('_', ' ').title()} by {primary_dimension.replace('_', ' ').title()}",
                x_axis=primary_dimension,
                y_axis=primary_measure,
                reason=f"Primary dimension with {cardinality or 'multiple'} categories detected - optimal for categorical comparison.",
                required_columns=[primary_dimension, primary_measure],
                confidence=0.85,
                priority="HIGH",
            ))

        if secondary_dimension and primary_measure:
            recommendations.append(ChartRecommendation(
                chart_type="horizontal_bar",
                title=f"Record Count by {secondary_dimension.replace('_', ' ').title()}",
                x_axis=secondary_dimension,
                y_axis=primary_measure,
                reason="Secondary dimension provides additional categorical context.",
                required_columns=[secondary_dimension, primary_measure],
                confidence=0.7,
                priority="MEDIUM",
            ))

        if len(measures) >= 2:
            recommendations.append(ChartRecommendation(
                chart_type="scatter",
                title=f"Correlation: {measures[0].replace('_', ' ').title()} vs {measures[1].replace('_', ' ').title()}",
                x_axis=measures[0],
                y_axis=measures[1],
                reason="Multiple numeric measures detected - scatter plot reveals relationships.",
                required_columns=[measures[0], measures[1]],
                confidence=0.75,
                priority="MEDIUM",
            ))

        if primary_measure:
            recommendations.append(ChartRecommendation(
                chart_type="histogram",
                title=f"Distribution of {primary_measure.replace('_', ' ').title()}",
                x_axis=primary_measure,
                y_axis="frequency",
                reason="Primary measure distribution provides insight into data spread and outliers.",
                required_columns=[primary_measure],
                confidence=0.65,
                priority="LOW",
            ))

        if primary_dimension and primary_measure:
            cardinality = profile.get("columns", {}).get(primary_dimension, {}).get("distinct_count", 0)
            if cardinality and cardinality <= 6:
                recommendations.append(ChartRecommendation(
                    chart_type="pie",
                    title=f"Composition: {primary_measure.replace('_', ' ').title()} by {primary_dimension.replace('_', ' ').title()}",
                    x_axis=primary_dimension,
                    y_axis=primary_measure,
                    reason="Few distinct categories detected - pie chart shows proportional contribution.",
                    required_columns=[primary_dimension, primary_measure],
                    confidence=0.8,
                    priority="MEDIUM",
                ))

        if len(dimensions) >= 2 and primary_measure:
            recommendations.append(ChartRecommendation(
                chart_type="treemap",
                title=f"Hierarchical View: {primary_measure.replace('_', ' ').title()} by {dimensions[0].replace('_', ' ').title()} and {dimensions[1].replace('_', ' ').title()}",
                x_axis=dimensions[0],
                y_axis=primary_measure,
                reason="Multiple dimensions detected - treemap supports hierarchical drill-down.",
                required_columns=dimensions[:2] + [primary_measure],
                confidence=0.6,
                priority="LOW",
            ))

        return recommendations

    # =========================================================================
    # Business Findings
    # =========================================================================
    @staticmethod
    def _generate_business_findings(analytics_result: AnalyticsResult, semantic_model: SemanticModel) -> List[BusinessFinding]:
        findings: List[BusinessFinding] = []
        critical_findings = getattr(analytics_result, "critical_findings", []) or []
        positive_findings = getattr(analytics_result, "positive_findings", []) or []
        negative_findings = getattr(analytics_result, "negative_findings", []) or []
        recommendations = getattr(analytics_result, "recommendations", []) or []
        anomalies = getattr(analytics_result, "anomalies", []) or []

        for i, f in enumerate(critical_findings[:5], 1):
            findings.append(BusinessFinding(
                id=f"FIND-{i}",
                title=f"Critical Insight {i}",
                category="Critical",
                severity="CRITICAL",
                description=f,
                evidence="Root cause and anomaly detection analysis",
            ))

        for i, f in enumerate(negative_findings[:3], len(findings) + 1):
            findings.append(BusinessFinding(
                id=f"FIND-{i}",
                title=f"Warning {i}",
                category="Warning",
                severity="HIGH",
                description=f,
                evidence="Trend and variance analysis",
            ))

        for i, f in enumerate(positive_findings[:2], len(findings) + 1):
            findings.append(BusinessFinding(
                id=f"FIND-{i}",
                title=f"Positive Signal {i}",
                category="Positive",
                severity="LOW",
                description=f,
                evidence="Growth and opportunity analysis",
            ))

        for a in anomalies[:3]:
            findings.append(BusinessFinding(
                id=f"ANOMALY-{getattr(a, 'period', 'unknown')}",
                title=getattr(a, "title", "Anomaly Detected"),
                category="Anomaly",
                severity=getattr(a, "severity", "MEDIUM"),
                description=getattr(a, "explanation", ""),
                evidence=f"Z-score: {getattr(a, 'z_score', 0)}, actual: {getattr(a, 'actual_value', 0)}, expected: {getattr(a, 'expected_value', 0)}",
            ))

        for r in recommendations[:3]:
            if getattr(r, "priority", "") in ("CRITICAL", "HIGH"):
                findings.append(BusinessFinding(
                    id=f"REC-{getattr(r, 'id', 'unknown')}",
                    title=getattr(r, "title", "Recommendation"),
                    category="Recommendation",
                    severity=getattr(r, "priority", "MEDIUM"),
                    description=getattr(r, "reason", ""),
                    evidence=getattr(r, "action", ""),
                ))

        return findings[:10]

    # =========================================================================
    # Dashboard Metadata
    # =========================================================================
    @staticmethod
    def _build_dashboard_metadata(analytics_result: AnalyticsResult, top: List[DynamicKPICard], secondary: List[DynamicKPICard], supporting: List[DynamicKPICard]) -> Dict[str, Any]:
        health_score = getattr(analytics_result, "health_score", None)
        hs_val = 0.0
        if health_score:
            if isinstance(health_score, dict):
                hs_val = health_score.get("overall_score", 0.0)
            else:
                hs_val = getattr(health_score, "overall_score", 0.0) or 0.0

        confidence_score = getattr(analytics_result, "confidence_score", 0.0) or 0.0

        return {
            "total_kpis": len(top) + len(secondary) + len(supporting),
            "top_kpis_count": len(top),
            "secondary_kpis_count": len(secondary),
            "supporting_kpis_count": len(supporting),
            "confidence_score": confidence_score,
            "health_score": hs_val,
            "domain": getattr(analytics_result, "domain", "Generic Business"),
            "dataset_type": getattr(analytics_result, "dataset_type", "Unknown"),
            "volume": getattr(analytics_result, "volume", 0) or 0,
        }
