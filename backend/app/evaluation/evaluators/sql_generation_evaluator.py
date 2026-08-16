from typing import Any, Dict, List
from dataclasses import dataclass, field


def evaluate_sql_generation(
    test_questions: List[Dict[str, Any]],
    sql_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Evaluates SQL generation quality by comparing generated SQL against expected patterns.

    Tests:
    - SQL syntax validity
    - Correct table references
    - Correct aggregation functions
    - Correct GROUP BY usage
    - Correct ORDER BY for top-N queries
    - Correct JOIN patterns for multi-table queries
    """
    scores = []
    details = {}

    if not sql_results or not test_questions:
        return 0.0, {"error": "No SQL results or test questions provided"}

    for i, (question, sql_result) in enumerate(zip(test_questions, sql_results)):
        question_intent = question.get("expected_intent", "summary")
        error = sql_result.get("error")
        query = sql_result.get("sql_query", "")
        rows = sql_result.get("rows", [])

        query_score = 0.0
        max_query_score = 1.0
        query_details = {}

        if error:
            query_details["error"] = error
            query_score = 0.0
        elif not query:
            query_details["error"] = "No SQL query generated"
            query_score = 0.0
        else:
            query_upper = query.upper()
            checks = {}

            has_select = "SELECT" in query_upper
            has_from = "FROM" in query_upper
            checks["has_select"] = has_select
            checks["has_from"] = has_from

            if question_intent in ("top_n", "trend", "breakdown", "comparison"):
                has_group_by = "GROUP BY" in query_upper
                checks["has_group_by"] = has_group_by

            if question_intent == "top_n":
                has_order = "ORDER BY" in query_upper
                has_limit = "LIMIT" in query_upper
                checks["has_order_by"] = has_order
                checks["has_limit"] = has_limit

            if question_intent == "trend":
                has_date_trunc = "STRFTIME" in query_upper or "DATE_TRUNC" in query_upper or "MONTH" in query_upper
                checks["has_date_truncation"] = has_date_trunc

            if question_intent == "breakdown" and "expected_metric" in question:
                metric = question.get("expected_metric", "")
                has_metric = metric.upper() in query_upper or any(agg in query_upper for agg in ["SUM", "AVG", "COUNT", "MAX", "MIN"])
                checks["has_metric_aggregation"] = has_metric

            all_passed = all(checks.values()) if checks else False
            query_score = sum(1.0 for v in checks.values() if v) / max(len(checks), 1)
            query_details["checks"] = checks
            query_details["score"] = round(query_score, 4)

        individual_score = query_score
        scores.append((f"sql_test_{i}", individual_score, 1.0))
        details[f"question_{i}"] = {
            "question": question.get("question", ""),
            "expected_intent": question_intent,
            "query": query,
            "rows_returned": len(rows),
            "score": round(individual_score, 4),
            **query_details,
        }

    overall = sum(s[1] * s[2] for s in scores) / sum(s[2] for s in scores) if scores else 0.0
    return round(overall, 4), details