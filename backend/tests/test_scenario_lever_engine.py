"""
Scenario Lever Engine Tests

Validates data-driven scenario lever discovery and simulation
across diverse dataset types without hardcoded business assumptions.
"""
import math
import uuid

import pandas as pd
import pytest

from app.services.scenario_lever_engine import ScenarioLeverEngine


def _make_profile(df: pd.DataFrame, identifier_cols: list = None) -> dict:
    """Build a minimal profile dict from a dataframe."""
    profile = {
        "total_rows": len(df),
        "columns": {},
        "column_categories": {
            "measures": [],
            "dimensions": [],
            "temporal": [],
            "identifiers": identifier_cols or [],
        },
    }
    for col in df.columns:
        col_data = df[col]
        null_count = int(col_data.isna().sum())
        non_null_count = len(df) - null_count
        distinct_count = int(col_data.nunique())
        stats = {}
        if pd.api.types.is_numeric_dtype(col_data):
            profile["column_categories"]["measures"].append(col)
            valid = col_data.dropna()
            if len(valid) > 0:
                stats = {
                    "mean": float(valid.mean()),
                    "sum": float(valid.sum()),
                    "min": float(valid.min()),
                    "max": float(valid.max()),
                    "stddev": float(valid.std()) if len(valid) > 1 else 0.0,
                    "median": float(valid.median()),
                }
        else:
            profile["column_categories"]["dimensions"].append(col)

        profile["columns"][col] = {
            "data_type": "DOUBLE" if pd.api.types.is_numeric_dtype(col_data) else "VARCHAR",
            "null_percentage": round(null_count / max(len(df), 1) * 100, 2),
            "non_null_count": non_null_count,
            "distinct_count": distinct_count,
            "stats": stats,
        }
    return profile


def _make_semantic_model(column_classifications=None):
    class MockSemanticModel:
        def __init__(self):
            self.workspace_id = f"ws-{uuid.uuid4().hex[:8]}"
            self.column_classifications = column_classifications or []

    return MockSemanticModel()


class TestScenarioLeverDiscovery:
    """Test lever discovery across different dataset types."""

    def test_retail_dataset_discovers_quantity_and_price(self):
        df = pd.DataFrame({
            "Invoice": range(1000),
            "StockCode": [f"SKU{i%100}" for i in range(1000)],
            "Quantity": [1 + (i % 10) for i in range(1000)],
            "Price": [1.0 + (i % 50) * 0.1 for i in range(1000)],
            "Country": ["UK", "US", "DE", "FR", "ES"] * 200,
        })
        profile = _make_profile(df)
        result = ScenarioLeverEngine.discover_levers(profile)
        lever_cols = [l["column"] for l in result["available_levers"]]
        assert "Quantity" in lever_cols, f"Quantity should be a lever, got {lever_cols}"
        assert "Price" in lever_cols, f"Price should be a lever, got {lever_cols}"
        assert result["scenario_capability"]["supported"] is True

    def test_healthcare_dataset_discovers_numeric_levers(self):
        df = pd.DataFrame({
            "PatientID": [f"P{i:04d}" for i in range(100)],
            "Age": [20 + (i % 5) * 10 for i in range(100)],
            "WaitTime": [10 + (i % 12) * 10 for i in range(100)],
            "TreatmentCost": [100.0 + (i % 10) * 500 for i in range(100)],
            "Department": ["Cardiology", "Neurology", "Orthopedics", "Pediatrics"] * 25,
        })
        profile = _make_profile(df, identifier_cols=["PatientID"])
        result = ScenarioLeverEngine.discover_levers(profile)
        lever_cols = [l["column"] for l in result["available_levers"]]
        assert "Age" in lever_cols, f"Age should be a lever, got {lever_cols}"
        assert "WaitTime" in lever_cols, f"WaitTime should be a lever, got {lever_cols}"
        assert "TreatmentCost" in lever_cols, f"TreatmentCost should be a lever, got {lever_cols}"
        assert "PatientID" not in lever_cols, f"PatientID should be excluded, got {lever_cols}"
        assert "Department" not in lever_cols, f"Department should be excluded, got {lever_cols}"
        assert result["scenario_capability"]["supported"] is True

    def test_manufacturing_dataset_discovers_operational_levers(self):
        factory_vals = ["Factory-A", "Factory-B", "Factory-C"] * 67
        df = pd.DataFrame({
            "MachineID": [f"MCH-{i%20:03d}" for i in range(200)],
            "Temperature": [65.0 + (i % 10) * 2 for i in range(200)],
            "Vibration": [0.1 + (i % 5) * 0.05 for i in range(200)],
            "Pressure": [100.0 + (i % 8) * 5 for i in range(200)],
            "Factory": factory_vals[:200],
        })
        profile = _make_profile(df, identifier_cols=["MachineID"])
        result = ScenarioLeverEngine.discover_levers(profile)
        lever_cols = [l["column"] for l in result["available_levers"]]
        assert "Temperature" in lever_cols, f"Temperature should be a lever, got {lever_cols}"
        assert "Vibration" in lever_cols, f"Vibration should be a lever, got {lever_cols}"
        assert "Pressure" in lever_cols, f"Pressure should be a lever, got {lever_cols}"
        assert "MachineID" not in lever_cols, f"MachineID should be excluded, got {lever_cols}"
        assert "Factory" not in lever_cols, f"Factory should be excluded, got {lever_cols}"

    def test_categorical_only_dataset_has_no_levers(self):
        df = pd.DataFrame({
            "Region": ["North", "South", "East", "West"] * 25,
            "Category": ["A", "B", "C", "D", "E"] * 20,
            "Status": ["Active", "Inactive", "Pending"] * 33 + ["Active"],
        })
        profile = _make_profile(df)
        result = ScenarioLeverEngine.discover_levers(profile)
        assert len(result["available_levers"]) == 0, f"Expected no levers, got {result['available_levers']}"
        assert result["scenario_capability"]["supported"] is False

    def test_identifier_heavy_dataset_excludes_ids(self):
        df = pd.DataFrame({
            "CustomerID": [f"CUST-{i}" for i in range(100)],
            "TransactionID": [f"TXN-{i}" for i in range(100)],
            "Amount": [10.0 + (i % 20) * 2 for i in range(100)],
            "Region": ["US", "EU", "APAC"] * 33 + ["US"],
        })
        classifications = [
            {"name": "CustomerID", "semantic_type": "customer_id", "business_role": "identifier"},
            {"name": "TransactionID", "semantic_type": "transaction_id", "business_role": "identifier"},
            {"name": "Amount", "semantic_type": "measure", "business_role": "measure"},
        ]
        semantic_model = _make_semantic_model(column_classifications=classifications)
        profile = _make_profile(df)
        result = ScenarioLeverEngine.discover_levers(profile, semantic_model=semantic_model)
        lever_cols = [l["column"] for l in result["available_levers"]]
        assert "Amount" in lever_cols, f"Amount should be a lever, got {lever_cols}"
        assert "CustomerID" not in lever_cols, f"CustomerID should be excluded, got {lever_cols}"
        assert "TransactionID" not in lever_cols, f"TransactionID should be excluded, got {lever_cols}"

    def test_zero_variance_metric_excluded(self):
        df = pd.DataFrame({
            "ConstantMetric": [5.0] * 100,
            "VariableMetric": [1.0 + (i % 10) * 2 for i in range(100)],
            "Category": ["A", "B"] * 50,
        })
        profile = _make_profile(df)
        result = ScenarioLeverEngine.discover_levers(profile)
        lever_cols = [l["column"] for l in result["available_levers"]]
        assert "VariableMetric" in lever_cols, f"VariableMetric should be a lever, got {lever_cols}"
        assert "ConstantMetric" not in lever_cols, f"ConstantMetric should be excluded, got {lever_cols}"

    def test_high_missing_values_excluded(self):
        df = pd.DataFrame({
            "SparseMetric": [1.0, None, None, None] * 25,
            "DenseMetric": [1.0 + (i % 10) * 2 for i in range(100)],
            "Category": ["A", "B"] * 50,
        })
        profile = _make_profile(df)
        result = ScenarioLeverEngine.discover_levers(profile)
        lever_cols = [l["column"] for l in result["available_levers"]]
        assert "DenseMetric" in lever_cols, f"DenseMetric should be a lever, got {lever_cols}"
        assert "SparseMetric" not in lever_cols, f"SparseMetric should be excluded, got {lever_cols}"

    def test_near_unique_numeric_excluded_as_identifier(self):
        df = pd.DataFrame({
            "SurrogateID": range(100),
            "Metric": [1.0 + (i % 10) * 2 for i in range(100)],
        })
        profile = _make_profile(df)
        result = ScenarioLeverEngine.discover_levers(profile)
        lever_cols = [l["column"] for l in result["available_levers"]]
        assert "Metric" in lever_cols, f"Metric should be a lever, got {lever_cols}"
        assert "SurrogateID" not in lever_cols, f"SurrogateID should be excluded, got {lever_cols}"


class TestScenarioSimulation:
    """Test scenario simulation math and evidence handling."""

    def test_single_lever_simulation(self):
        df = pd.DataFrame({
            "Metric": [10.0 + (i % 10) for i in range(100)],
            "Category": ["A", "B"] * 50,
        })
        profile = _make_profile(df)
        result = ScenarioLeverEngine.simulate(
            workspace_id="ws-test",
            changes=[{"lever_id": "metric", "change_pct": 10}],
            profile=profile,
        )
        assert result["workspace_id"] == "ws-test"
        assert "Metric" in result["baseline"]
        assert "Metric" in result["scenario"]
        assert result["baseline"]["Metric"] > 0
        assert abs(result["scenario"]["Metric"] - result["baseline"]["Metric"] * 1.1) < 0.01
        assert len(result["applied_changes"]) == 1

    def test_multiple_levers_simulation(self):
        df = pd.DataFrame({
            "MetricA": [10.0 + (i % 10) for i in range(100)],
            "MetricB": [5.0 + (i % 8) * 0.5 for i in range(100)],
        })
        profile = _make_profile(df)
        result = ScenarioLeverEngine.simulate(
            workspace_id="ws-test",
            changes=[
                {"lever_id": "metrica", "change_pct": 10},
                {"lever_id": "metricb", "change_pct": -5},
            ],
            profile=profile,
        )
        assert len(result["applied_changes"]) == 2

    def test_no_changes_returns_empty(self):
        df = pd.DataFrame({"Metric": [1.0, 2.0, 3.0]})
        profile = _make_profile(df)
        result = ScenarioLeverEngine.simulate(
            workspace_id="ws-test",
            changes=[],
            profile=profile,
        )
        assert result["confidence"] == 0.0

    def test_unknown_lever_ignored(self):
        df = pd.DataFrame({"Metric": [1.0, 2.0, 3.0]})
        profile = _make_profile(df)
        result = ScenarioLeverEngine.simulate(
            workspace_id="ws-test",
            changes=[{"lever_id": "nonexistent", "change_pct": 10}],
            profile=profile,
        )
        assert len(result["applied_changes"]) == 0

    def test_negative_change_produces_lower_scenario(self):
        df = pd.DataFrame({"Metric": [100.0] * 100})
        profile = _make_profile(df)
        result = ScenarioLeverEngine.simulate(
            workspace_id="ws-test",
            changes=[{"lever_id": "metric", "change_pct": -10}],
            profile=profile,
        )
        assert result["scenario"]["Metric"] < result["baseline"]["Metric"]

    def test_simulation_evidence_is_transparent(self):
        df = pd.DataFrame({"Metric": [10.0 + (i % 10) for i in range(100)]})
        profile = _make_profile(df)
        result = ScenarioLeverEngine.simulate(
            workspace_id="ws-test",
            changes=[{"lever_id": "metric", "change_pct": 5}],
            profile=profile,
        )
        assert "methodology" in result
        assert "Hypothetical" in result["methodology"]
        assert "limitations" in result


class TestScenarioLeverIntegration:
    """Test integration with correlations."""

    def test_correlations_identify_affected_metrics(self):
        df = pd.DataFrame({
            "Quantity": [1.0 + (i % 10) for i in range(100)],
            "Amount": [10.0 + (i % 10) * 5 for i in range(100)],
        })
        profile = _make_profile(df)
        correlations = [
            {"column_a": "Quantity", "column_b": "Amount", "coefficient": 0.95},
        ]
        analytics_result = type("MockAnalytics", (), {"correlations": correlations})()
        result = ScenarioLeverEngine.discover_levers(
            profile=profile,
            analytics_result=analytics_result,
        )
        quantity_lever = next((l for l in result["available_levers"] if l["column"] == "Quantity"), None)
        assert quantity_lever is not None, f"Quantity lever not found in {[l['column'] for l in result['available_levers']]}"
        affected_cols = [m["column"] for m in quantity_lever.get("affected_metrics", [])]
        assert "Amount" in affected_cols, f"Amount should be affected, got {affected_cols}"

    def test_no_correlation_gives_safe_limitation(self):
        df = pd.DataFrame({
            "MetricA": [1.0 + (i % 10) for i in range(100)],
            "MetricB": [10.0 + (i % 10) for i in range(100)],
        })
        profile = _make_profile(df)
        result = ScenarioLeverEngine.simulate(
            workspace_id="ws-test",
            changes=[{"lever_id": "MetricA", "change_pct": 10}],
            profile=profile,
        )
        assert result["confidence"] <= 0.55


class TestUniversalScenarioDiscovery:
    """Test that the engine works with any structured dataset, not just retail."""

    def test_education_dataset_discovers_generic_levers(self):
        df = pd.DataFrame({
            "StudentID": [f"S{i:03d}" for i in range(100)],
            "StudyHours": [1.0 + (i % 10) for i in range(100)],
            "Attendance": [60.0 + (i % 41) for i in range(100)],
            "Marks": [30.0 + (i % 71) for i in range(100)],
            "PreviousScore": [25.0 + (i % 60) for i in range(100)],
        })
        profile = _make_profile(df, identifier_cols=["StudentID"])
        result = ScenarioLeverEngine.discover_levers(profile)
        lever_cols = [l["column"] for l in result["available_levers"]]
        assert "StudyHours" in lever_cols
        assert "Attendance" in lever_cols
        assert "Marks" in lever_cols
        assert "PreviousScore" in lever_cols
        assert "StudentID" not in lever_cols
        assert result["scenario_capability"]["supported"] is True

    def test_hr_dataset_discovers_generic_levers(self):
        df = pd.DataFrame({
            "EmployeeID": [f"E{i:03d}" for i in range(100)],
            "Salary": [30000.0 + (i % 50) * 1000 for i in range(100)],
            "Experience": [0.5 + (i % 20) for i in range(100)],
            "Performance": [1.0 + (i % 5) for i in range(100)],
            "Satisfaction": [1.0 + (i % 10) * 0.5 for i in range(100)],
        })
        profile = _make_profile(df, identifier_cols=["EmployeeID"])
        result = ScenarioLeverEngine.discover_levers(profile)
        lever_cols = [l["column"] for l in result["available_levers"]]
        assert "Salary" in lever_cols
        assert "Experience" in lever_cols
        assert "Performance" in lever_cols
        assert "Satisfaction" in lever_cols
        assert "EmployeeID" not in lever_cols
        assert result["scenario_capability"]["supported"] is True

    def test_finance_dataset_discovers_generic_levers(self):
        df = pd.DataFrame({
            "TransactionID": [f"T{i:04d}" for i in range(100)],
            "TransactionAmount": [10.0 + (i % 1000) * 3.7 for i in range(100)],
            "Balance": [1000.0 + (i % 5000) * 1.3 for i in range(100)],
            "CreditScore": [300.0 + (i % 550) * 0.8 for i in range(100)],
            "AccountAge": [1.0 + (i % 120) * 0.5 for i in range(100)],
        })
        profile = _make_profile(df, identifier_cols=["TransactionID"])
        result = ScenarioLeverEngine.discover_levers(profile)
        lever_cols = [l["column"] for l in result["available_levers"]]
        assert "TransactionAmount" in lever_cols
        assert "Balance" in lever_cols
        assert "CreditScore" in lever_cols
        assert "AccountAge" in lever_cols
        assert "TransactionID" not in lever_cols
        assert result["scenario_capability"]["supported"] is True

    def test_manufacturing_dataset_discovers_generic_levers(self):
        df = pd.DataFrame({
            "MachineID": [f"MCH-{i%20:03d}" for i in range(200)],
            "Temperature": [65.0 + (i % 10) * 2 for i in range(200)],
            "Vibration": [0.1 + (i % 5) * 0.05 for i in range(200)],
            "Pressure": [100.0 + (i % 8) * 5 for i in range(200)],
            "ProductionRate": [50.0 + (i % 30) for i in range(200)],
            "DefectRate": [0.1 + (i % 10) * 0.5 for i in range(200)],
        })
        profile = _make_profile(df, identifier_cols=["MachineID"])
        result = ScenarioLeverEngine.discover_levers(profile)
        lever_cols = [l["column"] for l in result["available_levers"]]
        assert "Temperature" in lever_cols
        assert "Vibration" in lever_cols
        assert "Pressure" in lever_cols
        assert "ProductionRate" in lever_cols
        assert "DefectRate" in lever_cols
        assert "MachineID" not in lever_cols
        assert result["scenario_capability"]["supported"] is True

    def test_generic_dataset_without_business_names(self):
        df = pd.DataFrame({
            "ColA": [10.0 + (i % 10) for i in range(100)],
            "ColB": [5.0 + (i % 8) * 0.5 for i in range(100)],
            "ColC": [100.0 + (i % 50) for i in range(100)],
        })
        profile = _make_profile(df)
        result = ScenarioLeverEngine.discover_levers(profile)
        lever_cols = [l["column"] for l in result["available_levers"]]
        assert "ColA" in lever_cols
        assert "ColB" in lever_cols
        assert "ColC" in lever_cols
        assert result["scenario_capability"]["supported"] is True
        assert len(result["presets"]) > 0

    def test_simulation_without_correlation_returns_directional_estimate(self):
        df = pd.DataFrame({
            "MetricA": [10.0 + (i % 10) for i in range(100)],
            "MetricB": [5.0 + (i % 8) * 0.5 for i in range(100)],
        })
        profile = _make_profile(df)
        result = ScenarioLeverEngine.simulate(
            workspace_id="ws-test",
            changes=[{"lever_id": "MetricA", "change_pct": 10}],
            profile=profile,
        )
        assert result["confidence"] <= 0.55
        assert "Insufficient evidence" not in result.get("recommendation", "")
        assert "directional" in result.get("recommendation", "").lower() or "model-based" in result.get("recommendation", "").lower()

    def test_simulation_with_insufficient_data_returns_low_confidence(self):
        df = pd.DataFrame({
            "MetricA": [10.0] * 10,
        })
        profile = _make_profile(df)
        result = ScenarioLeverEngine.simulate(
            workspace_id="ws-test",
            changes=[{"lever_id": "MetricA", "change_pct": 10}],
            profile=profile,
        )
        assert result["confidence"] <= 0.55

    def test_presets_generated_for_any_numeric_dataset(self):
        df = pd.DataFrame({
            "Alpha": [10.0 + (i % 10) for i in range(100)],
            "Beta": [5.0 + (i % 8) * 0.5 for i in range(100)],
            "Gamma": [100.0 + (i % 50) for i in range(100)],
        })
        profile = _make_profile(df)
        result = ScenarioLeverEngine.discover_levers(profile)
        assert len(result["presets"]) > 0
        preset_ids = [p["id"] for p in result["presets"]]
        assert "single_adjustment" in preset_ids
        assert "dual_adjustment" in preset_ids

    def test_derived_metric_detection(self):
        df = pd.DataFrame({
            "quantity": [1.0 + (i % 10) for i in range(100)],
            "price": [10.0 + (i % 50) for i in range(100)],
        })
        df["revenue"] = df["quantity"] * df["price"]
        profile = _make_profile(df)
        result = ScenarioLeverEngine.discover_levers(profile)
        lever_cols = [l["column"] for l in result["available_levers"]]
        assert "quantity" in lever_cols
        assert "price" in lever_cols
        assert "revenue" in lever_cols

    def test_high_cardinality_retail_measures_discovered(self):
        df = pd.DataFrame({
            "revenue": [10.0 + (i % 1000) * 0.5 for i in range(1000)],
            "cost": [5.0 + (i % 800) * 0.3 for i in range(1000)],
            "profit": [2.0 + (i % 600) * 0.2 for i in range(1000)],
            "quantity": [1 + (i % 50) for i in range(1000)],
            "customers": [100 + (i % 900) for i in range(1000)],
            "unit_price": [5.0 + (i % 200) * 0.1 for i in range(1000)],
        })
        profile = _make_profile(df)
        result = ScenarioLeverEngine.discover_levers(profile)
        lever_cols = [l["column"] for l in result["available_levers"]]
        assert "revenue" in lever_cols, f"revenue should be a lever, got {lever_cols}"
        assert "cost" in lever_cols, f"cost should be a lever, got {lever_cols}"
        assert "profit" in lever_cols, f"profit should be a lever, got {lever_cols}"
        assert "quantity" in lever_cols, f"quantity should be a lever, got {lever_cols}"
        assert "customers" in lever_cols, f"customers should be a lever, got {lever_cols}"
        assert "unit_price" in lever_cols, f"unit_price should be a lever, got {lever_cols}"
        assert result["scenario_capability"]["supported"] is True

    def test_metric_type_classification(self):
        df = pd.DataFrame({
            "revenue": [10.0 + i for i in range(100)],
            "discount_rate": [0.1 + i * 0.001 for i in range(100)],
            "quantity": [1 + i for i in range(100)],
            "rating": [1 + (i % 5) for i in range(100)],
        })
        profile = _make_profile(df)
        result = ScenarioLeverEngine.discover_levers(profile)
        lever_map = {l["column"]: l for l in result["available_levers"]}
        assert lever_map["revenue"]["metric_type"] == "currency"
        assert lever_map["discount_rate"]["metric_type"] == "percentage"
        assert lever_map["quantity"]["metric_type"] == "volume"
        assert lever_map["rating"]["metric_type"] == "forecastable"

    def test_simulate_returns_categorized_metrics(self):
        df = pd.DataFrame({
            "revenue": [10.0 + i for i in range(100)],
            "cost": [5.0 + i * 0.5 for i in range(100)],
            "quantity": [1 + i for i in range(100)],
        })
        profile = _make_profile(df)
        result = ScenarioLeverEngine.simulate(
            workspace_id="ws-test",
            changes=[{"lever_id": "revenue", "change_pct": 10}],
            profile=profile,
        )
        assert "kpis" in result
        assert "currency_metrics" in result
        assert "volume_metrics" in result
        assert len(result["currency_metrics"]) >= 1
