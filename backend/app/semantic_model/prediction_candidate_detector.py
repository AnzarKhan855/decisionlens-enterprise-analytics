from typing import Any, Dict, List, Optional
from pathlib import Path

from app.semantic_model.core import PredictionCandidate
from app.ingestion.semantic_profiler import SemanticDataProfiler


ALGORITHM_MAP = {
    "binary_classification": ["Logistic Regression", "Random Forest", "XGBoost", "LightGBM", "SVM", "Neural Network"],
    "multiclass_classification": ["Random Forest", "XGBoost", "LightGBM", "SVM", "Neural Network", "KNN"],
    "regression": ["Linear Regression", "Random Forest", "XGBoost", "LightGBM", "Neural Network", "Ridge", "Lasso"],
    "time_series": ["Prophet", "ARIMA", "LSTM", "XGBoost", "LightGBM", "Exponential Smoothing"],
    "clustering": ["k-Means", "DBSCAN", "Hierarchical", "Gaussian Mixture", "Random Forest (unsupervised)"],
}


def detect_prediction_candidates(
    parquet_path: Path,
    profile: Optional[Dict[str, Any]] = None,
    semantic_model: Optional[Dict[str, Any]] = None,
) -> List[PredictionCandidate]:
    if profile is None:
        profile = SemanticDataProfiler.profile(parquet_path)

    table_name = semantic_model.get("table_name", parquet_path.stem) if semantic_model else parquet_path.stem
    columns_profile = profile.get("columns", {})
    col_names = list(columns_profile.keys())
    total_rows = profile.get("total_rows", 0)
    measures = profile.get("column_categories", {}).get("measures", [])
    dimensions = profile.get("column_categories", {}).get("dimensions", [])
    temporal = profile.get("column_categories", {}).get("temporal", [])
    identifiers = profile.get("column_categories", {}).get("identifiers", [])

    candidates = []

    for col_name in col_names:
        col_lower = col_name.lower()
        col_profile = columns_profile.get(col_name, {})

        skip = False
        for kw in ["id", "key", "code", "uuid", "pk", "fk", "_id", "_key"]:
            if col_lower.endswith(kw) or col_lower == kw.replace("_", ""):
                skip = True
                break
        if skip:
            continue

        category = col_profile.get("category", "unknown")
        distinct_count = col_profile.get("distinct_count", 0)
        distinct_ratio = distinct_count / max(total_rows, 1)
        null_rate = col_profile.get("null_percentage", 0) / 100.0
        col_type = col_profile.get("data_type", "").upper()

        candidate_type = _classify_candidate_type(
            col_lower=col_lower,
            category=category,
            distinct_ratio=distinct_ratio,
            col_type=col_type,
            temporal=temporal,
            measures=measures,
            dimensions=dimensions,
            identifiers=identifiers,
        )

        if candidate_type == "none":
            continue

        confidence = _compute_candidate_confidence(
            col_profile=col_profile,
            total_rows=total_rows,
            distinct_ratio=distinct_ratio,
            null_rate=null_rate,
            candidate_type=candidate_type,
        )

        algorithms = ALGORITHM_MAP.get(candidate_type, ["Random Forest", "XGBoost"])

        reason = _generate_reason(col_name, candidate_type, col_profile, total_rows)

        candidates.append(PredictionCandidate(
            column=col_name,
            table=table_name,
            candidate_type=candidate_type,
            confidence=round(confidence, 2),
            reason=reason,
            suitable_algorithms=algorithms,
        ))

    return candidates


def _classify_candidate_type(
    col_lower: str,
    category: str,
    distinct_ratio: float,
    col_type: str,
    temporal: List[str],
    measures: List[str],
    dimensions: List[str],
    identifiers: List[str],
) -> str:
    is_temporal_col = any(t.lower() == col_lower for t in temporal)

    if any(kw in col_lower for kw in ["churn", "default", "fraud", "attack", "malicious", "benign", "cancelled", "converted", "clicked", "subscribed", "renewed", "returns", "breach", "complaint", "readmission", "attrition", "delinquent"]):
        if distinct_ratio < 0.05:
            return "binary_classification"
        return "multiclass_classification"

    if any(kw in col_lower for kw in ["score", "grade", "amount", "revenue", "sales", "cost", "profit", "quantity", "value", "duration", "probability", "risk", "likelihood", "margin", "discount"]):
        if category == "measure" or any(nt in col_type for nt in ["BIGINT", "INTEGER", "SMALLINT", "TINYINT", "DOUBLE", "FLOAT", "DECIMAL"]):
            if is_temporal_col or col_lower in measures:
                return "time_series"
            return "regression"

    if category == "dimension" and distinct_ratio > 0.01 and distinct_ratio < 0.5:
        return "multiclass_classification"

    if category == "measure" and distinct_ratio > 0.5:
        return "regression"

    return "none"


def _compute_candidate_confidence(
    col_profile: Dict[str, Any],
    total_rows: int,
    distinct_ratio: float,
    null_rate: float,
    candidate_type: str,
) -> float:
    confidence = 0.4

    if total_rows > 100:
        confidence += 0.15
    if total_rows > 1000:
        confidence += 0.1

    if col_profile:
        if null_rate < 0.1:
            confidence += 0.15
        elif null_rate < 0.2:
            confidence += 0.05

        if candidate_type in ("binary_classification", "multiclass_classification"):
            if distinct_ratio > 0.005 and distinct_ratio < 0.5:
                confidence += 0.15
        elif candidate_type == "regression":
            if distinct_ratio > 0.1:
                confidence += 0.1

        if "stats" in col_profile:
            stats = col_profile["stats"]
            if "stddev" in stats and stats["stddev"] is not None and stats["stddev"] > 0:
                confidence += 0.05

    confidence = min(0.99, confidence)
    return confidence


def _generate_reason(
    col_name: str,
    candidate_type: str,
    col_profile: Dict[str, Any],
    total_rows: int,
) -> str:
    distinct_count = col_profile.get("distinct_count", 0) if col_profile else 0
    type_desc = candidate_type.replace("_", " ").title()

    if candidate_type == "binary_classification":
        return f"Column '{col_name}' has low cardinality ({distinct_count} distinct values) making it suitable for binary classification with {total_rows:,} records."
    if candidate_type == "multiclass_classification":
        return f"Column '{col_name}' has {distinct_count} unique values suitable for multiclass classification with {total_rows:,} records."
    if candidate_type == "regression":
        return f"Column '{col_name}' is numeric with sufficient variance for regression modeling over {total_rows:,} records."
    if candidate_type == "time_series":
        return f"Column '{col_name}' is a temporal measure suitable for time-series forecasting over {total_rows:,} records."
    if candidate_type == "clustering":
        return f"Column '{col_name}' has {distinct_count} unique values suitable for clustering analysis."

    return f"Column '{col_name}' is a candidate for {type_desc} prediction."