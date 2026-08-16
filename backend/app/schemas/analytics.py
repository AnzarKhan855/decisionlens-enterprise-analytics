from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class EvidenceReport:
    evidence: str = ""
    confidence: float = 0.0
    rows_analyzed: int = 0
    columns_analyzed: List[str] = field(default_factory=list)
    business_reasoning: str = ""
    recommendation: str = ""
    expected_impact: str = ""
    priority: str = "LOW"
    models_used: List[str] = field(default_factory=list)
    sql_query: str = ""
    tables_used: List[str] = field(default_factory=list)
    validation_status: str = "UNKNOWN"
    disclaimer: str = ""
    prediction_feasible: bool = False
    prediction_limitation: Optional[str] = None
    anomalies_detected: int = 0
    drivers_identified: int = 0
    kpi_count: int = 0
    forecast_available: bool = False
    recommendation_count: int = 0
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class KPIMetric:
    name: str
    value: Any
    formatted_value: str
    metric_type: str
    source_column: str
    formula: str
    rows_analyzed: int
    confidence: float
    available: bool = True
    status: str = "Derived from Dataset"
    evidence: str = ""
    business_meaning: str = ""
    business_impact: str = ""


@dataclass
class DistributionItem:
    category: str
    value: float
    percentage: Optional[float] = None


@dataclass
class TrendPoint:
    period: str
    value: float
    change_pct: Optional[float] = None


@dataclass
class GrowthDecline:
    period: str
    value: float
    previous_value: Optional[float] = None
    change_pct: Optional[float] = None
    direction: str = "stable"


@dataclass
class RankItem:
    rank: int
    category: str
    value: float
    percentage: Optional[float] = None


@dataclass
class DriverContribution:
    category: str
    amount: float
    contribution_percentage: float
    cumulative_percentage: float


@dataclass
class RootCause:
    dimension: str
    measure: str
    grand_total: float
    top_driver: Optional[Dict[str, Any]] = None
    concentration_risk: bool = False
    drivers: List[DriverContribution] = field(default_factory=list)


@dataclass
class Correlation:
    column_a: str
    column_b: str
    coefficient: float
    strength: str
    significance: str = "moderate"


@dataclass
class SegmentComparison:
    segment_a: str
    segment_b: str
    metric: str
    value_a: float
    value_b: float
    difference_pct: float
    winner: str


@dataclass
class Outlier:
    period: str
    value: float
    expected_value: float
    z_score: float
    direction: str
    severity: str
    pct_change: float


@dataclass
class BusinessAnomaly:
    period: str
    title: str
    category: str
    severity: str
    type: str
    actual_value: float
    expected_value: float
    z_score: float
    pct_change: float
    explanation: str
    business_impact: str
    possible_causes: List[str] = field(default_factory=list)
    recommendation: str = ""
    confidence_score: float = 0.0


@dataclass
class Prediction:
    model_type: str
    model_used: str
    prediction: str
    confidence: float
    evidence: str
    business_impact: str
    time_horizon: str
    risk_level: str
    recommended_action: str
    metric: str = ""
    predicted_value: float = 0.0
    current_value: float = 0.0
    expected_change_pct: float = 0.0
    model_name: str = ""
    horizon: str = ""
    drivers: List[Dict[str, str]] = field(default_factory=list)
    time_series_points: List[Dict[str, Any]] = field(default_factory=list)
    feasible: bool = True
    limitation: Optional[str] = None
    assumptions: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    opportunities: List[str] = field(default_factory=list)
    prediction_interval: Optional[Tuple[float, float]] = None


@dataclass
class Recommendation:
    id: str
    title: str
    category: str
    priority: str
    reason: str
    action: str
    expected_roi: str
    financial_impact: str
    investment_required: str
    timeline: str
    confidence: float
    risk_level: str
    owner: str
    implementation_difficulty: str = "Medium"
    evidence: str = ""
    problem: str = ""
    root_cause: str = ""
    business_impact: str = ""
    expected_gain: str = ""
    affected_products: List[str] = field(default_factory=list)
    affected_categories: List[str] = field(default_factory=list)


@dataclass
class RiskItem:
    id: str
    title: str
    category: str
    severity: str
    description: str
    impact: str
    causes: List[str] = field(default_factory=list)
    mitigation: str = ""


@dataclass
class OpportunityItem:
    id: str
    title: str
    category: str
    priority: str
    description: str
    impact: str
    action: str
    timeline: str


@dataclass
class HealthScore:
    overall_score: float = 78.0
    grade: str = "B"
    status: str = "Good"
    breakdown: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class AnalyticsResult:
    # 1. WHAT HAPPENED
    executive_summary: str = ""
    kpis: List[KPIMetric] = field(default_factory=list)
    summary_statistics: Dict[str, Any] = field(default_factory=dict)
    distributions: Dict[str, List[DistributionItem]] = field(default_factory=dict)
    trends: Dict[str, List[TrendPoint]] = field(default_factory=dict)
    growth: List[GrowthDecline] = field(default_factory=list)
    decline: List[GrowthDecline] = field(default_factory=list)
    rankings: Dict[str, List[RankItem]] = field(default_factory=dict)
    volume: int = 0
    utilization: Dict[str, Any] = field(default_factory=dict)
    performance: Dict[str, Any] = field(default_factory=dict)

    # 2. WHY DID IT HAPPEN
    root_causes: List[RootCause] = field(default_factory=list)
    drivers: List[Dict[str, Any]] = field(default_factory=list)
    correlations: List[Correlation] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    dimension_impact: List[Dict[str, Any]] = field(default_factory=list)
    segment_comparisons: List[SegmentComparison] = field(default_factory=list)
    outliers: List[Outlier] = field(default_factory=list)
    anomalies: List[BusinessAnomaly] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)

    # 3. WHAT WILL HAPPEN
    predictions: List[Prediction] = field(default_factory=list)
    prediction_strategy: str = "none"
    prediction_feasible: bool = True
    prediction_limitation: Optional[str] = None
    forecast_summary: Dict[str, Any] = field(default_factory=dict)

    # 4. WHAT SHOULD WE DO
    recommendations: List[Recommendation] = field(default_factory=list)
    critical_findings: List[str] = field(default_factory=list)
    positive_findings: List[str] = field(default_factory=list)
    negative_findings: List[str] = field(default_factory=list)
    risks: List[RiskItem] = field(default_factory=list)
    opportunities: List[OpportunityItem] = field(default_factory=list)
    key_drivers: List[Dict[str, Any]] = field(default_factory=list)

    # Canonical Analytics Object (Phase 2 Universal Engine)
    workspace_id: str = ""
    dataset_summary: Dict[str, Any] = field(default_factory=dict)
    metrics: List[str] = field(default_factory=list)
    dimensions: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    charts: List[Dict[str, Any]] = field(default_factory=list)
    copilot_context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    forecast_ready: bool = False
    recommendation_ready: bool = False
    report_ready: bool = False

    # Metadata
    health_score: HealthScore = field(default_factory=lambda: HealthScore(overall_score=0.0, grade="N/A", status="No Data"))
    confidence_score: float = 0.0
    confidence: float = 0.0
    confidence_factors: Dict[str, float] = field(default_factory=dict)
    evidence: Dict[str, Any] = field(default_factory=dict)
    evidence_report: EvidenceReport = field(default_factory=EvidenceReport)
    tables_used: List[str] = field(default_factory=list)
    columns_used: List[str] = field(default_factory=list)
    sql_query: str = ""
    domain: str = "Generic Business"
    dataset_type: str = "Unknown"
    semantic_model: Optional[Any] = None
    canonical_model: Optional[Dict[str, Any]] = None
    revenue_formula: Optional[str] = None
    available_kpis: List[str] = field(default_factory=list)
    generated_at: str = ""
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        result = {}
        for f in self.__dataclass_fields__:
            val = getattr(self, f)
            if hasattr(val, "to_dict"):
                result[f] = val.to_dict()
            elif isinstance(val, list):
                result[f] = [
                    item.to_dict() if hasattr(item, "to_dict") else (
                        {k: v for k, v in item.__dict__.items()} if hasattr(item, "__dict__") else item
                    )
                    for item in val
                ]
            elif hasattr(val, "__dict__"):
                result[f] = {k: v for k, v in val.__dict__.items()}
            else:
                result[f] = val
        return result
