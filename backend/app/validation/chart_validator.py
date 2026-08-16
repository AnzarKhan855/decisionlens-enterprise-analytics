import math
from typing import Any, Dict, List, Optional

from app.logging.logger import get_logger

logger = get_logger(__name__)


class ChartValidationError(Exception):
    pass


def validate_chart_data(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not data:
        return []

    cleaned = []
    for item in data:
        clean_item = {}
        for key, value in item.items():
            if value is None:
                continue
            if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                continue
            if isinstance(value, str) and value.strip().lower() in ("undefined", "null", "nan", ""):
                continue
            clean_item[key] = value

        label = clean_item.get("label") or clean_item.get("x_field") or clean_item.get("category") or clean_item.get("period")
        raw_value = clean_item.get("value") or clean_item.get("y_field")

        if label and raw_value is not None:
            try:
                val = float(raw_value)
                if math.isnan(val) or math.isinf(val):
                    continue
                clean_item["label"] = str(label)
                clean_item["value"] = val
                clean_item["x_field"] = str(label)
                clean_item["y_field"] = val
                cleaned.append(clean_item)
            except (TypeError, ValueError):
                continue
    return cleaned


def auto_select_chart_type(
    data: List[Dict[str, Any]],
    temporal_cols: List[str],
    measure_cols: List[str],
    dimension_cols: List[str],
) -> str:
    if not data:
        return "bar"

    if temporal_cols and measure_cols:
        return "line"
    if dimension_cols and measure_cols and len(dimension_cols) == 1:
        return "bar"
    if len(measure_cols) >= 2:
        return "scatter"
    if len(dimension_cols) == 1 and len(measure_cols) == 1:
        return "bar"
    return "bar"


def normalize_chart(chart: Dict[str, Any]) -> Dict[str, Any]:
    chart_type = chart.get("chart_type") or chart.get("type") or "bar"
    title = chart.get("title") or chart.get("chart_title") or ""
    source_column = chart.get("source_column") or chart.get("y_axis") or ""
    dimension_column = chart.get("dimension_column") or chart.get("x_axis") or ""
    data = chart.get("data") or chart.get("series") or []
    data = validate_chart_data(data)

    if not data:
        return {}

    labels = []
    for d in data:
        lbl = d.get("label") or d.get("x_field") or d.get("category") or d.get("period") or ""
        if lbl:
            labels.append(str(lbl))

    if not labels:
        return {}

    x_axis = chart.get("x_axis") or dimension_column or source_column
    y_axis = chart.get("y_axis") or source_column
    confidence = chart.get("confidence", 0.0)
    if isinstance(confidence, (int, float)) and (math.isnan(confidence) or math.isinf(confidence)):
        confidence = 0.0

    values = [d.get("y_field", d.get("value", 0)) for d in data]

    return {
        "chart_type": chart_type,
        "type": chart_type,
        "title": title,
        "x_axis": x_axis,
        "y_axis": y_axis,
        "x_field": data[0].get("x_field", x_axis) if data else x_axis,
        "y_field": data[0].get("y_field", y_axis) if data else y_axis,
        "series": data,
        "data": data,
        "labels": labels,
        "values": values,
        "confidence": confidence,
        "source_column": source_column,
        "dimension_column": dimension_column,
        "business_interpretation": chart.get("business_interpretation", ""),
        "evidence": chart.get("evidence", ""),
        "available": True,
        "id": chart.get("id", ""),
    }


def validate_charts(raw_charts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not raw_charts:
        return []

    normalized = []
    for c in raw_charts:
        try:
            norm = normalize_chart(c)
            if norm:
                normalized.append(norm)
        except Exception as exc:
            logger.warning("[ChartValidation] Failed to normalize chart: %s", exc)

    return normalized
