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
        def _serialize(obj: Any) -> Any:
            if hasattr(obj, "to_dict") and callable(obj.to_dict) and obj is not self:
                return obj.to_dict()
            elif isinstance(obj, dict):
                return {k: _serialize(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple, set)):
                return [_serialize(item) for item in obj]
            elif hasattr(obj, "__dataclass_fields__"):
                return {f: _serialize(getattr(obj, f)) for f in obj.__dataclass_fields__}
            elif hasattr(obj, "__dict__"):
                return {k: _serialize(v) for k, v in obj.__dict__.items()}
            return obj

        result = {}
        for f in self.__dataclass_fields__:
            val = getattr(self, f)
            result[f] = _serialize(val)
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AnalyticsResult:
        if not isinstance(data, dict):
            return cls()
        data_copy = dict(data)

        def _instantiate(dc_cls: Any, d: Any) -> Any:
            if not isinstance(d, dict):
                return d
            if hasattr(dc_cls, "__dataclass_fields__"):
                known = set(dc_cls.__dataclass_fields__.keys())
                filtered = {k: v for k, v in d.items() if k in known}
                return dc_cls(**filtered)
            return d

        if "kpis" in data_copy and isinstance(data_copy["kpis"], list):
            data_copy["kpis"] = [_instantiate(KPIMetric, k) for k in data_copy["kpis"]]
        if "distributions" in data_copy and isinstance(data_copy["distributions"], dict):
            data_copy["distributions"] = {
                cat: [_instantiate(DistributionItem, item) for item in items]
                for cat, items in data_copy["distributions"].items()
                if isinstance(items, list)
            }
        if "trends" in data_copy and isinstance(data_copy["trends"], dict):
            data_copy["trends"] = {
                m: [_instantiate(TrendPoint, tp) for tp in points]
                for m, points in data_copy["trends"].items()
                if isinstance(points, list)
            }
        if "growth" in data_copy and isinstance(data_copy["growth"], list):
            data_copy["growth"] = [_instantiate(GrowthDecline, g) for g in data_copy["growth"]]
        if "decline" in data_copy and isinstance(data_copy["decline"], list):
            data_copy["decline"] = [_instantiate(GrowthDecline, d) for d in data_copy["decline"]]
        if "rankings" in data_copy and isinstance(data_copy["rankings"], dict):
            data_copy["rankings"] = {
                cat: [_instantiate(RankItem, item) for item in items]
                for cat, items in data_copy["rankings"].items()
                if isinstance(items, list)
            }
        if "root_causes" in data_copy and isinstance(data_copy["root_causes"], list):
            data_copy["root_causes"] = [_instantiate(RootCause, rc) for rc in data_copy["root_causes"]]
        if "correlations" in data_copy and isinstance(data_copy["correlations"], list):
            data_copy["correlations"] = [_instantiate(Correlation, c) for c in data_copy["correlations"]]
        if "anomalies" in data_copy and isinstance(data_copy["anomalies"], list):
            data_copy["anomalies"] = [_instantiate(AnomalyItem, a) for a in data_copy["anomalies"]]
        if "outliers" in data_copy and isinstance(data_copy["outliers"], list):
            data_copy["outliers"] = [_instantiate(OutlierItem, o) for o in data_copy["outliers"]]
        if "recommendations" in data_copy and isinstance(data_copy["recommendations"], list):
            data_copy["recommendations"] = [_instantiate(RecommendationItem, rec) for rec in data_copy["recommendations"]]
        if "risks" in data_copy and isinstance(data_copy["risks"], list):
            data_copy["risks"] = [_instantiate(RiskItem, r) for r in data_copy["risks"]]
        if "opportunities" in data_copy and isinstance(data_copy["opportunities"], list):
            data_copy["opportunities"] = [_instantiate(OpportunityItem, o) for o in data_copy["opportunities"]]
        if "health_score" in data_copy and isinstance(data_copy["health_score"], dict):
            data_copy["health_score"] = _instantiate(HealthScore, data_copy["health_score"])
        if "evidence_report" in data_copy and isinstance(data_copy["evidence_report"], dict):
            data_copy["evidence_report"] = _instantiate(EvidenceReport, data_copy["evidence_report"])

        known_fields = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in data_copy.items() if k in known_fields}
        return cls(**filtered)
