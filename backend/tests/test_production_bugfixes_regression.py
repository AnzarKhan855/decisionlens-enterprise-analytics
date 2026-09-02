from __future__ import annotations

import os
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
import pandas as pd
import pytest

from app.analytics.semantic_analytics import SemanticAnalyticsEngine
from app.analytics.universal_engine import UniversalAnalyticsEngine
from app.analytics.variance_engine import VarianceDecompositionEngine
from app.database.mongodb import sanitize_mongo_document
from app.ml.prediction_engine import UniversalPredictionEngine
from app.schemas.analytics import AnalyticsResult
from app.semantic_model.core import SemanticModel


import uuid
from app.database.storage import STORAGE_DIR
from app.services.analytics_cache_service import AnalyticsCacheService


@pytest.fixture
def temp_region_dataset():
    """Dataset containing both 'region' and 'category' columns to test GROUP BY disambiguation."""
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    unique_name = f"test_temp_region_{uuid.uuid4().hex[:8]}.parquet"
    tmp_path = STORAGE_DIR / unique_name

    df = pd.DataFrame({
        "date": ["2024-01-01", "2024-01-02"],
        "region": ["North", "South"],
        "category": ["Electronics", "Clothing"],
        "quantity": [10, 20],
        "unit_price": [100.0, 50.0],
        "revenue": [1000.0, 1000.0]
    })
    df.to_parquet(tmp_path)
    yield tmp_path

    if tmp_path.exists():
        try:
            os.remove(tmp_path)
        except Exception:
            pass


def test_duckdb_region_group_by_disambiguation(temp_region_dataset):
    """Test A: Ensure querying breakdown on 'region' in a table with a 'category' column does not trigger Binder Error."""
    breakdown = SemanticAnalyticsEngine.get_dimension_breakdown(
        temp_region_dataset, dimension_col="region", measure_col="quantity"
    )
    assert isinstance(breakdown, list)
    assert len(breakdown) == 2
    categories = {r["category"] for r in breakdown}
    assert "North" in categories
    assert "South" in categories

    drivers = VarianceDecompositionEngine.analyze_drivers(
        temp_region_dataset, dimension_col="region", measure_col="quantity"
    )
    assert drivers["dimension"] == "region"
    assert len(drivers["drivers"]) == 2


def test_distributions_and_rankings_graceful_missing_category(temp_region_dataset):
    """Test B: Verify distributions and rankings computation gracefully handles schema and missing keys."""
    profile = {
        "total_rows": 2,
        "column_categories": {
            "dimensions": ["region", "category"],
            "measures": ["quantity", "unit_price"],
            "temporal": ["date"]
        }
    }
    dists = UniversalAnalyticsEngine._compute_distributions(
        temp_region_dataset, profile, ["region"], ["quantity"]
    )
    assert "region" in dists
    assert len(dists["region"]) == 2

    ranks = UniversalAnalyticsEngine._compute_rankings(
        temp_region_dataset, profile, ["region"], ["quantity"]
    )
    assert "region" in ranks
    assert len(ranks["region"]) == 2


def test_mongodb_date_serialization():
    """Test E: Verify Python datetime.date objects are converted to BSON-encodable values."""
    raw_doc = {
        "workspace_id": "test_ws_mongo",
        "created_date": date(2024, 1, 1),
        "nested": {
            "order_date": date(2024, 6, 15),
            "timestamp": datetime(2024, 6, 15, 12, 0, tzinfo=timezone.utc),
        },
        "date_list": [date(2024, 2, 1), date(2024, 3, 1)],
        "string_val": "hello",
        "int_val": 42
    }

    sanitized = sanitize_mongo_document(raw_doc)
    assert isinstance(sanitized["created_date"], datetime)
    assert sanitized["created_date"].year == 2024
    assert sanitized["created_date"].month == 1
    assert sanitized["created_date"].day == 1

    assert isinstance(sanitized["nested"]["order_date"], datetime)
    assert isinstance(sanitized["nested"]["timestamp"], datetime)
    assert isinstance(sanitized["date_list"][0], datetime)
    assert isinstance(sanitized["date_list"][1], datetime)
    assert sanitized["string_val"] == "hello"
    assert sanitized["int_val"] == 42


def test_forecasting_detection_and_insufficient_observations():
    """Test D: Verify deterministic forecasting column detection and insufficient observation handling."""
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    unique_id = f"fc_test_{uuid.uuid4().hex[:8]}"
    fc_path = STORAGE_DIR / f"{unique_id}.parquet"

    df = pd.DataFrame({
        "date": ["2024-01-01", "2024-01-02"],
        "quantity": [10, 20],
        "unit_price": [100.0, 50.0]
    })
    df.to_parquet(fc_path)

    try:
        AnalyticsCacheService.invalidate(unique_id)
        sm = SemanticModel(workspace_id=unique_id, domain="Retail", dataset_type="Sales")
        analytics = UniversalAnalyticsEngine.analyze(sm, parquet_path=fc_path, workspace_id=unique_id)

        assert analytics is not None
        forecast_sum = analytics.forecast_summary
        assert forecast_sum.get("column_detection_succeeded") is True
        assert forecast_sum.get("detected_time_column") == "date"
        assert "quantity" in forecast_sum.get("detected_measures", [])

        # With only 2 rows, forecasting_possible should be False and forecasting_status skipped_insufficient_observations
        assert forecast_sum.get("forecasting_possible") is False
        assert forecast_sum.get("forecasting_status") == "skipped_insufficient_observations"
    finally:
        if fc_path.exists():
            try:
                os.remove(fc_path)
            except Exception:
                pass
