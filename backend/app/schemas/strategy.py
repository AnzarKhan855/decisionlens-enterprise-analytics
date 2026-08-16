from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BusinessDriver:
    id: str
    name: str
    driver_type: str
    impact_score: float
    contribution_percentage: float
    trend: str
    confidence: float
    evidence: str = ""
    supporting_kpis: List[str] = field(default_factory=list)


@dataclass
class RiskItem:
    id: str
    title: str
    category: str
    probability: str
    severity: str
    business_impact: str
    recommended_mitigation: str
    confidence: float = 0.0
    affected_kpis: List[str] = field(default_factory=list)
    evidence: str = ""


@dataclass
class OpportunityItem:
    id: str
    title: str
    category: str
    priority: str
    potential_value: str
    timeline: str
    action: str
    confidence: float = 0.0
    supporting_kpis: List[str] = field(default_factory=list)
    evidence: str = ""


@dataclass
class ExecutiveRecommendation:
    id: str
    title: str
    category: str
    priority: str
    reason: str
    action: str
    supporting_kpis: List[str] = field(default_factory=list)
    evidence: str = ""
    expected_impact: str = ""
    estimated_roi: str = ""
    implementation_difficulty: str = "Medium"
    timeline: str = ""
    confidence: float = 0.0
    risk_level: str = "LOW"
    expected_gain: str = ""
    business_impact: str = ""


@dataclass
class ScenarioAnalysis:
    scenario_name: str
    case_type: str
    projected_revenue: float
    projected_profit: Optional[float]
    revenue_change_pct: float
    profit_change_pct: Optional[float]
    risk_level: str
    confidence: float
    key_assumptions: List[str] = field(default_factory=list)
    business_interpretation: str = ""


@dataclass
class BusinessImpact:
    revenue_gain: float = 0.0
    revenue_loss: float = 0.0
    profit_gain: float = 0.0
    profit_loss: float = 0.0
    cost_reduction: float = 0.0
    efficiency_improvement: str = ""
    customer_growth: float = 0.0
    market_share_impact: str = ""


@dataclass
class DecisionNode:
    id: str
    title: str
    description: str
    impact: str
    risk: str
    roi: str
    recommendation: str
    children: List["DecisionNode"] = field(default_factory=list)


@dataclass
class CrossKPIRelationship:
    source_kpi: str
    target_kpi: str
    relationship: str
    explanation: str
    confidence: float


@dataclass
class ExecutiveSummary:
    headline: str
    key_findings: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    business_impact: str = ""
    risks: List[str] = field(default_factory=list)
    opportunities: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    expected_outcome: str = ""
    confidence: float = 0.0


@dataclass
class StrategyReport:
    workspace_id: str
    domain: str = "Generic Business"
    dataset_type: str = "Unknown"
    generated_at: str = ""
    executive_summary: ExecutiveSummary = field(default_factory=lambda: ExecutiveSummary(headline=""))
    business_drivers: List[BusinessDriver] = field(default_factory=list)
    root_causes: List[Dict[str, Any]] = field(default_factory=list)
    risks: List[RiskItem] = field(default_factory=list)
    opportunities: List[OpportunityItem] = field(default_factory=list)
    recommendations: List[ExecutiveRecommendation] = field(default_factory=list)
    decision_tree: Optional[DecisionNode] = None
    scenario_analysis: List[ScenarioAnalysis] = field(default_factory=list)
    business_impact: BusinessImpact = field(default_factory=BusinessImpact)
    cross_kpi_relationships: List[CrossKPIRelationship] = field(default_factory=list)
    confidence_score: float = 0.0
    evidence: Dict[str, Any] = field(default_factory=dict)
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
