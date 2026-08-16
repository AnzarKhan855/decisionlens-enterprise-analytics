from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RetailColumnSemantics:
    column_name: str
    semantic_role: str
    business_entity: str
    confidence: float
    evidence: str


@dataclass
class RetailEntity:
    entity_type: str
    matched_columns: List[str]
    confidence: float
    sample_values: List[Any] = field(default_factory=list)
    row_count: int = 0
    evidence: str = ""


@dataclass
class RetailKPI:
    name: str
    value: Any
    formatted_value: str
    business_explanation: str
    evidence: str
    confidence: float
    business_impact: str
    calculation: str
    available: bool = True
    source_columns: List[str] = field(default_factory=list)


@dataclass
class RetailHealthScore:
    overall_score: float = 0.0
    grade: str = "N/A"
    status: str = "No Data"
    breakdown: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class RetailAnalysisResult:
    domain: str
    dataset_type: str
    entities_detected: List[RetailEntity] = field(default_factory=list)
    column_semantics: List[RetailColumnSemantics] = field(default_factory=list)
    kpis: List[RetailKPI] = field(default_factory=list)
    top_categories: List[Dict[str, Any]] = field(default_factory=list)
    top_products: List[Dict[str, Any]] = field(default_factory=list)
    top_customers: List[Dict[str, Any]] = field(default_factory=list)
    revenue_trend: List[Dict[str, Any]] = field(default_factory=list)
    freight_analysis: List[Dict[str, Any]] = field(default_factory=list)
    delivery_performance: List[Dict[str, Any]] = field(default_factory=list)
    payment_analysis: List[Dict[str, Any]] = field(default_factory=list)
    review_analysis: List[Dict[str, Any]] = field(default_factory=list)
    store_performance: List[Dict[str, Any]] = field(default_factory=list)
    regional_performance: List[Dict[str, Any]] = field(default_factory=list)
    inventory_health: List[Dict[str, Any]] = field(default_factory=list)
    avg_order_value: Dict[str, Any] = field(default_factory=dict)
    order_count: Dict[str, Any] = field(default_factory=dict)
    customer_count: Dict[str, Any] = field(default_factory=dict)
    returning_customers: Dict[str, Any] = field(default_factory=dict)
    total_revenue: Dict[str, Any] = field(default_factory=dict)
    health_score: RetailHealthScore = field(default_factory=RetailHealthScore)
    forecast_readiness: Dict[str, Any] = field(default_factory=dict)
    computed_metrics: List[str] = field(default_factory=list)
    forecast: List[Dict[str, Any]] = field(default_factory=list)
    confidence_score: float = 0.0
    evidence: Dict[str, Any] = field(default_factory=dict)
    sql_queries: List[str] = field(default_factory=list)
    generated_at: str = ""
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        result = {}
        for f in self.__dataclass_fields__:
            val = getattr(self, f)
            if hasattr(val, "to_dict"):
                result[f] = val.to_dict()
            elif isinstance(val, list) and val and hasattr(val[0], "to_dict"):
                result[f] = [item.to_dict() for item in val]
            elif isinstance(val, list):
                result[f] = [
                    {k: v for k, v in item.__dict__.items()} if hasattr(item, "__dict__") else item
                    for item in val
                ]
            elif hasattr(val, "__dict__"):
                result[f] = {k: v for k, v in val.__dict__.items()}
            else:
                result[f] = val
        return result
