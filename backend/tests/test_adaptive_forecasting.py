import pytest
from app.ml.prediction_engine import UniversalPredictionEngine
from app.semantic_model.core import SemanticModel, TimeColumn
from types import SimpleNamespace

def test_temporal_dataset_forecasting():
    sm = SemanticModel(
        workspace_id="test-temporal",
        domain="Retail",
        time_columns=[TimeColumn(column="order_date", data_type="datetime", granularity="datetime", is_primary_time=True)]
    )
    trend_points = [
        SimpleNamespace(period="2026-01-01", value=100.0),
        SimpleNamespace(period="2026-02-01", value=120.0),
        SimpleNamespace(period="2026-03-01", value=140.0),
        SimpleNamespace(period="2026-04-01", value=160.0),
    ]
    analytics_result = SimpleNamespace(
        trends={"revenue": trend_points},
        correlations=[],
        root_causes=[],
        drivers=[],
        anomalies=[],
        outliers=[],
        kpis=[SimpleNamespace(source_column="revenue")],
        volume=5000,
        confidence_score=95.0,
    )

    preds = UniversalPredictionEngine.generate(analytics_result=analytics_result, semantic_model=sm, horizons=[20, 30, 90, 180])
    assert len(preds) > 0
    assert any(p.feasible for p in preds)
    for p in preds:
        assert hasattr(p, "metric")
        assert hasattr(p, "predicted_value")
        assert hasattr(p, "current_value")
        assert hasattr(p, "expected_change_pct")
        assert hasattr(p, "drivers")
        assert hasattr(p, "horizon")
        assert p.metric == "revenue"
        assert p.current_value == 160.0
        assert p.predicted_value > 0
    ts_preds = [p for p in preds if getattr(p, "time_series_points", [])]
    assert len(ts_preds) > 0
    for p in ts_preds:
        assert isinstance(p.time_series_points, list)
        assert len(p.time_series_points) > 0
        assert "historical" in p.time_series_points[0]
        assert "forecast" in p.time_series_points[-1]

def assert_no_fake_dates_recursive(obj):
    """Recursively asserts that no fake forecast date strings exist in non-temporal predictions."""
    FORBIDDEN_DATE_PATTERNS = ["2026-01", "2026-02", "2026-03", "Next week", "Next month", "Next quarter"]
    if isinstance(obj, str):
        for pattern in FORBIDDEN_DATE_PATTERNS:
            assert pattern not in obj, f"Forbidden fake date string '{pattern}' found in non-temporal response: {obj}"
    elif isinstance(obj, dict):
        for k, v in obj.items():
            assert_no_fake_dates_recursive(k)
            assert_no_fake_dates_recursive(v)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            assert_no_fake_dates_recursive(item)
    elif hasattr(obj, "__dict__"):
        for k, v in vars(obj).items():
            assert_no_fake_dates_recursive(v)

def test_forecast_dataset_a_retail_non_temporal():
    sm = SemanticModel(workspace_id="ds-a-retail", domain="Retail", time_columns=[])
    analytics_result = SimpleNamespace(
        trends={}, correlations=[], root_causes=[], drivers=[], anomalies=[], outliers=[],
        kpis=[SimpleNamespace(source_column="Quantity"), SimpleNamespace(source_column="Price")],
        volume=10000, confidence_score=92.0,
        evidence={"measures_analyzed": ["Invoice", "Quantity", "Price"], "dimensions_analyzed": ["Country"]}
    )

    preds = UniversalPredictionEngine.generate(analytics_result=analytics_result, semantic_model=sm, horizons=[20, 30, 90, 180])
    assert len(preds) > 0
    p = preds[0]
    assert p.feasible is True
    assert "Model-Based" in p.model_type or "Baseline" in p.model_type
    assert hasattr(p, "drivers")
    assert hasattr(p, "horizon")
    assert "Predictive Outlook" in p.time_horizon or "Non-Temporal" in p.time_horizon
    assert_no_fake_dates_recursive(p.to_dict() if hasattr(p, "to_dict") else vars(p))

def test_forecast_dataset_b_healthcare_non_temporal():
    sm = SemanticModel(workspace_id="ds-b-health", domain="Healthcare", time_columns=[])
    analytics_result = SimpleNamespace(
        trends={}, correlations=[], root_causes=[], drivers=[], anomalies=[], outliers=[],
        kpis=[SimpleNamespace(source_column="Age"), SimpleNamespace(source_column="WaitTime"), SimpleNamespace(source_column="TreatmentCost")],
        volume=15000, confidence_score=89.0,
        evidence={"measures_analyzed": ["PatientID", "Age", "WaitTime", "TreatmentCost"], "dimensions_analyzed": ["Department"]}
    )

    preds = UniversalPredictionEngine.generate(analytics_result=analytics_result, semantic_model=sm, horizons=[20, 30, 90, 180])
    assert len(preds) > 0
    p = preds[0]
    assert p.feasible is True
    assert "PatientID" not in p.prediction
    assert hasattr(p, "drivers")
    assert len(p.drivers) > 0
    assert_no_fake_dates_recursive(p.to_dict() if hasattr(p, "to_dict") else vars(p))

def test_forecast_dataset_c_manufacturing_non_temporal():
    sm = SemanticModel(workspace_id="ds-c-mfg", domain="Manufacturing", time_columns=[])
    analytics_result = SimpleNamespace(
        trends={}, correlations=[], root_causes=[], drivers=[], anomalies=[], outliers=[],
        kpis=[SimpleNamespace(source_column="Temperature"), SimpleNamespace(source_column="Vibration"), SimpleNamespace(source_column="ProductionOutput")],
        volume=8000, confidence_score=94.0,
        evidence={"measures_analyzed": ["MachineID", "Temperature", "Vibration", "Pressure", "ProductionOutput"], "dimensions_analyzed": ["Factory"]}
    )

    preds = UniversalPredictionEngine.generate(analytics_result=analytics_result, semantic_model=sm, horizons=[20, 30, 90, 180])
    assert len(preds) > 0
    p = preds[0]
    assert p.feasible is True
    assert "MachineID" not in p.prediction
    assert hasattr(p, "drivers")
    assert len(p.drivers) > 0
    assert_no_fake_dates_recursive(p.to_dict() if hasattr(p, "to_dict") else vars(p))

def test_forecast_dataset_d_temporal_retail():
    sm = SemanticModel(
        workspace_id="ds-d-temporal", domain="Retail",
        time_columns=[TimeColumn(column="InvoiceDate", data_type="datetime", granularity="datetime", is_primary_time=True)]
    )
    trend_points = [
        SimpleNamespace(period="2026-01-01", value=100.0),
        SimpleNamespace(period="2026-02-01", value=150.0),
        SimpleNamespace(period="2026-03-01", value=200.0),
    ]
    analytics_result = SimpleNamespace(
        trends={"Revenue": trend_points}, correlations=[], root_causes=[], drivers=[], anomalies=[], outliers=[],
        kpis=[SimpleNamespace(source_column="Revenue")], volume=20000, confidence_score=96.0,
        evidence={"temporal_columns": ["InvoiceDate"]}
    )

    preds = UniversalPredictionEngine.generate(analytics_result=analytics_result, semantic_model=sm, horizons=[20, 30, 90, 180])
    assert len(preds) > 0
    assert any(p.feasible for p in preds)

def test_forecast_dataset_e_categorical_only():
    sm = SemanticModel(workspace_id="ds-e-cat", domain="Marketing", time_columns=[])
    analytics_result = SimpleNamespace(
        trends={}, correlations=[], root_causes=[], drivers=[], anomalies=[], outliers=[],
        kpis=[], volume=120, confidence_score=40.0,
        evidence={"measures_analyzed": [], "dimensions_analyzed": ["Region", "Category", "Status"]}
    )

    preds = UniversalPredictionEngine.generate(analytics_result=analytics_result, semantic_model=sm, horizons=[20, 30, 90, 180])
    assert len(preds) > 0
    p = preds[0]
    assert p.feasible is False
    assert "No suitable numeric target was found" in p.prediction or "No numeric measures" in p.prediction

def test_forecast_horizons_are_20_30_90_180():
    sm = SemanticModel(
        workspace_id="test-horizons", domain="Retail",
        time_columns=[TimeColumn(column="order_date", data_type="datetime", granularity="datetime", is_primary_time=True)]
    )
    trend_points = [
        SimpleNamespace(period="2026-01-01", value=100.0),
        SimpleNamespace(period="2026-02-01", value=110.0),
        SimpleNamespace(period="2026-03-01", value=120.0),
    ]
    analytics_result = SimpleNamespace(
        trends={"sales": trend_points},
        correlations=[], root_causes=[], drivers=[], anomalies=[], outliers=[],
        kpis=[SimpleNamespace(source_column="sales")],
        volume=5000, confidence_score=90.0,
    )
    preds = UniversalPredictionEngine.generate(analytics_result=analytics_result, semantic_model=sm, horizons=[20, 30, 90, 180])
    assert len(preds) >= 4
    horizon_labels = [p.horizon for p in preds]
    assert any("20" in h for h in horizon_labels)
    assert any("30" in h for h in horizon_labels)
    assert any("90" in h or "3 Month" in h for h in horizon_labels)
    assert any("180" in h or "6 Month" in h for h in horizon_labels)

def test_forecast_summary_in_analytics_result():
    from app.analytics.universal_engine import UniversalAnalyticsEngine
    from app.ml.prediction_engine import UniversalPredictionEngine
    from app.semantic_model.core import SemanticModel, TimeColumn
    from types import SimpleNamespace

    sm = SemanticModel(
        workspace_id="test-summary", domain="Retail", dataset_type="Temporal",
        time_columns=[TimeColumn(column="date", data_type="datetime", granularity="datetime", is_primary_time=True)]
    )
    trend_points = [
        SimpleNamespace(period="2026-01-01", value=100.0),
        SimpleNamespace(period="2026-02-01", value=120.0),
        SimpleNamespace(period="2026-03-01", value=140.0),
    ]
    analytics_result = SimpleNamespace(
        trends={"revenue": trend_points},
        correlations=[], root_causes=[], drivers=[], anomalies=[], outliers=[],
        kpis=[SimpleNamespace(source_column="revenue")],
        volume=5000, confidence_score=95.0,
    )
    preds = UniversalPredictionEngine.generate(analytics_result=analytics_result, semantic_model=sm, horizons=[20, 30, 90, 180])

    summary = UniversalAnalyticsEngine._compute_forecast_summary(preds, ["date"], ["revenue"], "Retail")
    assert summary is not None
    assert "outlook" in summary
    assert "expected_change_pct" in summary
    assert "risk" in summary
    assert "management_action" in summary
    assert summary["has_temporal_data"] is True
    assert summary["forecast_models_count"] >= 1
    assert summary["feasible_forecasts_count"] >= 1
    assert "revenue" in summary["primary_metric"].lower()
