from typing import Any, Dict, List

from app.semantic_model.core import TimeColumn


RETAIL_DATE_ALIASES = [
    "invoicedate", "invoice_date", "orderdate", "order_date",
    "purchasedate", "purchase_date", "date", "timestamp",
    "transaction_date", "sales_date", "created_at", "updated_at",
    "event_time", "event_date", "order_timestamp",
    "delivery_date", "shipped_date", "estimated_delivery", "actual_delivery",
    "month", "year", "quarter", "week", "day", "hour",
]


def detect_time_columns(columns: List[Dict[str, Any]]) -> List[TimeColumn]:
    time_cols = []
    for c in columns:
        cname = c["name"].lower()
        ctype = c.get("type", "").lower()

        is_time = (
            any(k in ctype for k in ["date", "time", "timestamp"]) or
            any(k in cname for k in RETAIL_DATE_ALIASES) or
            any(k in cname for k in [
                "date", "timestamp", "datetime", "created_at", "updated_at",
                "order_date", "invoice_date", "purchase_date"
            ])
        )
        if not is_time:
            continue

        granularity = "datetime"
        if any(k in cname for k in ["year", "annual"]):
            granularity = "year"
        elif any(k in cname for k in ["quarter", "q1", "q2", "q3", "q4"]):
            granularity = "quarter"
        elif any(k in cname for k in ["month", "monthly"]):
            granularity = "month"
        elif any(k in cname for k in ["day", "daily", "date"]):
            granularity = "day"
        elif any(k in cname for k in ["hour", "hourly"]):
            granularity = "hour"

        is_primary = any(k in cname for k in [
            "date", "timestamp", "created_at", "order_date", "invoice_date",
            "purchase_date", "transaction_date", "order_timestamp"
        ])

        time_cols.append(TimeColumn(
            column=c["name"],
            data_type=c.get("type"),
            granularity=granularity,
            is_primary_time=is_primary,
        ))

    return time_cols