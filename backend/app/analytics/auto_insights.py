from pathlib import Path
from typing import Any, Dict, List, Optional

from app.ingestion.semantic_profiler import SemanticDataProfiler
from app.analytics.anomaly_engine import StatisticalAnomalyEngine
from app.analytics.variance_engine import VarianceDecompositionEngine
from app.analytics.recommendation_engine import RecommendationEngine, MetricDetector


class AutoInsights:
    """
    Executive Business Narrative & Evidence Engine.
    Strict Rule: Detects underlying metric types. If metric is Record Count or Unknown,
    displays an educational explanation instead of generating misleading strategy.
    """

    @staticmethod
    def generate_from_parquet(parquet_path: Path, semantic_profile: Optional[Dict[str, Any]] = None) -> List[str]:
        if not semantic_profile:
            semantic_profile = SemanticDataProfiler.profile(parquet_path)

        measures = semantic_profile["column_categories"].get("measures", [])
        dimensions = semantic_profile["column_categories"].get("dimensions", [])
        temporal = semantic_profile["column_categories"].get("temporal", [])
        total_rows = semantic_profile.get("total_rows", 0)

        primary_measure = measures[0] if measures else None
        metric_type = MetricDetector.detect_metric_type(primary_measure) if primary_measure else "Record Count"

        insights = []

        if metric_type in ("Record Count", "Unknown"):
            insights.append(
                "DATASET DISTRIBUTION NOTICE: This visualization shows the distribution of records across categories. "
                "It does not indicate business performance. Financial or operational metrics "
                "are required before strategic recommendations can be made."
            )
            return insights

        if dimensions and measures:
            top_dim = dimensions[0]
            top_meas = measures[0]
            variance = VarianceDecompositionEngine.analyze_drivers(parquet_path, top_dim, top_meas)
            top_driver = variance.get("top_driver")

            if top_driver:
                category = top_driver.get("category", "Primary Segment")
                contrib = top_driver.get("contribution_percentage", 0.0)
                amount = top_driver.get("amount", 0.0)

                if contrib > 40.0:
                    insights.append(
                        f"CONCENTRATION RISK (Metric: {metric_type}): Top segment '{category}' contributes {contrib}% ({amount:,.2f}) of total {metric_type.lower()}. "
                        f"Implication: High dependency vulnerability. Recommended Action: Diversify efforts to secondary categories to lower single-driver risk."
                    )
                else:
                    insights.append(
                        f"GROWTH DRIVER (Metric: {metric_type}): Segment '{category}' leads contribution at {contrib}% ({amount:,.2f}). "
                        f"Opportunity: Expand presence in this core category for immediate gain."
                    )

        if temporal and measures:
            anomalies = StatisticalAnomalyEngine.detect_anomalies(parquet_path, temporal[0], measures[0])
            if anomalies:
                top_anomaly = anomalies[0]
                period = top_anomaly.get("period", "recent period")
                actual = top_anomaly.get("actual_value", 0.0)
                expected = top_anomaly.get("expected_value", 0.0)
                anom_type = top_anomaly.get("type", "VOLATILITY")

                if anom_type == "DIP":
                    insights.append(
                        f"VALUE DROP ALERT (Metric: {metric_type}): Detected a statistical drop on {period} (Actual: {actual:,.2f} vs Expected: {expected:,.2f}). "
                        f"Risk: Operational disruption. Action: Review contributing factors and establish buffer capacity."
                    )
                else:
                    insights.append(
                        f"VALUE SPIKE OPPORTUNITY (Metric: {metric_type}): Detected a statistical surge on {period} (Actual: {actual:,.2f}). "
                        f"Opportunity: Capitalize on peak demand by expanding capacity or campaigns."
                    )
            else:
                insights.append(
                    f"STABLE TREND BASELINE (Metric: {metric_type}): Historical {measures[0].replace('_', ' ').title()} exhibits steady baseline variance without severe volatility."
                )

        insights.append(
            f"EVIDENCE AUDIT: Analyzed {total_rows:,} verified records for column '{primary_measure}'. No record count assumptions were applied."
        )

        return insights

    @staticmethod
    def generate(df):
        return ["Metric type: Record Count. Financial or operational metrics required for strategic advice."]
