from typing import Any, Dict, List


def evaluate_visualization_quality(
    analysis_result: Dict[str, Any],
    question_understanding: Dict[str, Any],
    charts_generated: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Evaluates visualization quality by checking:
    - Are charts generated for supported intents?
    - Do chart types match the analysis intent?
    - Do charts reference the correct columns?
    - Is the configuration valid (no missing required fields)?
    """
    scores = []
    details = {}

    intent = question_understanding.get("intent", "summary")

    intent_chart_map = {
        "trend": "line",
        "top_n": "bar",
        "breakdown": "bar",
        "comparison": "bar",
        "percentage": "pie",
        "correlation": "scatter",
        "distribution": "histogram",
    }

    expected_chart_type = intent_chart_map.get(intent, "table")

    intent_score = 1.0 if any(c.get("type") == expected_chart_type for c in charts_generated) else 0.3
    scores.append(("chart_type_match", intent_score, 1.0))
    details["chart_type_match"] = {
        "expected_type": expected_chart_type,
        "actual_types": [c.get("type") for c in charts_generated],
        "match": intent_score >= 1.0,
    }

    charts_have_data = all(
        "data" in c and len(c.get("data", [])) > 0
        for c in charts_generated
    ) if charts_generated else False
    data_score = 1.0 if charts_have_data or not charts_generated else 0.4
    scores.append(("chart_data_completeness", data_score, 1.0))
    details["chart_data_completeness"] = {
        "charts_generated": len(charts_generated),
        "all_have_data": charts_have_data,
        "score": round(data_score, 4),
    }

    charts_have_labels = all(
        "title" in c and "x_label" in c and "y_label" in c
        for c in charts_generated
    ) if charts_generated else False
    label_score = 1.0 if charts_have_labels or not charts_generated else 0.5
    scores.append(("chart_labeling", label_score, 1.0))
    details["chart_labeling"] = {
        "all_have_labels": charts_have_labels,
        "score": round(label_score, 4),
    }

    columns_used = analysis_result.get("columns_used", [])
    charts_reference_columns = True
    for chart in charts_generated:
        chart_cols = [chart.get("x_column"), chart.get("y_column")]
        for cc in chart_cols:
            if cc and cc not in columns_used:
                charts_reference_columns = False
                break
    column_score = 1.0 if charts_reference_columns or not charts_generated else 0.3
    scores.append(("column_reference_accuracy", column_score, 1.0))
    details["column_reference_accuracy"] = {
        "columns_used": columns_used,
        "all_charts_use_valid_columns": charts_reference_columns,
        "score": round(column_score, 4),
    }

    overall = sum(s[1] * s[2] for s in scores) / sum(s[2] for s in scores) if scores else 0.0
    return round(overall, 4), details