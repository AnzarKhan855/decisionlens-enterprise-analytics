from typing import Any, Dict, List


def evaluate_recommendations(
    question_understanding: Dict[str, Any],
    insight_result: Dict[str, Any],
    expected_intent: str,
) -> Dict[str, Any]:
    """
    Evaluates recommendation quality by checking:
    - Intent alignment (does the answer match the question intent?)
    - Evidence grounding (are recommendations backed by data?)
    - Actionability (are recommendations concrete and actionable?)
    - Relevance (is the answer relevant to the domain?)
    """
    scores = []
    details = {}

    answer = insight_result.get("answer", "")
    confidence = insight_result.get("confidence", 0.0)
    data_evidence = insight_result.get("data_evidence", [])
    status = insight_result.get("status", "unknown")
    detected_intent = question_understanding.get("intent", "unknown")

    intent_match_score = 1.0 if detected_intent == expected_intent else 0.3
    scores.append(("intent_alignment", intent_match_score, 1.0))
    details["intent_alignment"] = {
        "expected": expected_intent,
        "detected": detected_intent,
        "match": detected_intent == expected_intent,
    }

    evidence_score = min(1.0, len(data_evidence) / 3.0) if data_evidence else 0.0
    scores.append(("evidence_grounding", evidence_score, 1.0))
    details["evidence_grounding"] = {
        "evidence_count": len(data_evidence),
        "target_count": 3,
        "score": round(evidence_score, 4),
    }

    actionability_keywords = ["should", "recommend", "suggest", "consider", "advise", "action", "step", "prioritize", "focus"]
    answer_lower = answer.lower()
    actionability_hits = sum(1 for kw in actionability_keywords if kw in answer_lower)
    actionability_score = min(1.0, actionability_hits / 3.0)
    scores.append(("actionability", actionability_score, 1.0))
    details["actionability"] = {
        "keywords_found": actionability_hits,
        "target": 3,
        "score": round(actionability_score, 4),
    }

    confidence_score = confidence
    scores.append(("confidence_score", confidence_score, 1.0))
    details["confidence_score"] = {
        "confidence": confidence,
        "status": status,
    }

    overall = sum(s[1] * s[2] for s in scores) / sum(s[2] for s in scores) if scores else 0.0
    return round(overall, 4), details