from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DynamicKPICard:
    title: str
    value: Any
    formatted_value: str
    confidence: float
    business_meaning: str
    evidence: str
    why_it_matters: str
    trend: str
    status: str
    importance: str
    priority: str
    metric_type: str = ""
    source_column: str = ""
    formula: str = ""
    rows_analyzed: int = 0
    category: str = ""
    rank_score: float = 0.0
    trend_value: str = ""
    change_pct: Optional[float] = None
    comparison_period: str = ""
    data_source: str = ""


@dataclass
class ChartRecommendation:
    chart_type: str
    title: str
    x_axis: str
    y_axis: str
    reason: str
    required_columns: List[str] = field(default_factory=list)
    confidence: float = 0.0
    priority: str = "MEDIUM"


@dataclass
class BusinessFinding:
    id: str
    title: str
    category: str
    severity: str
    description: str
    evidence: str
    impact: str = ""


@dataclass
class ExecutiveSummary:
    top_5_findings: List[BusinessFinding] = field(default_factory=list)
    top_5_risks: List[BusinessFinding] = field(default_factory=list)
    top_5_opportunities: List[BusinessFinding] = field(default_factory=list)
    critical_metrics: List[str] = field(default_factory=list)
    fastest_growing_segment: str = ""
    weakest_segment: str = ""
    largest_contributor: str = ""
    most_stable_indicator: str = ""


@dataclass
class DynamicKPIResult:
    workspace_id: str
    domain: str
    dataset_type: str
    generated_at: str
    kpi_cards: Dict[str, List[DynamicKPICard]] = field(default_factory=dict)
    executive_summary: ExecutiveSummary = field(default_factory=ExecutiveSummary)
    chart_recommendations: List[ChartRecommendation] = field(default_factory=list)
    business_findings: List[BusinessFinding] = field(default_factory=list)
    dashboard_metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
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
            elif isinstance(val, dict):
                result[f] = {
                    k: (v.to_dict() if hasattr(v, "to_dict") else (
                        {kk: vv for kk, vv in v.__dict__.items()} if hasattr(v, "__dict__") else v
                    ))
                    for k, v in val.items()
                }
            elif hasattr(val, "__dict__"):
                result[f] = {k: v for k, v in val.__dict__.items()}
            else:
                result[f] = val
        return result
