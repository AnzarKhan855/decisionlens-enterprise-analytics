from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple
from app.logging.logger import get_logger

logger = get_logger(__name__)


class ForecastingColumnDetector:
    """
    Deterministic dataset-detection pipeline for forecasting.

    Detects:
    1. Time column (date, timestamp, order_date, transaction_date, month, year...)
    2. Quantity column (quantity, qty, units, units_sold, order_quantity...)
    3. Unit Price column (unit_price, price, selling_price, sale_price, rate...)
    4. Revenue column (revenue, sales, total_sales, amount, net_sales...)

    Uses semantic normalized matching + datatype and statistical value validation.
    Returns deterministic results for identical dataset profiles.
    """

    TIME_PATTERNS = [
        r"^date$", r"^timestamp$", r"^order_date$", r"^transaction_date$", r"^txn_date$",
        r"^sale_date$", r"^day$", r"^month$", r"^year$", r"^dt$", r"^time$", r".*_date$", r".*_dt$"
    ]

    QUANTITY_PATTERNS = [
        r"^quantity$", r"^qty$", r"^units$", r"^units_sold$", r"^order_quantity$",
        r"^items$", r"^item_count$", r"^volume$", r"^count$", r"^num_units$", r".*_qty$"
    ]

    UNIT_PRICE_PATTERNS = [
        r"^unit_price$", r"^price$", r"^selling_price$", r"^sale_price$", r"^rate$",
        r"^item_price$", r"^list_price$", r"^cost_per_unit$", r"^avg_price$", r".*_price$"
    ]

    REVENUE_PATTERNS = [
        r"^revenue$", r"^sales$", r"^total_sales$", r"^amount$", r"^net_sales$",
        r"^gross_sales$", r"^total_amount$", r"^turnover$", r"^order_value$", r"^income$", r".*_sales$"
    ]

    @classmethod
    def detect_columns(cls, profile: Dict[str, Any], semantic_model: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        columns = profile.get("columns", {})
        total_rows = profile.get("total_rows", 0)

        time_col, time_cand = cls._detect_time_column(columns, semantic_model)
        qty_col, qty_cand = cls._detect_quantity_column(columns, semantic_model)
        price_col, price_cand = cls._detect_unit_price_column(columns, semantic_model)
        rev_col, rev_cand = cls._detect_revenue_column(columns, semantic_model)

        return {
            "dataset_detected": True,
            "total_rows": total_rows,
            "total_columns": len(columns),
            "detections": {
                "time_column": {
                    "detected": time_col is not None,
                    "selected": time_col,
                    "confidence": 0.95 if time_col else 0.0,
                    "possible_columns": time_cand,
                },
                "quantity_column": {
                    "detected": qty_col is not None,
                    "selected": qty_col,
                    "confidence": 0.90 if qty_col else 0.0,
                    "possible_columns": qty_cand,
                },
                "unit_price_column": {
                    "detected": price_col is not None,
                    "selected": price_col,
                    "confidence": 0.90 if price_col else 0.0,
                    "possible_columns": price_cand,
                },
                "revenue_column": {
                    "detected": rev_col is not None,
                    "selected": rev_col,
                    "confidence": 0.95 if rev_col else 0.0,
                    "possible_columns": rev_cand,
                },
            },
            "all_numeric_columns": [
                name for name, c in columns.items()
                if c.get("stats") and c.get("stats", {}).get("stddev") is not None
            ],
            "all_columns": list(columns.keys()),
        }

    @classmethod
    def _detect_time_column(cls, columns: Dict[str, Any], semantic_model: Optional[Dict[str, Any]]) -> Tuple[Optional[str], List[str]]:
        candidates = []
        best_col = None
        best_score = -1.0

        for col_name, c_prof in columns.items():
            col_clean = col_name.lower().strip()
            data_type = str(c_prof.get("data_type", "")).upper()
            is_temporal = any(k in data_type for k in ["DATE", "TIME", "TIMESTAMP"])

            score = 0.0
            if is_temporal:
                score += 50.0

            for pat in cls.TIME_PATTERNS:
                if re.match(pat, col_clean):
                    score += 40.0
                    candidates.append(col_name)
                    break

            if score > best_score and score > 20.0:
                best_score = score
                best_col = col_name

        candidates = list(dict.fromkeys(candidates))
        return best_col, candidates

    @classmethod
    def _detect_quantity_column(cls, columns: Dict[str, Any], semantic_model: Optional[Dict[str, Any]]) -> Tuple[Optional[str], List[str]]:
        candidates = []
        best_col = None
        best_score = -1.0

        for col_name, c_prof in columns.items():
            col_clean = col_name.lower().strip()
            stats = c_prof.get("stats") or {}
            if not stats or stats.get("stddev") is None:
                continue

            score = 0.0
            for pat in cls.QUANTITY_PATTERNS:
                if re.match(pat, col_clean):
                    score += 50.0
                    candidates.append(col_name)
                    break

            min_val = stats.get("min")
            if min_val is not None and min_val >= 0:
                score += 10.0

            if score > best_score and score > 20.0:
                best_score = score
                best_col = col_name

        candidates = list(dict.fromkeys(candidates))
        return best_col, candidates

    @classmethod
    def _detect_unit_price_column(cls, columns: Dict[str, Any], semantic_model: Optional[Dict[str, Any]]) -> Tuple[Optional[str], List[str]]:
        candidates = []
        best_col = None
        best_score = -1.0

        for col_name, c_prof in columns.items():
            col_clean = col_name.lower().strip()
            stats = c_prof.get("stats") or {}
            if not stats or stats.get("stddev") is None:
                continue

            score = 0.0
            for pat in cls.UNIT_PRICE_PATTERNS:
                if re.match(pat, col_clean):
                    score += 50.0
                    candidates.append(col_name)
                    break

            min_val = stats.get("min")
            if min_val is not None and min_val >= 0:
                score += 10.0

            if score > best_score and score > 20.0:
                best_score = score
                best_col = col_name

        candidates = list(dict.fromkeys(candidates))
        return best_col, candidates

    @classmethod
    def _detect_revenue_column(cls, columns: Dict[str, Any], semantic_model: Optional[Dict[str, Any]]) -> Tuple[Optional[str], List[str]]:
        candidates = []
        best_col = None
        best_score = -1.0

        for col_name, c_prof in columns.items():
            col_clean = col_name.lower().strip()
            stats = c_prof.get("stats") or {}
            if not stats or stats.get("stddev") is None:
                continue

            score = 0.0
            for pat in cls.REVENUE_PATTERNS:
                if re.match(pat, col_clean):
                    score += 50.0
                    candidates.append(col_name)
                    break

            min_val = stats.get("min")
            if min_val is not None and min_val >= 0:
                score += 10.0

            if score > best_score and score > 20.0:
                best_score = score
                best_col = col_name

        candidates = list(dict.fromkeys(candidates))
        return best_col, candidates
