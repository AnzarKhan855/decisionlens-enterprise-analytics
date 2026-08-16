from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from types import SimpleNamespace

from app.ml.prediction_engine import UniversalPredictionEngine
from app.retail.canonical_model import CanonicalRetailModel, build_canonical_model
from app.semantic_model.core import SemanticModel, TimeColumn
from app.ingestion.semantic_profiler import SemanticDataProfiler
from app.analytics.semantic_analytics import SemanticAnalyticsEngine
from app.logging.logger import get_logger

logger = get_logger(__name__)


class RetailForecastEngine:
    """
    Retail & E-Commerce Forecast Engine.

    Wraps UniversalPredictionEngine with retail-specific date/measure detection
    and multi-horizon time-series forecasting.

    Never fails silently if a valid date column exists. Auto-detects:
      - Date columns: InvoiceDate, OrderDate, PurchaseDate, Timestamp, date, datetime, etc.
      - Measure columns: revenue, sales, quantity, or any numeric column

    Generates forecasts for multiple horizons using the best available algorithm:
      - ARIMA (AR(1) via scipy)
      - Exponential Smoothing (numpy)
      - Moving Average (numpy)
      - Linear Regression (fallback)
    """

    # Date column name aliases for auto-detection
    DATE_COLUMN_ALIASES = [
        "invoicedate", "orderdate", "purchasedate", "timestamp",
        "date", "order_date", "invoice_date", "purchase_date",
        "created_at", "updated_at", "transaction_date", "ship_date",
        "delivery_date", "payment_date", "time", "datetime",
    ]

    # Measure column name aliases for auto-detection
    MEASURE_COLUMN_ALIASES = [
        "revenue", "sales", "amount", "total", "price", "unit_price",
        "quantity", "qty", "units", "volume", "profit", "cost",
        "cogs", "freight", "shipping", "discount", "margin",
    ]

    @classmethod
    def generate_forecasts(
        cls,
        parquet_path: Path,
        canonical_model: Optional[CanonicalRetailModel] = None,
        horizons: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        Generate multi-horizon forecasts for a retail dataset.

        Args:
            parquet_path: Path to the parquet dataset
            canonical_model: Optional canonical retail model (built if not provided)
            horizons: List of forecast horizons in days (default: [7, 30, 90, 180, 365])

        Returns:
            Dict with date_column, measure_column, total_rows, and forecasts list
        """
        if horizons is None:
            horizons = [7, 30, 90, 180, 365]

        if not parquet_path or not parquet_path.exists():
            return cls._error_result("Parquet file not found.", parquet_path)

        # Profile the dataset
        try:
            profile = SemanticDataProfiler.profile(parquet_path)
        except Exception as exc:
            logger.error("[RetailForecastEngine] Profiling failed: %s", exc)
            return cls._error_result(f"Dataset profiling failed: {str(exc)}", parquet_path)

        total_rows = profile.get("total_rows", 0)
        columns = list(profile.get("columns", {}).keys())

        # Build or use provided canonical model
        if canonical_model is None:
            try:
                retail_mapping = profile.get("retail_mapping")
                if not retail_mapping:
                    from app.retail.retail_semantic_mapper import RetailSemanticMapper
                    retail_mapping = RetailSemanticMapper.map({
                        "columns": profile.get("columns", {}),
                        "total_rows": total_rows,
                        "column_categories": profile.get("column_categories", {}),
                    })
                canonical_model = build_canonical_model(profile, retail_mapping or {})
            except Exception as exc:
                logger.warning("[RetailForecastEngine] Canonical model build failed: %s", exc)
                canonical_model = None

        # Auto-detect date column
        date_col = cls._detect_date_column(parquet_path, canonical_model, profile, columns)
        if not date_col:
            return cls._error_result(
                "No valid date column detected. Expected columns like InvoiceDate, OrderDate, PurchaseDate, or Timestamp.",
                parquet_path,
                date_col=None,
                measure_col=None,
            )

        # Auto-detect measure column
        measure_col = cls._detect_measure_column(parquet_path, canonical_model, profile, columns)
        if not measure_col:
            return cls._error_result(
                "No numeric measure column detected. Expected columns like revenue, sales, quantity, or price.",
                parquet_path,
                date_col=date_col,
                measure_col=None,
            )

        # Build time-series trends
        try:
            rows = SemanticAnalyticsEngine.get_time_series_trend(parquet_path, date_col, measure_col)
        except Exception as exc:
            logger.error("[RetailForecastEngine] Time-series query failed: %s", exc)
            return cls._error_result(
                f"Time-series aggregation failed for '{measure_col}' by '{date_col}': {str(exc)}",
                parquet_path,
                date_col=date_col,
                measure_col=measure_col,
            )

        if not rows or len(rows) < 3:
            return cls._error_result(
                f"Insufficient time-series data points ({len(rows) if rows else 0} found). "
                f"At least 3 distinct periods are required for forecasting.",
                parquet_path,
                date_col=date_col,
                measure_col=measure_col,
            )

        # Build trends dict in the format expected by UniversalPredictionEngine
        from app.schemas.analytics import TrendPoint
        trend_points = []
        for r in rows:
            try:
                val = float(r.get("value", 0) or 0)
            except (TypeError, ValueError):
                val = 0.0
            trend_points.append(TrendPoint(period=str(r.get("period", "")), value=val))

        trends = {measure_col: trend_points}

        # Build partial analytics result namespace
        analytics_result = SimpleNamespace(
            trends=trends,
            correlations=[],
            root_causes=[],
            drivers=[],
            anomalies=[],
            outliers=[],
            kpis=[],
            volume=total_rows,
            confidence_score=0.0,
            evidence={
                "measures_analyzed": [measure_col],
                "dimensions_analyzed": [],
                "temporal_columns": [date_col],
                "total_rows": total_rows,
            },
        )

        # Build minimal semantic model
        sm = SemanticModel(
            workspace_id="retail-forecast",
            domain="Retail & E-Commerce",
            dataset_type="Retail",
        )
        sm.time_columns = [TimeColumn(column=date_col, data_type="date")]

        # Call UniversalPredictionEngine with multi-horizon support
        try:
            predictions = UniversalPredictionEngine.generate(
                analytics_result=analytics_result,
                semantic_model=sm,
                horizons=horizons,
                temporal=[date_col],
            )
        except Exception as exc:
            logger.error("[RetailForecastEngine] Prediction engine failed: %s", exc)
            return cls._error_result(
                f"Forecast generation failed: {str(exc)}",
                parquet_path,
                date_col=date_col,
                measure_col=measure_col,
            )

        # Filter and structure forecasts
        forecasts = []
        for pred in predictions:
            if not getattr(pred, "feasible", True):
                continue
            forecasts.append({
                "model_type": pred.model_type,
                "model_used": pred.model_used,
                "prediction": pred.prediction,
                "confidence": round(pred.confidence, 4),
                "evidence": pred.evidence,
                "assumptions": pred.assumptions,
                "business_impact": pred.business_impact,
                "time_horizon": pred.time_horizon,
                "risk_level": pred.risk_level,
                "recommended_action": pred.recommended_action,
                "risks": pred.risks,
                "opportunities": pred.opportunities,
                "prediction_interval": list(pred.prediction_interval) if pred.prediction_interval else None,
                "feasible": pred.feasible,
                "limitation": pred.limitation,
            })

        return {
            "date_column": date_col,
            "measure_column": measure_col,
            "total_rows": total_rows,
            "data_points": len(trend_points),
            "horizons_requested": horizons,
            "forecasts": forecasts,
            "forecast_available": bool(forecasts),
        }

    @classmethod
    def _detect_date_column(
        cls,
        parquet_path: Path,
        canonical_model: Optional[CanonicalRetailModel],
        profile: Dict[str, Any],
        columns: List[str],
    ) -> Optional[str]:
        """Auto-detect the date column from canonical model or parquet schema."""
        # 1. Check canonical model
        if canonical_model and canonical_model.has_date():
            date_col = canonical_model.date_column
            if date_col and date_col in columns:
                return date_col

        # 2. Check profiler temporal columns
        temporal = profile.get("column_categories", {}).get("temporal", [])
        if temporal:
            return temporal[0]

        # 3. Scan column names for date aliases
        col_lower_map = {c.lower(): c for c in columns}
        for alias in cls.DATE_COLUMN_ALIASES:
            for col_lower, original in col_lower_map.items():
                if alias in col_lower:
                    return original

        # 4. Check DuckDB schema for DATE/TIMESTAMP types
        try:
            from app.database.duckdb_engine import DuckDBEngine
            schema = DuckDBEngine.get_schema(parquet_path)
            for col, dtype in schema.items():
                if any(t in dtype.upper() for t in ["DATE", "TIME", "TIMESTAMP"]):
                    return col
        except Exception:
            pass

        return None

    @classmethod
    def _detect_measure_column(
        cls,
        parquet_path: Path,
        canonical_model: Optional[CanonicalRetailModel],
        profile: Dict[str, Any],
        columns: List[str],
    ) -> Optional[str]:
        """Auto-detect the primary measure column."""
        # 1. Check canonical model revenue column
        if canonical_model:
            rev = canonical_model.revenue_column
            if rev and rev in columns:
                return rev
            qty = canonical_model.quantity_column
            if qty and qty in columns:
                return qty
            price = canonical_model.price_column
            if price and price in columns:
                return price

        # 2. Check profiler measures
        measures = profile.get("column_categories", {}).get("measures", [])
        if measures:
            # Prefer revenue/sales aliases
            col_lower_map = {c.lower(): c for c in measures}
            for alias in cls.MEASURE_COLUMN_ALIASES:
                for col_lower, original in col_lower_map.items():
                    if alias in col_lower:
                        return original
            return measures[0]

        # 3. Scan all columns for numeric types
        try:
            from app.database.duckdb_engine import DuckDBEngine
            schema = DuckDBEngine.get_schema(parquet_path)
            numeric_types = ["BIGINT", "INTEGER", "SMALLINT", "TINYINT", "DOUBLE", "FLOAT", "DECIMAL", "HUGEINT", "REAL"]
            for col, dtype in schema.items():
                if any(nt in dtype.upper() for nt in numeric_types):
                    # Skip IDs
                    if not any(id_kw in col.lower() for id_kw in ["id", "uuid", "guid", "key", "code", "no", "sku", "index"]):
                        return col
        except Exception:
            pass

        return None

    @classmethod
    def _error_result(
        cls,
        error_message: str,
        parquet_path: Path,
        date_col: Optional[str] = None,
        measure_col: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build a standardized error result."""
        return {
            "date_column": date_col,
            "measure_column": measure_col,
            "total_rows": 0,
            "data_points": 0,
            "horizons_requested": [],
            "forecasts": [],
            "forecast_available": False,
            "error": error_message,
        }
