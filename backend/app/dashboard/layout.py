from typing import Any, Dict, List, Optional

from app.dashboard.schema import DashboardSection, ChartSpec, KPICard, HealthCard


def get_section_order() -> List[str]:
    return [
        "hero",
        "kpis",
        "health",
        "trends",
        "segment_performance",
        "anomalies",
        "forecast",
        "opportunities",
        "risks",
        "recommendations",
        "insights",
        "scenarios",
        "evidence",
        "charts",
    ]


def build_sections(
    kpi_cards: List[KPICard],
    health_card: Optional[HealthCard],
    trend_cards: List[Any],
    root_cause_cards: List[Any],
    prediction_cards: List[Any],
    risk_cards: List[Any],
    opportunity_cards: List[Any],
    recommendation_cards: List[Any],
    charts: List[ChartSpec],
    evidence_cards: List[Any],
    analytics_dict: Dict[str, Any],
    anomaly_cards: Optional[List[Any]] = None,
    segment_cards: Optional[List[Any]] = None,
    insight_cards: Optional[List[Any]] = None,
    forecast_cards: Optional[List[Any]] = None,
) -> List[DashboardSection]:
    sections: List[DashboardSection] = []

    if kpi_cards:
        sections.append(DashboardSection(
            id="kpis",
            title="KPI Summary",
            description="Key performance indicators derived from the dataset.",
            order=1,
            cards=kpi_cards,
        ))

    if health_card:
        sections.append(DashboardSection(
            id="health",
            title="Executive Overview",
            description="Overall dataset and analytical health score.",
            order=2,
            cards=[health_card],
        ))

    if trend_cards:
        sections.append(DashboardSection(
            id="trends",
            title="Trends",
            description="Time-series trends and growth/decline patterns.",
            order=3,
            cards=trend_cards,
            charts=[c for c in charts if c.type in ("line", "area")],
        ))

    if segment_cards:
        sections.append(DashboardSection(
            id="segment_performance",
            title="Segment Performance",
            description="Performance breakdowns by dimension and segment comparisons.",
            order=4,
            cards=segment_cards,
        ))

    if anomaly_cards:
        sections.append(DashboardSection(
            id="anomalies",
            title="Anomalies",
            description="Detected anomalies and outliers requiring attention.",
            order=5,
            cards=anomaly_cards,
        ))

    if forecast_cards:
        sections.append(DashboardSection(
            id="forecast",
            title="Forecast",
            description="Projected future values and trends.",
            order=6,
            cards=forecast_cards,
            charts=[c for c in charts if c.type in ("line", "area") and "forecast" in (c.title or "").lower()],
        ))

    if opportunity_cards:
        sections.append(DashboardSection(
            id="opportunities",
            title="Opportunities",
            description="Growth opportunities and recommended actions.",
            order=7,
            cards=opportunity_cards,
        ))

    if risk_cards:
        sections.append(DashboardSection(
            id="risks",
            title="Risks",
            description="Identified risks and mitigation strategies.",
            order=8,
            cards=risk_cards,
        ))

    if recommendation_cards:
        sections.append(DashboardSection(
            id="recommendations",
            title="Recommended Actions",
            description="Evidence-based strategic recommendations.",
            order=9,
            cards=recommendation_cards,
        ))

    if insight_cards:
        sections.append(DashboardSection(
            id="insights",
            title="Insights",
            description="AI-generated business insights based on actual data.",
            order=10,
            cards=insight_cards,
        ))

    remaining_charts = [c for c in charts if c.type not in ("line", "area")]
    if remaining_charts:
        sections.append(DashboardSection(
            id="charts",
            title="Visualizations",
            description="Data visualizations with business interpretation.",
            order=11,
            charts=remaining_charts,
        ))

    if evidence_cards:
        sections.append(DashboardSection(
            id="evidence",
            title="Evidence Panel",
            description="SQL queries and data sources used for this analysis.",
            order=12,
            cards=evidence_cards,
        ))

    sections.sort(key=lambda s: s.order)
    return sections
