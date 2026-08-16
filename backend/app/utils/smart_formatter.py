import re
from typing import Any

CURRENCY_KEYWORDS = {
    "revenue", "sales", "profit", "cost", "price", "discount", "amount",
    "expense", "income", "salary", "balance", "fee", "tax", "budget", "spend"
}

NON_CURRENCY_KEYWORDS = {
    "id", "uuid", "guid", "code", "index", "key", "pk", "fk",
    "age", "qty", "quantity", "count", "number", "rating", "score", "rows",
    "columns", "items", "units", "year", "month", "day", "hour", "rank"
}

PERCENTAGE_KEYWORDS = {
    "rate", "percentage", "margin", "growth", "retention", "share",
    "ratio", "roi", "churn", "accuracy", "confidence", "yield"
}


def format_business_value(metric_name: str, value: Any, currency_symbol: str = "$") -> str:
    """
    Smart Enterprise Value Formatter.
    Formats numeric metrics accurately according to domain semantics.
    Ensures non-currency metrics (IDs, Ages, Quantities, Ratings) NEVER show currency symbols.
    """
    if value is None:
        return "N/A"

    if isinstance(value, str):
        return value

    try:
        val_float = float(value)
    except (ValueError, TypeError):
        return str(value)

    name_clean = metric_name.lower().replace("_", " ")

    # 1. Non-currency check (IDs, Quantities, Ages, Ratings, Counts)
    if any(kw in name_clean.split() or name_clean.endswith(kw) for kw in NON_CURRENCY_KEYWORDS):
        if val_float.is_integer():
            return f"{int(val_float):,}"
        return f"{val_float:,.2f}"

    # 2. Percentage check
    if any(kw in name_clean for kw in PERCENTAGE_KEYWORDS) or (0 < abs(val_float) <= 1 and "rate" in name_clean):
        percentage_val = val_float * 100 if abs(val_float) <= 1 else val_float
        return f"{percentage_val:.1f}%"

    # 3. Currency check
    if any(kw in name_clean for kw in CURRENCY_KEYWORDS):
        if abs(val_float) >= 1_000_000_000:
            return f"{currency_symbol}{val_float / 1_000_000_000:.2f}B"
        if abs(val_float) >= 1_000_000:
            return f"{currency_symbol}{val_float / 1_000_000:.2f}M"
        if abs(val_float) >= 1_000:
            return f"{currency_symbol}{val_float:,.2f}"
        return f"{currency_symbol}{val_float:.2f}"

    # 4. Standard default numeric formatting
    if val_float.is_integer():
        return f"{int(val_float):,}"
    return f"{val_float:,.2f}"
