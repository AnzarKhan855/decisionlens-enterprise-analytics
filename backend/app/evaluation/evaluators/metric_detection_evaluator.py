from typing import Any, Dict, List


def evaluate_metric_detection(
    dataset_info: Dict[str, Any],
    detection_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Evaluates metric detection accuracy against expected metrics.

    Tests:
    - Are expected numeric measures detected?
    - Are detected metrics actually valid metrics?
    - Precision and recall of metric detection
    """
    scores = []
    details = {}

    expected_metrics = set(dataset_info.get("expected_metrics", []))
    detected_metrics = set(detection_result.get("metrics", [])) if isinstance(detection_result.get("metrics"), list) else set()

    if not detected_metrics:
        detected_metrics = set(detection_result.get("identified_metrics", [])) if isinstance(detection_result.get("identified_metrics"), list) else set()

    if not detected_metrics and "profile_summary" in detection_result:
        measures = detection_result["profile_summary"].get("measures", [])
        detected_metrics = set(measures)

    true_positives = len(expected_metrics & detected_metrics)
    false_positives = len(detected_metrics - expected_metrics)
    false_negatives = len(expected_metrics - detected_metrics)

    precision = true_positives / max(true_positives + false_positives, 1)
    recall = true_positives / max(true_positives + false_negatives, 1)
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    scores.append(("metric_detection_f1", round(f1, 4), 1.0))
    details["metric_detection"] = {
        "expected": list(expected_metrics),
        "detected": list(detected_metrics),
        "true_positives": list(expected_metrics & detected_metrics),
        "false_positives": list(detected_metrics - expected_metrics),
        "false_negatives": list(expected_metrics - detected_metrics),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }

    metric_type_check = 0
    for m in detected_metrics:
        if m.lower() in ("total_revenue", "quantity", "unit_price", "cost", "profit", "discount_pct",
                          "balance", "amount", "interest_rate", "credit_score",
                          "total_charges", "insurance_coverage", "admission_days", "satisfaction_score", "age",
                          "salary", "years_at_company", "performance_rating",
                          "impressions", "clicks", "cost", "conversions", "revenue", "ctr", "roi",
                          "gpa", "credits_completed", "tuition", "scholarship",
                          "quantity", "unit_cost", "total_cost", "lead_time_days", "defect_rate", "throughput"):
            metric_type_check += 1
    metric_type_score = metric_type_check / max(len(detected_metrics), 1) if detected_metrics else 1.0
    scores.append(("metric_type_correctness", round(metric_type_score, 4), 1.0))
    details["metric_type_correctness"] = {
        "detected_metrics": list(detected_metrics),
        "valid_metric_count": metric_type_check,
        "score": round(metric_type_score, 4),
    }

    overall = sum(s[1] * s[2] for s in scores) / sum(s[2] for s in scores) if scores else 0.0
    return round(overall, 4), details