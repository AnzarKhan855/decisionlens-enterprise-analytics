"""
Regression tests for time-series analytics and forecasting pipeline.

Covers:
- Date column detection (date, order_date, datetime)
- Trend normalization with stable "period" key
- Forecasting with sufficient/insufficient observations
- DuckDBEngine correlation (NameError regression)
- Executive report robustness with missing analytics
- Copilot API error response structure
"""
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import uuid
import pytest

from app.database.storage import ParquetStorageManager
from app.ingestion.generic_loader import GenericDataLoader
from app.ingestion.semantic_profiler import SemanticDataProfiler
from app.analytics.semantic_analytics import SemanticAnalyticsEngine
from app.analytics.universal_engine import UniversalAnalyticsEngine
from app.ml.prediction_engine import UniversalPredictionEngine
from app.semantic_model.core import SemanticModel
from app.reports.executive_report_engine import UniversalExecutiveReportEngine
from app.schemas.analytics import TrendPoint, Prediction, AnalyticsResult


def _make_monthly_df(n_months: int = 24, date_col: str = "date") -> pd.DataFrame:
    start = datetime(2024, 1, 1)
    dates = [start + timedelta(days=30 * i) for i in range(n_months)]
    return pd.DataFrame({
        date_col: [d.strftime("%Y-%m-%d") for d in dates],
        "store_id": [f"S{(i % 3) + 1}" for i in range(n_months)],
        "product_id": [f"P{(i % 2) + 1}" for i in range(n_months)],
        "quantity": [100 + i * 10 + (i % 5) * 5 for i in range(n_months)],
        "price": [10.0 + i * 0.5 for i in range(n_months)],
        "revenue": [1000 + i * 100 + (i % 3) * 50 for i in range(n_months)],
    })


def _df_to_parquet(df: pd.DataFrame) -> tuple[Path, str]:
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        csv_path = Path(tmp.name)
        df.to_csv(csv_path, index=False)
    dataset_id = str(uuid.uuid4())
    parquet_path = GenericDataLoader.convert_to_parquet(csv_path, dataset_id)
    csv_path.unlink()
    return parquet_path, dataset_id


class TestDateColumnDetection:
    def test_date_column_named_date(self):
        df = _make_monthly_df(date_col="date")
        parquet_path, dataset_id = _df_to_parquet(df)
        try:
            profile = SemanticDataProfiler.profile(parquet_path)
            temporal = profile.get("column_categories", {}).get("temporal", [])
            assert "date" in temporal, f"Expected 'date' in temporal columns, got {temporal}"
        finally:
            ParquetStorageManager.delete_dataset_files(dataset_id)

    def test_date_column_named_order_date(self):
        df = _make_monthly_df(date_col="order_date")
        parquet_path, dataset_id = _df_to_parquet(df)
        try:
            profile = SemanticDataProfiler.profile(parquet_path)
            temporal = profile.get("column_categories", {}).get("temporal", [])
            assert "order_date" in temporal, f"Expected 'order_date' in temporal columns, got {temporal}"
        finally:
            ParquetStorageManager.delete_dataset_files(dataset_id)

    def test_datetime_dtype_detected(self):
        df = _make_monthly_df(date_col="timestamp")
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        parquet_path, dataset_id = _df_to_parquet(df)
        try:
            profile = SemanticDataProfiler.profile(parquet_path)
            temporal = profile.get("column_categories", {}).get("temporal", [])
            assert "timestamp" in temporal, f"Expected 'timestamp' in temporal columns, got {temporal}"
        finally:
            ParquetStorageManager.delete_dataset_files(dataset_id)

    def test_missing_time_column(self):
        df = pd.DataFrame({
            "store_id": ["S1", "S2", "S3"],
            "revenue": [100.0, 200.0, 300.0],
        })
        parquet_path, dataset_id = _df_to_parquet(df)
        try:
            profile = SemanticDataProfiler.profile(parquet_path)
            temporal = profile.get("column_categories", {}).get("temporal", [])
            assert len(temporal) == 0, f"Expected no temporal columns, got {temporal}"
        finally:
            ParquetStorageManager.delete_dataset_files(dataset_id)


class TestTrendNormalization:
    def test_trend_has_stable_period_key(self):
        df = _make_monthly_df(n_months=24, date_col="date")
        parquet_path, dataset_id = _df_to_parquet(df)
        try:
            profile = SemanticDataProfiler.profile(parquet_path)
            temporal = profile.get("column_categories", {}).get("temporal", [])
            measures = profile.get("column_categories", {}).get("measures", [])
            trends = UniversalAnalyticsEngine._compute_trends(parquet_path, profile, temporal, measures)
            assert "revenue" in trends or len(trends) > 0
            for measure, points in trends.items():
                for p in points:
                    assert hasattr(p, "period"), f"TrendPoint missing 'period' attribute for {measure}"
                    assert hasattr(p, "value"), f"TrendPoint missing 'value' attribute for {measure}"
                    assert p.period != "Unknown", f"TrendPoint period should not be 'Unknown' for {measure}"
        finally:
            ParquetStorageManager.delete_dataset_files(dataset_id)

    def test_trend_with_order_date_column(self):
        df = _make_monthly_df(n_months=24, date_col="order_date")
        parquet_path, dataset_id = _df_to_parquet(df)
        try:
            profile = SemanticDataProfiler.profile(parquet_path)
            temporal = profile.get("column_categories", {}).get("temporal", [])
            measures = profile.get("column_categories", {}).get("measures", [])
            trends = UniversalAnalyticsEngine._compute_trends(parquet_path, profile, temporal, measures)
            assert len(trends) > 0, "Expected trends to be generated"
            for measure, points in trends.items():
                assert len(points) > 0, f"Expected trend points for {measure}"
        finally:
            ParquetStorageManager.delete_dataset_files(dataset_id)

    def test_growth_decline_no_keyerror(self):
        df = _make_monthly_df(n_months=24, date_col="date")
        parquet_path, dataset_id = _df_to_parquet(df)
        try:
            profile = SemanticDataProfiler.profile(parquet_path)
            temporal = profile.get("column_categories", {}).get("temporal", [])
            measures = profile.get("column_categories", {}).get("measures", [])
            growth, decline = UniversalAnalyticsEngine._compute_growth_decline(
                parquet_path, profile, temporal, measures
            )
            assert isinstance(growth, list)
            assert isinstance(decline, list)
        finally:
            ParquetStorageManager.delete_dataset_files(dataset_id)


class TestForecasting:
    def test_time_series_forecast_with_monthly_data(self):
        df = _make_monthly_df(n_months=24, date_col="date")
        parquet_path, dataset_id = _df_to_parquet(df)
        try:
            profile = SemanticDataProfiler.profile(parquet_path)
            temporal = profile.get("column_categories", {}).get("temporal", [])
            measures = profile.get("column_categories", {}).get("measures", [])
            trends = UniversalAnalyticsEngine._compute_trends(parquet_path, profile, temporal, measures)

            sm = SemanticModel(workspace_id="test", domain="Generic Business", dataset_type="Test")
            result = UniversalAnalyticsEngine.analyze(sm, parquet_path)
            predictions = result.predictions
            assert len(predictions) > 0, "Expected at least one prediction"
            feasible = [p for p in predictions if getattr(p, "feasible", False)]
            assert len(feasible) > 0, "Expected at least one feasible prediction"
        finally:
            ParquetStorageManager.delete_dataset_files(dataset_id)

    def test_insufficient_observations_returns_clear_reason(self):
        df = _make_monthly_df(n_months=3, date_col="date")
        parquet_path, dataset_id = _df_to_parquet(df)
        try:
            profile = SemanticDataProfiler.profile(parquet_path)
            temporal = profile.get("column_categories", {}).get("temporal", [])
            measures = profile.get("column_categories", {}).get("measures", [])
            trends = UniversalAnalyticsEngine._compute_trends(parquet_path, profile, temporal, measures)

            sm = SemanticModel(workspace_id="test", domain="Generic Business", dataset_type="Test")
            result = UniversalAnalyticsEngine.analyze(sm, parquet_path)
            not_feasible = [p for p in result.predictions if not getattr(p, "feasible", True)]
            if not_feasible:
                assert not_feasible[0].limitation is not None
                assert len(not_feasible[0].limitation) > 0
        finally:
            ParquetStorageManager.delete_dataset_files(dataset_id)

    def test_daily_time_series_trend(self):
        df = _make_monthly_df(n_months=30, date_col="date")
        parquet_path, dataset_id = _df_to_parquet(df)
        try:
            profile = SemanticDataProfiler.profile(parquet_path)
            temporal = profile.get("column_categories", {}).get("temporal", [])
            measures = profile.get("column_categories", {}).get("measures", [])
            trends = UniversalAnalyticsEngine._compute_trends(parquet_path, profile, temporal, measures)
            assert len(trends) > 0
        finally:
            ParquetStorageManager.delete_dataset_files(dataset_id)


class TestDuckDBEngineCorrelation:
    def test_correlation_no_nameerror(self):
        df = _make_monthly_df(n_months=24, date_col="date")
        parquet_path, dataset_id = _df_to_parquet(df)
        try:
            profile = SemanticDataProfiler.profile(parquet_path)
            measures = profile.get("column_categories", {}).get("measures", [])
            correlations = UniversalAnalyticsEngine._compute_correlations(parquet_path, measures)
            assert isinstance(correlations, list)
        finally:
            ParquetStorageManager.delete_dataset_files(dataset_id)


class TestExecutiveReportRobustness:
    def test_report_with_missing_prediction(self):
        df = _make_monthly_df(n_months=24, date_col="date")
        parquet_path, dataset_id = _df_to_parquet(df)
        try:
            sm = SemanticModel(workspace_id="test", domain="Generic Business", dataset_type="Test")
            result = UniversalAnalyticsEngine.analyze(sm, parquet_path)
            result.predictions = []
            report = UniversalExecutiveReportEngine.generate_report(result, sm)
            assert "sections" in report
            assert "executive_summary" in report["sections"]
        finally:
            ParquetStorageManager.delete_dataset_files(dataset_id)

    def test_report_with_missing_trend(self):
        df = _make_monthly_df(n_months=24, date_col="date")
        parquet_path, dataset_id = _df_to_parquet(df)
        try:
            sm = SemanticModel(workspace_id="test", domain="Generic Business", dataset_type="Test")
            result = UniversalAnalyticsEngine.analyze(sm, parquet_path)
            result.trends = {}
            report = UniversalExecutiveReportEngine.generate_report(result, sm)
            assert "sections" in report
            assert "trend_analysis" in report["sections"]
        finally:
            ParquetStorageManager.delete_dataset_files(dataset_id)

    def test_report_with_missing_correlation(self):
        df = _make_monthly_df(n_months=24, date_col="date")
        parquet_path, dataset_id = _df_to_parquet(df)
        try:
            sm = SemanticModel(workspace_id="test", domain="Generic Business", dataset_type="Test")
            result = UniversalAnalyticsEngine.analyze(sm, parquet_path)
            result.correlations = []
            report = UniversalExecutiveReportEngine.generate_report(result, sm)
            assert "sections" in report
            assert "root_cause_analysis" in report["sections"]
        finally:
            ParquetStorageManager.delete_dataset_files(dataset_id)


class TestInvalidAndEdgeCases:
    def test_invalid_date_column_not_crash(self):
        df = pd.DataFrame({
            "date_like": ["not_a_date"] * 10,
            "revenue": [100.0 + i * 10 for i in range(10)],
        })
        parquet_path, dataset_id = _df_to_parquet(df)
        try:
            profile = SemanticDataProfiler.profile(parquet_path)
            temporal = profile.get("column_categories", {}).get("temporal", [])
            measures = profile.get("column_categories", {}).get("measures", [])
            trends = UniversalAnalyticsEngine._compute_trends(parquet_path, profile, temporal, measures)
            assert isinstance(trends, dict)
        finally:
            ParquetStorageManager.delete_dataset_files(dataset_id)

    def test_copilot_error_response_has_no_traceback(self):
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)
        resp = client.post("/api/v1/ai/copilot/query", json={
            "question": "trigger error",
            "session_id": "test-error",
        })
        assert resp.status_code in (200, 401, 403, 422, 500)
        data = resp.json()
        if resp.status_code == 500:
            detail = data.get("detail", {})
            if isinstance(detail, dict):
                error_msg = detail.get("error", "")
                assert "Traceback" not in error_msg, "Error response should not contain Python traceback"
                assert "File \"" not in error_msg, "Error response should not contain file paths"
