from typing import Any, Dict, List


def evaluate_entity_detection(
    dataset_info: Dict[str, Any],
    detection_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Evaluates entity detection accuracy against expected entities in the dataset.

    Tests:
    - Are the expected entities detected?
    - Are column-to-entity mappings correct?
    - Are there false positives or false negatives?
    """
    scores = []
    details = {}

    expected_entities = set(dataset_info.get("expected_entities", []))
    detected_entities = set(detection_result.get("entities", {}).keys()) if isinstance(detection_result.get("entities"), dict) else set(detection_result.get("entities", []))

    true_positives = len(expected_entities & detected_entities)
    false_positives = len(detected_entities - expected_entities)
    false_negatives = len(expected_entities - detected_entities)

    precision = true_positives / max(true_positives + false_positives, 1)
    recall = true_positives / max(true_positives + false_negatives, 1)
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    scores.append(("entity_detection_f1", round(f1, 4), 1.0))
    details["entity_detection"] = {
        "expected": list(expected_entities),
        "detected": list(detected_entities),
        "true_positives": list(expected_entities & detected_entities),
        "false_positives": list(detected_entities - expected_entities),
        "false_negatives": list(expected_entities - detected_entities),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }

    column_entity_coverage = {}
    for entity_name, columns in detection_result.get("entities", {}).items():
        column_entity_coverage[entity_name] = len(columns) if isinstance(columns, list) else 0

    expected_entity_names = set(expected_entities)
    covered_entities = set(column_entity_coverage.keys()) & expected_entity_names
    coverage_ratio = len(covered_entities) / max(len(expected_entity_names), 1)
    scores.append(("entity_column_coverage", round(coverage_ratio, 4), 1.0))
    details["entity_column_coverage"] = {
        "expected_entities": list(expected_entity_names),
        "covered_entities": list(covered_entities),
        "coverage_ratio": round(coverage_ratio, 4),
    }

    overall = sum(s[1] * s[2] for s in scores) / sum(s[2] for s in scores) if scores else 0.0
    return round(overall, 4), details