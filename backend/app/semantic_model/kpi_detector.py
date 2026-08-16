from typing import Any, Dict, List, Optional
from pathlib import Path

from app.semantic_model.core import KPI
from app.semantic_model.measure_detector import MEASURE_AGGREGATION_MAP
from app.ingestion.semantic_profiler import SemanticDataProfiler


KPI_CANDIDATE_KEYWORDS = [
    "revenue", "sales", "amount", "total", "profit", "cost", "price",
    "quantity", "count", "value", "balance", "fee", "tax", "margin",
    "rate", "percentage", "score", "grade", "salary", "income", "expense",
    "discount", "bonus", "commission", "payout", "claim", "premium",
    "duration", "size", "weight", "distance", "speed", "volume",
    "utilization", "capacity", "throughput", "efficiency", "conversion",
    "roi", "mrr", "arr", "ltv", "cac", "churn", "nps", "ctr", "cpc",
    "cpa", "roas", "oee", "yield", "mortality", "readmission", "attrition",
]

KPI_AGGREGATION_MAP = {
    "revenue": "SUM", "sales": "SUM", "amount": "SUM", "total": "SUM",
    "profit": "SUM", "cost": "SUM", "price": "SUM", "balance": "SUM",
    "salary": "SUM", "income": "SUM", "expense": "SUM", "payout": "SUM",
    "claim": "SUM", "premium": "SUM", "fee": "SUM", "tax": "SUM",
    "quantity": "SUM", "volume": "SUM", "throughput": "SUM",
    "count": "COUNT", "count_order": "COUNT",
    "discount": "AVG", "margin": "AVG", "rate": "AVG", "percentage": "AVG",
    "score": "AVG", "grade": "AVG", "efficiency": "AVG", "utilization": "AVG",
    "conversion": "AVG", "ctr": "AVG", "cpc": "AVG", "cpa": "AVG",
    "roas": "AVG", "nps": "AVG", "duration": "AVG", "size": "AVG",
    "weight": "AVG", "distance": "AVG", "speed": "AVG", "oee": "AVG",
    "yield": "AVG", "mortality": "AVG", "readmission": "AVG", "attrition": "AVG",
}


def detect_kpis(
    parquet_path: Path,
    profile: Optional[Dict[str, Any]] = None,
    semantic_model: Optional[Dict[str, Any]] = None,
) -> List[KPI]:
    if profile is None:
        profile = SemanticDataProfiler.profile(parquet_path)

    measures = profile.get("column_categories", {}).get("measures", [])
    columns_profile = profile.get("columns", {})
    total_rows = profile.get("total_rows", 0)
    table_name = semantic_model.get("table_name", parquet_path.stem) if semantic_model else parquet_path.stem

    kpis = []
    for col_name in measures:
        col_lower = col_name.lower()
        col_profile = columns_profile.get(col_name, {})

        metric_type = _classify_kpi_type(col_lower)
        agg = _get_aggregation(col_lower)

        value = 0.0
        unit = ""
        if col_profile and "stats" in col_profile:
            stats = col_profile["stats"]
            if agg == "SUM" and "sum" in stats:
                value = stats["sum"]
            elif agg == "AVG" and "mean" in stats:
                value = stats["mean"]
            elif agg == "COUNT" and "count" in stats:
                value = stats["count"]
            elif "mean" in stats:
                value = stats["mean"]

        if any(k in col_lower for k in ["price", "cost", "salary", "income", "fee", "tax", "amount", "revenue", "balance", "payout", "premium", "claim"]):
            unit = "currency"
        elif any(k in col_lower for k in ["percentage", "rate", "score", "grade", "nps", "ctr", "cpc", "cpa", "roas"]):
            unit = "percent"
        elif any(k in col_lower for k in ["duration", "time", "lead_time"]):
            unit = "time"
        elif any(k in col_lower for k in ["quantity", "count", "volume", "size", "weight", "distance"]):
            unit = "count"

        confidence = _compute_kpi_confidence(col_profile, total_rows, metric_type)

        kpis.append(KPI(
            name=col_name,
            column=col_name,
            table=table_name,
            metric_type=metric_type,
            aggregation=agg,
            value=round(value, 4) if isinstance(value, float) else value,
            unit=unit,
            description=f"{metric_type} KPI derived from column '{col_name}' in table '{table_name}'.",
            confidence=round(confidence, 2),
            source_dataset=parquet_path.name,
        ))

    return kpis


def _classify_kpi_type(col_name: str) -> str:
    if any(k in col_name for k in ["revenue", "sales", "amount", "total", "profit", "balance", "income", "payout", "premium", "claim", "fee", "tax", "bonus", "commission"]):
        return "financial"
    if any(k in col_name for k in ["quantity", "count", "volume", "size", "weight", "distance", "speed"]):
        return "volume"
    if any(k in col_name for k in ["rate", "percentage", "ratio", "score", "grade", "nps", "ctr", "cpc", "cpa", "roas"]):
        return "ratio"
    if any(k in col_name for k in ["duration", "time", "lead_time", "response", "latency"]):
        return "temporal"
    if any(k in col_name for k in ["utilization", "capacity", "throughput", "efficiency", "oee"]):
        return "operational"
    if any(k in col_name for k in ["yield", "mortality", "readmission", "attrition", "churn"]):
        return "rate"
    return "numeric"


def _get_aggregation(col_name: str) -> str:
    col_lower = col_name.lower()
    for keyword, agg in KPI_AGGREGATION_MAP.items():
        if keyword in col_lower:
            return agg
    return "SUM"


def _compute_kpi_confidence(
    col_profile: Dict[str, Any],
    total_rows: int,
    metric_type: str,
) -> float:
    confidence = 0.5
    if total_rows > 0:
        confidence += 0.1
    if col_profile:
        null_pct = col_profile.get("null_percentage", 0)
        if null_pct < 5:
            confidence += 0.15
        elif null_pct < 20:
            confidence += 0.05
        distinct = col_profile.get("distinct_count", 0)
        if distinct > 10:
            confidence += 0.1
        if "stats" in col_profile:
            stats = col_profile["stats"]
            if "stddev" in stats and stats["stddev"] is not None and stats["stddev"] > 0:
                confidence += 0.05
    confidence = min(0.99, confidence)
    return confidence