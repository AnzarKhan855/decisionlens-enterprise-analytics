from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class KPICard(BaseModel):
    name: str
    value: str
    formatted_value: str
    metric_type: str
    source_column: str
    formula: str
    rows_analyzed: int
    confidence: float
    available: bool = True
    status: str = "Derived from Dataset"
    insight: str = ""
    trend_value: str = ""
    change_pct: Optional[float] = None
    comparison_period: str = ""
    data_source: str = ""


class HealthCard(BaseModel):
    overall_score: float
    grade: str
    status: str
    breakdown: List[Dict[str, Any]] = []


class TrendCard(BaseModel):
    measure: str
    data_points: int
    latest_value: float
    latest_change_pct: Optional[float] = None
    direction: str = "stable"
    up_periods: int = 0
    down_periods: int = 0
    chart_data: List[Dict[str, Any]] = []


class RootCauseCard(BaseModel):
    dimension: str
    measure: str
    grand_total: float
    top_driver: Optional[Dict[str, Any]] = None
    concentration_risk: bool = False
    driver_count: int = 0
    drivers: List[Dict[str, Any]] = []


class PredictionCard(BaseModel):
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
    drivers: List[Dict[str, str]] = []
    time_series_points: List[Dict[str, Any]] = []
    feasible: bool = True
    limitation: Optional[str] = None
    scenarios: List[Dict[str, Any]] = []


class RiskCard(BaseModel):
    id: str
    title: str
    category: str
    severity: str
    description: str
    impact: str
    causes: List[str] = []
    mitigation: str = ""


class OpportunityCard(BaseModel):
    id: str
    title: str
    category: str
    priority: str
    description: str
    impact: str
    action: str
    timeline: str


class RecommendationCard(BaseModel):
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


class EvidenceCard(BaseModel):
    source: str
    query: str
    rows_returned: int
    columns_used: List[str] = []
    tables_used: List[str] = []
    snippet: str = ""
    confidence: float = 0.0


class ExecutiveHeroCard(BaseModel):
    greeting: str
    domain: str
    dataset_type: str
    total_records: int
    total_columns: int
    health_score: float
    health_status: str
    primary_kpi: str
    primary_kpi_value: str
    anomaly_count: int
    recommendation_count: int
    prediction_count: int
    ai_confidence: str
    forecast: str


class ChartSpec(BaseModel):
    id: str
    type: str
    title: str
    available: bool = True
    reason: str = ""
    required_columns: List[str] = []
    x_axis: str = ""
    y_axis: str = ""
    source_column: str = ""
    dimension_column: str = ""
    data: List[Dict[str, Any]] = []
    business_interpretation: str = ""
    confidence: float = 0.0
    evidence: str = ""


class ExplainabilityCard(BaseModel):
    overall_confidence: float
    evidence_score: float
    prediction_score: float
    recommendation_score: float
    risk_score: float
    confidence_factors: Dict[str, float] = {}
    why_generated: str = ""
    evidence_support: List[str] = []
    columns_used: List[str] = []
    tables_used: List[str] = []
    statistical_methods: List[str] = []
    assumptions: List[str] = []
    limitations: List[str] = []


class DashboardSection(BaseModel):
    id: str
    title: str
    description: str = ""
    order: int = 0
    cards: List[Any] = []
    charts: List[ChartSpec] = []
    metadata: Dict[str, Any] = {}


class DashboardResponse(BaseModel):
    generated_at: str
    domain: str
    dataset_type: str
    dataset_id: str
    workspace_id: str
    total_records: int
    total_columns: int
    hero: ExecutiveHeroCard
    sections: List[DashboardSection]
    kpi_cards: List[KPICard] = []
    kpis: List[Dict[str, Any]] = []
    health_card: Optional[HealthCard] = None
    charts: List[ChartSpec] = []
    evidence: List[EvidenceCard] = []
    copilot_suggestion: str = ""
    errors: List[str] = []
    predictions: List[Dict[str, Any]] = []
    ml_forecast: List[Dict[str, Any]] = []
    ml_segmentation: List[Dict[str, Any]] = []
    explainability: Optional[ExplainabilityCard] = None
    intelligence: Dict[str, Any] = {}
    forecast_summary: Dict[str, Any] = {}

    model_config = ConfigDict(arbitrary_types_allowed=True)
