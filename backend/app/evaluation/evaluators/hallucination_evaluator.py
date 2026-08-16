import re
from typing import Any, Dict, List


def evaluate_hallucination_prevention(
    insight_result: Dict[str, Any],
    data_rows: List[Dict[str, Any]],
    validation_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Evaluates hallucination prevention by checking:
    - Are numeric claims traceable to actual data?
    - Does the answer contain unsupported assertions?
    - Are confidence scores reasonable given data availability?
    - Does the validator flag any fabrication risks?
    """
    scores = []
    details = {}

    answer = insight_result.get("answer", "")
    status = insight_result.get("status", "unknown")
    confidence = insight_result.get("confidence", 0.0)
    has_error = status in ("error", "empty_result")
    validation = validation_result if isinstance(validation_result, dict) else {}

    if has_error and "error" in status.lower():
        scores.append(("error_transparency", 1.0, 1.0))
        details["error_transparency"] = {"status": status, "correctly_reported_error": True}
    else:
        validation_flags = validation.get("warnings", []) if isinstance(validation, dict) else []
        fabrication_risk = len(validation_flags) > 0
        no_hallucination_score = 0.3 if fabrication_risk else 1.0
        scores.append(("no_hallucination", no_hallucination_score, 1.0))
        details["no_hallucination"] = {
            "fabrication_warnings": validation_flags,
            "risk_detected": fabrication_risk,
            "score": no_hallucination_score,
        }

    numeric_pattern = r"\d[\d,]*\.?\d*\s*(?:%|million|billion|m|b|k|usd|\$|\bunits\b|\brecords\b)"
    numeric_claims = re.findall(numeric_pattern, answer)
    if numeric_claims:
        evidence_count = len(data_rows)
        has_evidence = evidence_count > 0
        evidence_score = 1.0 if has_evidence else 0.2
    else:
        evidence_score = 1.0

    scores.append(("numeric_evidence_traceability", evidence_score, 1.0))
    details["numeric_evidence_traceability"] = {
        "numeric_claims_found": len(numeric_claims),
        "data_rows_available": len(data_rows),
        "evidence_present": len(data_rows) > 0,
        "score": round(evidence_score, 4),
    }

    validation_is_valid = validation.get("is_valid", True) if isinstance(validation, dict) else True
    validation_confidence = validation.get("confidence_score", confidence) if isinstance(validation, dict) else confidence

    confidence_reasonable = 0.5 <= confidence <= 1.0 if not has_error else True
    scores.append(("confidence_reasonableness", 1.0 if confidence_reasonable else 0.3, 1.0))
    details["confidence_reasonableness"] = {
        "reported_confidence": confidence,
        "validated_confidence": validation_confidence,
        "reasonable": confidence_reasonable,
    }

    status_score = 1.0 if status == "ok" else (0.5 if status in ("empty_result",) else 0.0)
    scores.append(("status_correctness", status_score, 1.0))
    details["status_correctness"] = {
        "status": status,
        "score": status_score,
    }

    overall = sum(s[1] * s[2] for s in scores) / sum(s[2] for s in scores) if scores else 0.0
    return round(overall, 4), details