from typing import Any, Dict, List


def evaluate_dataset_understanding(
    dataset_info: Dict[str, Any],
    profile_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Evaluates how well the AI understands a dataset schema and domain.

    Tests:
    - Can it identify the domain correctly?
    - Can it summarize the dataset schema?
    - Can it count rows and columns accurately?
    - Does it identify the right column types?
    """
    scores = []
    details = {}

    expected_domain = dataset_info.get("domain", "")
    detected_domain = profile_result.get("domain_hints", {}).get("primary_domain", "")
    domain_match = expected_domain.lower() in detected_domain.lower() or detected_domain.lower() in expected_domain.lower()
    domain_score = 1.0 if domain_match else 0.5
    scores.append(("domain_identification", domain_score, 1.0))
    details["domain_identification"] = {
        "expected": expected_domain,
        "detected": detected_domain,
        "correct": domain_match,
    }

    expected_columns = dataset_info.get("expected_metrics", []) + dataset_info.get("expected_dimensions", [])
    detected_columns = profile_result.get("profile_summary", {}).get("measures", []) + profile_result.get("profile_summary", {}).get("dimensions", [])
    expected_count = len(expected_columns)
    detected_count = len(detected_columns)
    column_recall = min(1.0, detected_count / max(expected_count, 1)) if expected_count > 0 else 1.0
    column_precision = min(1.0, detected_count / max(expected_count, 1)) if expected_count > 0 else 1.0
    f1 = (2 * column_recall * column_precision) / (column_recall + column_precision) if (column_recall + column_precision) > 0 else 0.0
    scores.append(("column_detection", round(f1, 4), 1.0))
    details["column_detection"] = {
        "expected_count": expected_count,
        "detected_count": detected_count,
        "expected_columns": expected_columns,
        "detected_columns": detected_columns,
        "f1_score": round(f1, 4),
    }

    total_rows = dataset_info.get("total_rows", 1)
    detected_rows = profile_result.get("total_rows", 0)
    row_accuracy = 1.0 if total_rows == detected_rows else (min(total_rows, detected_rows) / max(total_rows, detected_rows))
    scores.append(("row_count_accuracy", row_accuracy, 1.0))
    details["row_count_accuracy"] = {
        "expected": total_rows,
        "detected": detected_rows,
        "correct": total_rows == detected_rows,
    }

    expected_entities = dataset_info.get("expected_entities", [])
    detected_entities = list(profile_result.get("entities", {}).keys())
    entity_recall = len(set(expected_entities) & set(detected_entities)) / max(len(expected_entities), 1)
    entity_precision = len(set(expected_entities) & set(detected_entities)) / max(len(detected_entities), 1)
    entity_f1 = (2 * entity_recall * entity_precision) / (entity_recall + entity_precision) if (entity_recall + entity_precision) > 0 else 0.0
    scores.append(("entity_schema_understanding", round(entity_f1, 4), 1.0))
    details["entity_schema_understanding"] = {
        "expected_entities": expected_entities,
        "detected_entities": detected_entities,
        "match_count": len(set(expected_entities) & set(detected_entities)),
        "f1_score": round(entity_f1, 4),
    }

    overall = sum(s[1] * s[2] for s in scores) / sum(s[2] for s in scores) if scores else 0.0
    return round(overall, 4), details