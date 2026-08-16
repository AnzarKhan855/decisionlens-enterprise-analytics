from typing import Any, Dict, List, Optional
from pathlib import Path

from app.semantic_model.core import TargetVariable
from app.ingestion.semantic_profiler import SemanticDataProfiler


TARGET_VARIABLE_KEYWORDS = [
    "target", "label", "outcome", "result", "prediction",
    "churn", "default", "fraud", "attack", "malicious",
    "benign", "severity", "classification", "category",
    "pass_fail", "result", "status", "is_fraud", "is_churn",
    "is_default", "is_attack", "is_returns", "is_complaint",
    "converted", "clicked", "purchased", "subscribed",
    "renewed", "cancelled", "left", "attrition", "breach",
    "claim", "readmission", "satisfaction", "delinquent",
]

BINARY_OUTCOME_KEYWORDS = [
    "is_", "has_", "flag", "indicator", "binary", "yes_no",
    "true_false", "pass_fail", "churn", "default", "fraud",
    "attack", "malicious", "benign", "breach", "cancelled",
    "converted", "clicked", "subscribed", "renewed", "returns",
    "complaint", "readmission",
]

NUMERIC_TARGET_KEYWORDS = [
    "score", "grade", "amount", "revenue", "sales", "cost",
    "profit", "quantity", "value", "duration", "probability",
    "risk", "likelihood", "confidence", "prediction",
    "expected", "forecast", "estimate", "margin", "discount",
]


def detect_target_variables(
    parquet_path: Path,
    profile: Optional[Dict[str, Any]] = None,
    semantic_model: Optional[Dict[str, Any]] = None,
) -> List[TargetVariable]:
    if profile is None:
        profile = SemanticDataProfiler.profile(parquet_path)

    table_name = semantic_model.get("table_name", parquet_path.stem) if semantic_model else parquet_path.stem
    columns_profile = profile.get("columns", {})
    col_names = list(columns_profile.keys())
    total_rows = profile.get("total_rows", 0)

    targets = []

    for col_name in col_names:
        col_lower = col_name.lower()
        col_profile = columns_profile.get(col_name, {})

        is_target_candidate = False
        variable_type = "unknown"
        confidence = 0.0
        reason = ""

        for kw in TARGET_VARIABLE_KEYWORDS:
            if kw in col_lower:
                is_target_candidate = True
                break

        if not is_target_candidate:
            continue

        col_type = col_profile.get("data_type", "").upper()
        category = col_profile.get("category", "unknown")
        distinct_ratio = col_profile.get("distinct_count", 0) / max(total_rows, 1)
        null_rate = col_profile.get("null_percentage", 0) / 100.0

        is_binary = (
            distinct_ratio < 0.05
            or any(kw in col_lower for kw in BINARY_OUTCOME_KEYWORDS)
            or any(kw in col_type for kw in ["BOOL", "BOOLEAN"])
        )

        if is_binary:
            variable_type = "binary_classification"
            confidence = 0.8
            if distinct_ratio < 0.05:
                confidence += 0.1
            if null_rate < 0.1:
                confidence += 0.05
            reason = f"Column '{col_name}' has low cardinality ({col_profile.get('distinct_count', 0)} distinct values) indicating a binary classification target."
        elif any(kw in col_lower for kw in NUMERIC_TARGET_KEYWORDS) or category == "measure":
            variable_type = "regression"
            confidence = 0.75
            if category == "measure":
                confidence += 0.1
            if null_rate < 0.1:
                confidence += 0.05
            reason = f"Column '{col_name}' is numeric with measure characteristics suitable for regression prediction."
        elif category == "dimension" and distinct_ratio > 0.01 and distinct_ratio < 0.5:
            variable_type = "multiclass_classification"
            confidence = 0.7
            if distinct_ratio < 0.1:
                confidence += 0.1
            reason = f"Column '{col_name}' is a categorical dimension with {col_profile.get('distinct_count', 0)} unique values suitable for multiclass classification."
        else:
            variable_type = "unknown"
            confidence = 0.3
            reason = f"Column '{col_name}' matches target keywords but its type is ambiguous for prediction."

        confidence = min(0.99, confidence)

        targets.append(TargetVariable(
            column=col_name,
            table=table_name,
            variable_type=variable_type,
            confidence=round(confidence, 2),
            reason=reason,
            is_prediction_target=is_target_candidate,
        ))

    return targets