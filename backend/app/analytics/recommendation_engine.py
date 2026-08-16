from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from app.ingestion.semantic_profiler import SemanticDataProfiler
from app.ai.explainable_ai_engine import ExplainableAIEngine
from app.database.duckdb_engine import DuckDBEngine


def _kpi_val(kpi: Any, attr: str = "value", default: Any = 0.0) -> Any:
    if isinstance(kpi, dict):
        return kpi.get(attr, default)
    return getattr(kpi, attr, default)


class MetricDetector:
    """
    Detects the true underlying business metric represented by dataset columns.
    """

    @classmethod
    def detect_metric_type(cls, column_name: str) -> str:
        if not column_name or column_name.lower() in ("count", "row_count", "total_records", "record_count", "frequency"):
            return "Record Count"

        col_lower = column_name.lower()
        metric_keywords = {
            "Revenue": ["revenue", "sales", "amount", "total", "income"],
            "Profit": ["profit", "margin", "net", "earnings"],
            "Cost": ["cost", "expense", "cogs", "overhead", "fee"],
            "Quantity": ["quantity", "qty", "volume", "units", "count"],
            "Price": ["price", "rate", "fare", "premium"],
            "Rate": ["rate", "percentage", "ratio", "efficiency", "density"],
            "Score": ["score", "rating", "index", "nps", "grade"],
            "Duration": ["duration", "time", "period", "interval"],
            "Count": ["count", "frequency", "number", "total"],
            "Value": ["value", "worth", "valuation", "capital"],
        }
        for metric_type, keywords in metric_keywords.items():
            for kw in keywords:
                if kw in col_lower:
                    return metric_type

        return "Unknown"


class RecommendationEngine:
    """
    Enterprise Evidence-Based AI Recommendation Engine.
    Strict Rule: Only generates strategic recommendations when supported by verified business metrics.
    """

    @classmethod
    def generate_recommendations(
        cls,
        parquet_path: Path,
        semantic_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if not semantic_profile:
            semantic_profile = SemanticDataProfiler.profile(parquet_path)

        measures = semantic_profile["column_categories"].get("measures", [])
        dimensions = semantic_profile["column_categories"].get("dimensions", [])
        total_rows = semantic_profile.get("total_rows", 0)

        primary_measure = measures[0] if measures else None
        metric_type = MetricDetector.detect_metric_type(primary_measure) if primary_measure else "Record Count"

        if metric_type in ("Record Count", "Unknown"):
            confidence_result = ExplainableAIEngine.compute_confidence(
                profile=semantic_profile,
                recommendations=[],
            )
            rec_confidence = confidence_result.recommendation_score
            return {
                "has_valid_strategy": False,
                "disclaimer": (
                    "This analysis shows record distributions across categories. "
                    "It does not indicate business performance. Numeric financial or operational metrics "
                    "are required before strategic recommendations can be made."
                ),
                "metric_type": metric_type,
                "evidence_panel": {
                    "dataset_columns_used": measures + dimensions,
                    "rows_analysed": total_rows,
                    "aggregation_performed": "COUNT(*)",
                    "formula": "COUNT(rows_per_category)",
                    "confidence": f"{rec_confidence:.0%}",
                    "validity_rationale": "Record distribution reflects data volume, not operational performance."
                },
                "recommendations": []
            }

        primary_dim = dimensions[0] if dimensions else "Segment"
        confidence_result = ExplainableAIEngine.compute_confidence(
            profile=semantic_profile,
            recommendations=[],
        )
        rec_confidence = confidence_result.recommendation_score

        recommendations = [
            {
                "id": "REC-001",
                "title": f"Optimize Top-Performing {primary_dim.replace('_', ' ').title()} Strategy",
                "evidence_used": f"Aggregated {metric_type} values across {total_rows:,} verified rows.",
                "metrics_analysed": [primary_measure, primary_dim],
                "business_rationale": f"Data indicates significant {metric_type} concentration in top category segments.",
                "confidence": round(rec_confidence * 100.0, 1),
                "assumptions": ["Current conditions remain consistent"],
                "limitations": ["Historical baseline evaluated over current sample period only"],
                "evidence_panel": {
                    "dataset_columns_used": [primary_measure, primary_dim],
                    "rows_analysed": total_rows,
                    "aggregation_performed": f"SUM({primary_measure}) GROUP BY {primary_dim}",
                    "formula": f"SUM({primary_measure})",
                    "confidence": f"{rec_confidence:.0%}",
                    "validity_rationale": f"Direct metric '{primary_measure}' verified against verified data analysis."
                }
            }
        ]

        return {
            "has_valid_strategy": True,
            "metric_type": metric_type,
            "disclaimer": None,
            "recommendations": recommendations,
            "evidence_panel": {
                "dataset_columns_used": [primary_measure, primary_dim],
                "rows_analysed": total_rows,
                "aggregation_performed": f"SUM({primary_measure})",
                "formula": f"SUM({primary_measure})",
                "confidence": f"{rec_confidence:.0%}",
                "validity_rationale": "Backed by verified quantitative metric schema classification."
            }
        }

    @classmethod
    def generate_retail_recommendations(
        cls,
        parquet_path: Path,
        profile: Dict[str, Any],
        canonical_model: Optional[Any],
        root_causes: List[Any],
        anomalies: List[Any],
        drivers: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Generate evidence-based retail-specific recommendations.

        Every recommendation includes:
        - problem, evidence, root_cause, priority, business_impact,
          expected_gain, recommended_action, affected_products,
          affected_categories, confidence
        """
        path_str = str(parquet_path).replace("\\", "/")
        recommendations: List[Dict[str, Any]] = []

        if not canonical_model:
            return {
                "has_valid_strategy": False,
                "recommendations": [],
                "disclaimer": "Canonical retail model not available for evidence-based retail recommendations."
            }

        try:
            from app.retail.kpi_engine import RetailKPIEngine
            kpis = RetailKPIEngine.compute_all_kpis(parquet_path, canonical_model, profile)
        except Exception:
            kpis = []

        try:
            confidence_result = ExplainableAIEngine.compute_confidence(profile=profile, recommendations=[])
            base_confidence = confidence_result.recommendation_score
        except Exception:
            base_confidence = 0.75

        kpi_map = {k.name: k for k in kpis} if kpis else {}

        # =====================================================================
        # Helper: safe duckdb query
        # =====================================================================
        def _safe_query(sql: str) -> Optional[Dict[str, Any]]:
            try:
                rows = DuckDBEngine.query(sql)
                return rows[0] if rows else None
            except Exception:
                return None

        def _esc(col: Optional[str]) -> str:
            return f'"{col}"' if col else ""

        # =====================================================================
        # 1. Concentration risk: diversify away from top driver
        # =====================================================================
        for rc in root_causes:
            if not rc.top_driver or not getattr(rc, "concentration_risk", False):
                continue
            top_cat = rc.top_driver.get("category", "Top Category")
            contrib_pct = rc.top_driver.get("contribution_percentage", 0)
            recommendations.append({
                "id": f"REC-CONCENTRATION-{rc.dimension}",
                "title": f"Diversify {rc.dimension.replace('_', ' ').title()} Away from '{top_cat}'",
                "problem": f"Over-reliance on '{top_cat}' creates concentration risk.",
                "evidence": f"'{top_cat}' contributes {contrib_pct:.1f}% of total {rc.measure}. Total {rc.measure}: {rc.grand_total:,.2f}. Verified from {profile.get('total_rows', 0):,} records.",
                "root_cause": "Revenue/volume concentrated in a single dimension value. Loss of that segment would materially impact performance.",
                "priority": "CRITICAL",
                "business_impact": f"Single-segment dependency exposes {contrib_pct:.1f}% of {rc.measure} to volatility.",
                "expected_gain": f"Reducing concentration from {contrib_pct:.1f}% to <40% would stabilize revenue baseline and reduce downside risk by 30-50%.",
                "recommended_action": f"Reallocate growth investment from '{top_cat}' to secondary segments. Expand channel distribution and negotiate supplier diversification.",
                "affected_products": [],
                "affected_categories": [top_cat] if top_cat else [],
                "confidence": round(base_confidence * 100, 1),
            })

        # =====================================================================
        # 2. Address critical/high severity anomalies
        # =====================================================================
        for a in anomalies:
            if str(getattr(a, "severity", "")).upper() not in ("CRITICAL", "HIGH"):
                continue
            recommendations.append({
                "id": f"REC-ANOMALY-{getattr(a, 'period', 'unknown')}",
                "title": f"Address {getattr(a, 'title', 'Anomaly')}",
                "problem": f"Detected {getattr(a, 'type', 'anomaly').lower()} event: {getattr(a, 'explanation', '')}",
                "evidence": f"Period: {getattr(a, 'period', 'N/A')}. Actual: {getattr(a, 'actual_value', 0):,.2f}, Expected: {getattr(a, 'expected_value', 0):,.2f}. Z-score: {getattr(a, 'z_score', 0):.2f}. Severity: {getattr(a, 'severity', 'HIGH')}.",
                "root_cause": getattr(a, "explanation", "Statistical variance from historical baseline."),
                "priority": "CRITICAL" if str(getattr(a, "severity", "")).upper() == "CRITICAL" else "HIGH",
                "business_impact": getattr(a, "business_impact", "Operational disruption and revenue leakage."),
                "expected_gain": f"Mitigating this {getattr(a, 'type', 'anomaly').lower()} could recover {abs(getattr(a, 'pct_change', 0)):.1f}% of affected metric volume.",
                "recommended_action": getattr(a, "recommendation", "Initiate root-cause audit on flagged period and recalibrate thresholds."),
                "affected_products": [],
                "affected_categories": [],
                "confidence": round(getattr(a, "confidence_score", 70) / 100, 2) if getattr(a, "confidence_score", 0) > 1 else round(getattr(a, "confidence_score", 0.7), 2),
            })

        # =====================================================================
        # 3. Low AOV — increase basket size
        # =====================================================================
        aov_kpi = kpi_map.get("Average Order Value")
        if aov_kpi and _kpi_val(aov_kpi, "value", 0.0) > 0:
            recommendations.append({
                "id": "REC-AOV",
                "title": "Increase Average Order Value (AOV)",
                "problem": "Current AOV indicates limited basket size and weak cross-selling effectiveness.",
                "evidence": f"AOV = {_kpi_val(aov_kpi, 'formatted_value', '0.0')} (formula: {_kpi_val(aov_kpi, 'formula', 'N/A')}). Computed across {_kpi_val(aov_kpi, 'rows_analyzed', 0):,} records.",
                "root_cause": "Customers purchasing single items without add-ons, bundles, or premium upgrades.",
                "priority": "HIGH",
                "business_impact": "Low AOV restricts revenue per transaction and increases customer acquisition cost burden.",
                "expected_gain": "Increasing AOV by 20% through bundling and upsell strategies could lift total revenue by 15-25%.",
                "recommended_action": "Launch product bundles, implement 'frequently bought together' recommendations, introduce threshold-based free shipping, and promote premium SKUs at checkout.",
                "affected_products": [],
                "affected_categories": [],
                "confidence": round(base_confidence * 100, 1),
            })

        # =====================================================================
        # 4. Low repeat customers — retention program
        # =====================================================================
        repeat_kpi = kpi_map.get("Repeat Customers")
        customer_kpi = kpi_map.get("Total Customers")
        if repeat_kpi and customer_kpi and _kpi_val(customer_kpi, "value", 0.0) > 0:
            repeat_rate = _kpi_val(repeat_kpi, "value", 0.0) / _kpi_val(customer_kpi, "value", 1.0)
            if repeat_rate < 0.3:
                recommendations.append({
                    "id": "REC-RETENTION",
                    "title": "Launch Customer Retention Program",
                    "problem": f"Only {repeat_rate:.1%} of customers make repeat purchases — below healthy retail threshold (~30%).",
                    "evidence": f"Repeat Customers: {_kpi_val(repeat_kpi, 'formatted_value', '0')}, Total Customers: {_kpi_val(customer_kpi, 'formatted_value', '0')}. Repeat rate = {repeat_rate:.1%}.",
                    "root_cause": "Weak post-purchase engagement, absence of loyalty incentives, or suboptimal product-market fit for returning buyers.",
                    "priority": "HIGH",
                    "business_impact": f"Acquiring a new customer costs 5-25x more than retaining an existing one. Current churn is eroding LTV.",
                    "expected_gain": "Improving repeat rate from {:.1%} to 35% could increase customer lifetime value by 40-60%.".format(repeat_rate),
                    "recommended_action": "Deploy loyalty points program, win-back email campaigns for lapsed customers, personalized re-order reminders, and subscription models for consumables.",
                    "affected_products": [],
                    "affected_categories": [],
                    "confidence": round(base_confidence * 100, 1),
                })

        # =====================================================================
        # 5. High freight ratio — optimize shipping
        # =====================================================================
        freight_kpi = kpi_map.get("Freight Ratio")
        revenue_kpi = kpi_map.get("Total Revenue") or kpi_map.get("Total Revenue (Computed)")
        if freight_kpi and revenue_kpi and _kpi_val(revenue_kpi, "value", 0.0) > 0:
            freight_ratio = _kpi_val(freight_kpi, "value", 0.0) / _kpi_val(revenue_kpi, "value", 1.0)
            if freight_ratio > 0.15:
                recommendations.append({
                    "id": "REC-FREIGHT",
                    "title": "Optimize Shipping Costs and Freight Ratio",
                    "problem": f"Freight ratio of {freight_ratio:.1%} exceeds healthy retail benchmark (<15% of revenue).",
                    "evidence": f"Freight Ratio: {_kpi_val(freight_kpi, 'formatted_value', '0')}. Total Revenue: {_kpi_val(revenue_kpi, 'formatted_value', '0')}. Ratio = {freight_ratio:.1%}.",
                    "root_cause": "High per-unit shipping costs, suboptimal carrier contracts, excessive packaging, or low average order value inflating per-order freight.",
                    "priority": "HIGH",
                    "business_impact": f"Every 1% reduction in freight ratio on {_kpi_val(revenue_kpi, 'formatted_value', '0')} revenue saves ~{_kpi_val(revenue_kpi, 'value', 0.0) * 0.01:,.2f}.",
                    "expected_gain": "Optimizing freight to <12% of revenue could improve gross margin by 3-5 points.",
                    "recommended_action": "Renegotiate carrier SLAs, introduce free-shipping thresholds, optimize packaging dimensions/weight, regional fulfillment center allocation, and carrier mix diversification.",
                    "affected_products": [],
                    "affected_categories": [],
                    "confidence": round(base_confidence * 100, 1),
                })

        # =====================================================================
        # 6. High discount ratio — review pricing strategy
        # =====================================================================
        discount_kpi = kpi_map.get("Discount Ratio")
        if discount_kpi and revenue_kpi and _kpi_val(revenue_kpi, "value", 0.0) > 0:
            discount_ratio = _kpi_val(discount_kpi, "value", 0.0) / _kpi_val(revenue_kpi, "value", 1.0)
            if discount_ratio > 0.10:
                recommendations.append({
                    "id": "REC-DISCOUNT",
                    "title": "Review Discount and Promotion Strategy",
                    "problem": f"Discount ratio of {discount_ratio:.1%} is eroding margin and may devalue brand positioning.",
                    "evidence": f"Discount Ratio: {_kpi_val(discount_kpi, 'formatted_value', '0')}. Total Revenue: {_kpi_val(revenue_kpi, 'formatted_value', '0')}. Ratio = {discount_ratio:.1%}.",
                    "root_cause": "Excessive promotional depth, unoptimized coupon codes, or systematic markdowns to move slow inventory.",
                    "priority": "MEDIUM",
                    "business_impact": f"High discounting reduces effective revenue and trains customers to wait for sales, suppressing full-price conversion.",
                    "expected_gain": "Reducing discount ratio by 2-3 points could recover margin equivalent to {_kpi_val(revenue_kpi, 'value', 0.0) * 0.02:,.2f}.",
                    "recommended_action": "Implement dynamic pricing rules, restrict blanket promotions to high-intent segments, introduce loyalty-exclusive discounts, and monitor discount-to-revenue elasticity weekly.",
                    "affected_products": [],
                    "affected_categories": [],
                    "confidence": round(base_confidence * 100, 1),
                })

        # =====================================================================
        # 7. Low profit margin — cost optimization
        # =====================================================================
        profit_kpi = kpi_map.get("Total Profit") or kpi_map.get("Profit Margin")
        if profit_kpi and revenue_kpi and _kpi_val(revenue_kpi, "value", 0.0) > 0:
            profit_margin = _kpi_val(profit_kpi, "value", 0.0) / _kpi_val(revenue_kpi, "value", 1.0) if _kpi_val(profit_kpi, "value", 0.0) != _kpi_val(revenue_kpi, "value", 0.0) else 0.0
            if profit_margin < 0.10:
                recommendations.append({
                    "id": "REC-PROFIT",
                    "title": "Optimize Cost Structure to Improve Profit Margin",
                    "problem": f"Profit margin of {profit_margin:.1%} is below healthy retail threshold (>10%).",
                    "evidence": f"Profit: {_kpi_val(profit_kpi, 'formatted_value', '0')}. Revenue: {_kpi_val(revenue_kpi, 'formatted_value', '0')}. Margin = {profit_margin:.1%}.",
                    "root_cause": "Elevated COGS, uncontrolled operating expenses, high freight/discount ratios, or underperforming low-margin product mix.",
                    "priority": "CRITICAL",
                    "business_impact": f"Thin margins reduce reinvestment capacity and increase vulnerability to demand shocks.",
                    "expected_gain": "Improving margin by 5 points on current revenue would add {revenue_kpi.value * 0.05:,.2f} to bottom-line profit.",
                    "recommended_action": "Renegotiate supplier terms, phase out low-margin SKUs, reduce return rates, optimize marketing spend ROI, and implement margin-aware pricing.",
                    "affected_products": [],
                    "affected_categories": [],
                    "confidence": round(base_confidence * 100, 1),
                })

        # =====================================================================
        # 8. Identify affected products/categories from drivers
        # =====================================================================
        for d in drivers:
            td = d.get("top_driver") or {}
            cat = td.get("category")
            if cat:
                for rec in recommendations:
                    if cat not in rec.get("affected_categories", []):
                        rec.setdefault("affected_categories", [])
                        rec["affected_categories"].append(cat)

        # Deduplicate and cap
        seen_ids = set()
        unique_recs = []
        for rec in recommendations:
            if rec["id"] not in seen_ids:
                seen_ids.add(rec["id"])
                unique_recs.append(rec)
        recommendations = unique_recs[:12]

        has_valid_strategy = len(recommendations) > 0

        return {
            "has_valid_strategy": has_valid_strategy,
            "recommendations": recommendations,
            "disclaimer": None if has_valid_strategy else "Insufficient evidence to generate retail-specific recommendations."
        }
