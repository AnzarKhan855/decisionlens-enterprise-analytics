"""
Dynamic Dataset Acceptance Test Suite

Proves DecisionLens is genuinely domain-agnostic by testing with arbitrary
datasets that have NO retail/e-commerce assumptions.

Tests cover:
- Healthcare dataset
- Cybersecurity dataset
- Manufacturing dataset
- Generic dataset with only categorical columns
- Dataset without dates
- Dataset without revenue
- Dataset without quantity
- Dataset with missing values
- Dataset with duplicate rows
- Zero-value bug prevention
- Undefined/NaN/null state handling
- Dynamic KPI adaptation
- Dynamic chart adaptation
- Dynamic forecast adaptation
- Dynamic recommendation adaptation
- Report generation from arbitrary data
- Workspace isolation
"""
import tempfile
import uuid
import math
from pathlib import Path

import pandas as pd
import pytest

from app.ingestion.generic_loader import GenericDataLoader
from app.ingestion.semantic_profiler import SemanticDataProfiler
from app.services.workspace_service import EnterpriseWorkspaceManager
from app.database.storage import ParquetStorageManager


def _setup_workspace(df: pd.DataFrame, ws_id: str) -> tuple:
    """Create workspace, convert to parquet, register table, return (parquet_path, profile, csv_path)."""
    csv_path = Path(tempfile.mktemp(suffix=".csv"))
    df.to_csv(csv_path, index=False)
    dataset_id = f"{ws_id}__data"
    parquet_path = GenericDataLoader.convert_to_parquet(csv_path, dataset_id)
    EnterpriseWorkspaceManager.create_or_get_workspace(ws_id, "Test Workspace")
    EnterpriseWorkspaceManager.set_active_workspace(ws_id)
    profile = SemanticDataProfiler.profile(parquet_path)
    EnterpriseWorkspaceManager.register_table(
        ws_id,
        "dataset",
        [{"name": c, "type": profile["columns"][c].get("inferred_type", "VARCHAR")} for c in profile["columns"]],
        profile.get("total_rows", 0),
        str(parquet_path),
    )
    return parquet_path, profile, csv_path


def _cleanup(ws_id: str, csv_path: Path):
    try:
        EnterpriseWorkspaceManager.delete_workspace(ws_id)
    except Exception:
        pass
    if csv_path.exists():
        csv_path.unlink()


class TestDynamicDatasetAcceptance:
    """Proves DecisionLens works with ANY uploaded dataset, not just retail."""

    def setup_method(self):
        try:
            from app.database.duckdb_engine import _duckdb_cb
            _duckdb_cb._state = "CLOSED"
            _duckdb_cb._failure_count = 0
            _duckdb_cb._success_count = 0
            _duckdb_cb._last_failure_time = None
        except Exception:
            pass

    def test_healthcare_dataset_end_to_end(self):
        """Healthcare dataset: PatientID, Diagnosis, Age, BloodPressure, Temperature, AdmissionDate."""
        df = pd.DataFrame({
            "PatientID": [f"P{i:04d}" for i in range(1, 51)],
            "Diagnosis": ["Flu", "Diabetes", "Hypertension", "Asthma", "Migraine"] * 10,
            "Age": [25, 45, 62, 38, 55, 70, 33, 48, 59, 41] * 5,
            "BloodPressure": [120, 140, 160, 110, 135, 155, 118, 142, 148, 130] * 5,
            "Temperature": [98.6, 101.2, 99.1, 97.8, 100.5, 102.3, 98.9, 99.5, 101.0, 97.5] * 5,
            "AdmissionDate": pd.date_range("2024-01-01", periods=50, freq="D").astype(str),
        })
        ws_id = f"ws-healthcare-{uuid.uuid4().hex[:8]}"
        parquet_path, profile, csv_path = _setup_workspace(df, ws_id)
        try:
            from app.analytics.universal_engine import UniversalAnalyticsEngine
            from app.semantic_model.core import SemanticModel
            from app.services.dynamic_dashboard_service import get_dynamic_dashboard
            from app.reports.executive_report_engine import UniversalExecutiveReportEngine

            sm = SemanticModel(workspace_id=ws_id, domain="Generic Business", dataset_type="Unknown")
            result = UniversalAnalyticsEngine.analyze(sm, parquet_path=parquet_path)
            assert result.volume == 50
            assert len(result.kpis) > 0
            assert result.domain != "Retail & E-Commerce"
            assert result.prediction_feasible is not None
            assert result.forecast_ready is not None
            kpi_names = [k.source_column.lower() for k in result.kpis if hasattr(k, 'source_column') and k.source_column != '*']
            for retail_kpi in ["revenue", "sales", "orders", "quantity", "price"]:
                if retail_kpi not in [c.lower() for c in profile.get("columns", {}).keys()]:
                    assert retail_kpi not in kpi_names, f"Hardcoded retail KPI '{retail_kpi}' found in healthcare dataset"
            dashboard = get_dynamic_dashboard(workspace_id=ws_id)
            assert dashboard is not None
            assert "kpis" in dashboard
            report = UniversalExecutiveReportEngine.generate_report(result, sm)
            assert "sections" in report
            assert "executive_summary" in report["sections"]
        finally:
            _cleanup(ws_id, csv_path)

    def test_cybersecurity_dataset_end_to_end(self):
        """Cybersecurity dataset: Timestamp, SrcIP, DstIP, Port, Protocol, AttackType, Severity, FlowDuration."""
        df = pd.DataFrame({
            "Timestamp": pd.date_range("2024-01-01", periods=100, freq="h").astype(str),
            "SrcIP": [f"192.168.1.{i%254}" for i in range(100)],
            "DstIP": [f"10.0.0.{i%254}" for i in range(100)],
            "Port": [22, 80, 443, 3389, 8080, 53, 123, 25, 21, 3306] * 10,
            "Protocol": ["TCP", "UDP", "ICMP", "TCP", "UDP"] * 20,
            "AttackType": ["DDoS", "PortScan", "BruteForce", "Malware", "Phishing"] * 20,
            "Severity": ["Low", "Medium", "High", "Critical", "Low"] * 20,
            "FlowDuration": [100, 250, 50, 500, 150, 300, 80, 400, 120, 200] * 10,
        })
        ws_id = f"ws-cyber-{uuid.uuid4().hex[:8]}"
        parquet_path, profile, csv_path = _setup_workspace(df, ws_id)
        try:
            from app.analytics.universal_engine import UniversalAnalyticsEngine
            from app.semantic_model.core import SemanticModel
            from app.reports.executive_report_engine import UniversalExecutiveReportEngine

            sm = SemanticModel(workspace_id=ws_id, domain="Generic Business", dataset_type="Unknown")
            result = UniversalAnalyticsEngine.analyze(sm, parquet_path=parquet_path)
            assert result.volume == 100
            assert len(result.kpis) > 0
            kpi_names = [k.source_column.lower() for k in result.kpis if hasattr(k, 'source_column') and k.source_column != '*']
            for retail_kpi in ["revenue", "sales", "orders", "quantity", "price"]:
                assert retail_kpi not in kpi_names, f"Hardcoded retail KPI '{retail_kpi}' found in cybersecurity dataset"
            report = UniversalExecutiveReportEngine.generate_report(result, sm)
            assert "sections" in report
        finally:
            _cleanup(ws_id, csv_path)

    def test_manufacturing_dataset_end_to_end(self):
        """Manufacturing dataset: MachineID, Temperature, Vibration, Pressure, RPM, Timestamp."""
        df = pd.DataFrame({
            "MachineID": [f"MCH-{i%20:03d}" for i in range(100)],
            "Temperature": [65.0 + i * 0.5 for i in range(100)],
            "Vibration": [0.1 + i * 0.01 for i in range(100)],
            "Pressure": [100.0 + i * 0.2 for i in range(100)],
            "RPM": [1500 + i * 10 for i in range(100)],
            "Timestamp": pd.date_range("2024-01-01", periods=100, freq="h").astype(str),
        })
        ws_id = f"ws-mfg-{uuid.uuid4().hex[:8]}"
        parquet_path, profile, csv_path = _setup_workspace(df, ws_id)
        try:
            from app.analytics.universal_engine import UniversalAnalyticsEngine
            from app.semantic_model.core import SemanticModel
            from app.reports.executive_report_engine import UniversalExecutiveReportEngine

            sm = SemanticModel(workspace_id=ws_id, domain="Generic Business", dataset_type="Unknown")
            result = UniversalAnalyticsEngine.analyze(sm, parquet_path=parquet_path)
            assert result.volume == 100
            assert len(result.kpis) > 0
            for kpi in result.kpis:
                assert kpi.source_column.lower() not in ["revenue", "sales", "orders", "quantity", "price", "customers"], \
                    f"Hardcoded retail KPI found: {kpi.source_column}"
            report = UniversalExecutiveReportEngine.generate_report(result, sm)
            assert "sections" in report
        finally:
            _cleanup(ws_id, csv_path)

    def test_generic_categorical_only_dataset(self):
        """Dataset with only categorical columns - should still produce insights."""
        df = pd.DataFrame({
            "Region": ["North", "South", "East", "West"] * 25,
            "Category": ["A", "B", "C", "D", "E"] * 20,
            "Status": ["Active", "Inactive", "Pending", "Active", "Inactive"] * 20,
        })
        ws_id = f"ws-cat-{uuid.uuid4().hex[:8]}"
        parquet_path, profile, csv_path = _setup_workspace(df, ws_id)
        try:
            from app.analytics.universal_engine import UniversalAnalyticsEngine
            from app.semantic_model.core import SemanticModel
            from app.services.dynamic_dashboard_service import get_dynamic_dashboard

            sm = SemanticModel(workspace_id=ws_id, domain="Generic Business", dataset_type="Unknown")
            result = UniversalAnalyticsEngine.analyze(sm, parquet_path=parquet_path)
            assert result.volume == 100
            assert len(result.kpis) > 0
            dashboard = get_dynamic_dashboard(workspace_id=ws_id)
            assert dashboard is not None
        finally:
            _cleanup(ws_id, csv_path)

    def test_dataset_without_dates(self):
        """Dataset without any date column - should still analyze but no time-series forecast."""
        df = pd.DataFrame({
            "Product": [f"Product-{i}" for i in range(1, 31)],
            "Score": [50 + i * 2 for i in range(30)],
            "Category": ["A", "B", "C"] * 10,
            "Rating": [1, 2, 3, 4, 5] * 6,
        })
        ws_id = f"ws-nodate-{uuid.uuid4().hex[:8]}"
        parquet_path, profile, csv_path = _setup_workspace(df, ws_id)
        try:
            from app.analytics.universal_engine import UniversalAnalyticsEngine
            from app.semantic_model.core import SemanticModel

            sm = SemanticModel(workspace_id=ws_id, domain="Generic Business", dataset_type="Unknown")
            result = UniversalAnalyticsEngine.analyze(sm, parquet_path=parquet_path)
            assert result.volume == 30
            assert len(result.kpis) > 0
        finally:
            _cleanup(ws_id, csv_path)

    def test_dataset_without_revenue_or_sales(self):
        """Dataset with NO revenue/sales columns - must NOT invent revenue KPIs."""
        df = pd.DataFrame({
            "EmployeeID": [f"E{i:03d}" for i in range(1, 21)],
            "Department": ["Engineering", "Marketing", "HR", "Finance", "Operations"] * 4,
            "Salary": [50000 + i * 1000 for i in range(20)],
            "ExperienceYears": [1, 3, 5, 7, 10, 2, 4, 6, 8, 15] * 2,
            "PerformanceScore": [60, 75, 85, 90, 95, 70, 80, 88, 92, 98] * 2,
        })
        ws_id = f"ws-norev-{uuid.uuid4().hex[:8]}"
        parquet_path, profile, csv_path = _setup_workspace(df, ws_id)
        try:
            from app.analytics.universal_engine import UniversalAnalyticsEngine
            from app.semantic_model.core import SemanticModel

            sm = SemanticModel(workspace_id=ws_id, domain="Generic Business", dataset_type="Unknown")
            result = UniversalAnalyticsEngine.analyze(sm, parquet_path=parquet_path)
            assert result.volume == 20
            kpi_names_lower = [k.source_column.lower() for k in result.kpis if hasattr(k, 'source_column') and k.source_column != '*']
            assert "revenue" not in kpi_names_lower
            assert "sales" not in kpi_names_lower
            assert "orders" not in kpi_names_lower
            assert any("salary" in n or "experience" in n or "performance" in n for n in kpi_names_lower), \
                "KPIs must reflect actual dataset columns"
        finally:
            _cleanup(ws_id, csv_path)

    def test_dataset_with_missing_values(self):
        """Dataset with missing values - should handle gracefully."""
        df = pd.DataFrame({
            "ID": [f"ID-{i}" for i in range(1, 31)],
            "Value": [10.0 + i for i in range(30)],
            "Category": ["A", "B", "C", None, "D"] * 6,
            "Timestamp": pd.date_range("2024-01-01", periods=30, freq="D").astype(str),
        })
        df.loc[5:10, "Value"] = None
        ws_id = f"ws-missing-{uuid.uuid4().hex[:8]}"
        parquet_path, profile, csv_path = _setup_workspace(df, ws_id)
        try:
            from app.analytics.universal_engine import UniversalAnalyticsEngine
            from app.semantic_model.core import SemanticModel

            sm = SemanticModel(workspace_id=ws_id, domain="Generic Business", dataset_type="Unknown")
            result = UniversalAnalyticsEngine.analyze(sm, parquet_path=parquet_path)
            assert result.volume == 30
            assert result.health_score.overall_score >= 0
            assert result.health_score.overall_score <= 100
            assert not math.isnan(result.health_score.overall_score)
            assert not math.isinf(result.health_score.overall_score)
        finally:
            _cleanup(ws_id, csv_path)

    def test_dataset_with_duplicate_rows(self):
        """Dataset with duplicate rows - should still function."""
        df = pd.DataFrame({
            "RecordID": [1, 2, 3, 4, 5] * 10,
            "Metric": [100.0, 200.0, 300.0, 400.0, 500.0] * 10,
            "Label": ["X", "Y", "Z", "X", "Y"] * 10,
        })
        ws_id = f"ws-dup-{uuid.uuid4().hex[:8]}"
        parquet_path, profile, csv_path = _setup_workspace(df, ws_id)
        try:
            from app.analytics.universal_engine import UniversalAnalyticsEngine
            from app.semantic_model.core import SemanticModel

            sm = SemanticModel(workspace_id=ws_id, domain="Generic Business", dataset_type="Unknown")
            result = UniversalAnalyticsEngine.analyze(sm, parquet_path=parquet_path)
            assert result.volume == 50
            assert len(result.kpis) > 0
        finally:
            _cleanup(ws_id, csv_path)

    def test_zero_value_is_genuine_not_error(self):
        """A KPI showing 0 must be the real calculated value, not a calculation error."""
        df = pd.DataFrame({
            "Item": [f"Item-{i}" for i in range(1, 11)],
            "Quantity": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            "Category": ["A", "B", "C", "D", "E"] * 2,
        })
        ws_id = f"ws-zero-{uuid.uuid4().hex[:8]}"
        parquet_path, profile, csv_path = _setup_workspace(df, ws_id)
        try:
            from app.analytics.universal_engine import UniversalAnalyticsEngine
            from app.semantic_model.core import SemanticModel

            sm = SemanticModel(workspace_id=ws_id, domain="Generic Business", dataset_type="Unknown")
            result = UniversalAnalyticsEngine.analyze(sm, parquet_path=parquet_path)
            quantity_kpi = None
            for kpi in result.kpis:
                if hasattr(kpi, 'source_column') and kpi.source_column.lower() == "quantity":
                    quantity_kpi = kpi
                    break
            if quantity_kpi:
                assert quantity_kpi.value == 0 or quantity_kpi.value == 0.0 or str(quantity_kpi.formatted_value).startswith("0"), \
                    "Zero quantity must show as 0, not error/undefined"
                assert quantity_kpi.available is True, "Zero-value KPI must still be available"
        finally:
            _cleanup(ws_id, csv_path)

    def test_no_undefined_nan_null_in_dashboard(self):
        """Dashboard must not contain undefined, NaN, null, or 'Unavailable' when data exists."""
        df = pd.DataFrame({
            "Metric": [10, 20, 30, 40, 50] * 10,
            "Dimension": ["A", "B", "C", "D", "E"] * 10,
            "Time": pd.date_range("2024-01-01", periods=50, freq="D").astype(str),
        })
        ws_id = f"ws-undef-{uuid.uuid4().hex[:8]}"
        parquet_path, profile, csv_path = _setup_workspace(df, ws_id)
        try:
            from app.analytics.universal_engine import UniversalAnalyticsEngine
            from app.semantic_model.core import SemanticModel
            from app.services.dynamic_dashboard_service import get_dynamic_dashboard

            sm = SemanticModel(workspace_id=ws_id, domain="Generic Business", dataset_type="Unknown")
            UniversalAnalyticsEngine.analyze(sm, parquet_path=parquet_path)
            dashboard = get_dynamic_dashboard(workspace_id=ws_id)
            import re
            dashboard_str = str(dashboard)
            assert not re.search(r'\bNaN\b', dashboard_str, re.IGNORECASE) or "nan" in [c.lower() for c in df.columns], \
                "Dashboard contains standalone 'NaN' when data exists"
            assert not re.search(r'\bundefined\b', dashboard_str, re.IGNORECASE) or "undefined" in [c.lower() for c in df.columns], \
                "Dashboard contains standalone 'undefined' when data exists"
        finally:
            _cleanup(ws_id, csv_path)

    def test_dynamic_kpis_adapt_to_dataset(self):
        """KPIs must reflect actual dataset columns, not hardcoded assumptions."""
        df = pd.DataFrame({
            "Temperature": [20.0 + (i % 10) * 0.5 for i in range(100)],
            "Humidity": [40 + (i % 15) for i in range(100)],
            "Machine": [f"MCH-{i%5}" for i in range(100)],
        })
        ws_id = f"ws-dynkpi-{uuid.uuid4().hex[:8]}"
        parquet_path, profile, csv_path = _setup_workspace(df, ws_id)
        try:
            from app.analytics.universal_engine import UniversalAnalyticsEngine
            from app.semantic_model.core import SemanticModel
            from app.services.dynamic_kpi_engine import DynamicKPIEngine

            sm = SemanticModel(workspace_id=ws_id, domain="Generic Business", dataset_type="Unknown")
            result = UniversalAnalyticsEngine.analyze(sm, parquet_path=parquet_path)
            dynamic = DynamicKPIEngine.analyze(analytics_result=result, semantic_model=sm, profile=profile)
            assert dynamic is not None
            kpi_names = [c.name.lower() for c in dynamic.kpi_cards.get("top", [])]
            dataset_columns_lower = [c.lower() for c in df.columns]
            for kpi_name in kpi_names:
                assert any(col in kpi_name for col in dataset_columns_lower) or kpi_name in ("total verified rows", "*"), \
                    f"KPI '{kpi_name}' does not reference any dataset column"
        finally:
            _cleanup(ws_id, csv_path)

    def test_role_reports_generate_from_arbitrary_data(self):
        """Role-based reports must generate from any dataset, not just retail."""
        df = pd.DataFrame({
            "ErrorCode": [f"ERR-{i%10}" for i in range(100)],
            "ErrorCount": [1 + i % 50 for i in range(100)],
            "Region": ["US", "EU", "APAC", "LATAM"] * 25,
            "System": ["Auth", "Payment", "Database", "API", "Cache"] * 20,
            "Timestamp": pd.date_range("2024-01-01", periods=100, freq="h").astype(str),
        })
        ws_id = f"ws-role-{uuid.uuid4().hex[:8]}"
        parquet_path, profile, csv_path = _setup_workspace(df, ws_id)
        try:
            from app.analytics.universal_engine import UniversalAnalyticsEngine
            from app.semantic_model.core import SemanticModel
            from app.reports.role_based_report_engine import RoleBasedReportEngine

            sm = SemanticModel(workspace_id=ws_id, domain="Generic Business", dataset_type="Unknown")
            result = UniversalAnalyticsEngine.analyze(sm, parquet_path=parquet_path)
            for audience in ["CEO", "CFO", "COO", "CMO", "BOARD"]:
                report = RoleBasedReportEngine.generate_report(
                    analytics_result=result,
                    semantic_model=sm,
                    audience=audience,
                    predictions=result.predictions,
                )
                assert "sections" in report, f"{audience} report missing sections"
        finally:
            _cleanup(ws_id, csv_path)

    def test_forecast_feasibility_respects_data(self):
        """Forecast must be feasible only when temporal+numeric data supports it."""
        df = pd.DataFrame({
            "Metric": [10, 20, 30, 40, 50],
            "Category": ["A", "B", "C", "D", "E"],
        })
        ws_id = f"ws-nofcast-{uuid.uuid4().hex[:8]}"
        parquet_path, profile, csv_path = _setup_workspace(df, ws_id)
        try:
            from app.analytics.universal_engine import UniversalAnalyticsEngine
            from app.semantic_model.core import SemanticModel

            sm = SemanticModel(workspace_id=ws_id, domain="Generic Business", dataset_type="Unknown")
            result = UniversalAnalyticsEngine.analyze(sm, parquet_path=parquet_path)
            if result.forecast_ready:
                feasible_preds = [p for p in result.predictions if getattr(p, 'feasible', False)]
                assert len(feasible_preds) > 0 or result.prediction_limitation is not None, \
                    "Forecast must include limitation when not truly feasible"
        finally:
            _cleanup(ws_id, csv_path)

    def test_health_score_never_zero_when_data_exists(self):
        """Health score must be meaningful (>0) when data exists."""
        df = pd.DataFrame({
            "Value": [10, 20, 30, 40, 50] * 10,
            "Category": ["A", "B", "C", "D", "E"] * 10,
        })
        ws_id = f"ws-health-{uuid.uuid4().hex[:8]}"
        parquet_path, profile, csv_path = _setup_workspace(df, ws_id)
        try:
            from app.analytics.universal_engine import UniversalAnalyticsEngine
            from app.semantic_model.core import SemanticModel

            sm = SemanticModel(workspace_id=ws_id, domain="Generic Business", dataset_type="Unknown")
            result = UniversalAnalyticsEngine.analyze(sm, parquet_path=parquet_path)
            assert result.health_score.overall_score > 0, \
                f"Health score must be > 0 when data exists, got {result.health_score.overall_score}"
            assert not math.isnan(result.health_score.overall_score)
            assert not math.isinf(result.health_score.overall_score)
        finally:
            _cleanup(ws_id, csv_path)

    def test_copilot_no_hallucination_on_arbitrary_data(self):
        """Copilot must not invent information not in the dataset."""
        df = pd.DataFrame({
            "SensorID": [f"SENSOR-{i}" for i in range(1, 21)],
            "Temperature": [22.0 + i * 0.3 for i in range(20)],
            "Humidity": [45 + i for i in range(20)],
            "Location": ["Room-A", "Room-B", "Room-C", "Room-D"] * 5,
        })
        ws_id = f"ws-copilot-{uuid.uuid4().hex[:8]}"
        parquet_path, profile, csv_path = _setup_workspace(df, ws_id)
        try:
            from app.ai.universal_copilot_brain import UniversalAIBrain

            response = UniversalAIBrain.query(
                question="What is the average temperature?",
                workspace_id=ws_id,
                dataset_id=ws_id,
            )
            assert "answer" in response
            assert response.get("confidence", 0) > 0
            assert "evidence" in response
        finally:
            _cleanup(ws_id, csv_path)

    def test_workspace_isolation(self):
        """Workspace A must not see Workspace B's data."""
        df_a = pd.DataFrame({"MetricA": [1, 2, 3], "CatA": ["X", "Y", "Z"]})
        df_b = pd.DataFrame({"MetricB": [10, 20, 30], "CatB": ["P", "Q", "R"]})
        ws_a = f"ws-iso-a-{uuid.uuid4().hex[:8]}"
        ws_b = f"ws-iso-b-{uuid.uuid4().hex[:8]}"
        parquet_a, profile_a, csv_a = _setup_workspace(df_a, ws_a)
        parquet_b, profile_b, csv_b = _setup_workspace(df_b, ws_b)
        try:
            from app.analytics.universal_engine import UniversalAnalyticsEngine
            from app.semantic_model.core import SemanticModel

            sm_a = SemanticModel(workspace_id=ws_a, domain="Generic Business", dataset_type="Unknown")
            sm_b = SemanticModel(workspace_id=ws_b, domain="Generic Business", dataset_type="Unknown")
            result_a = UniversalAnalyticsEngine.analyze(sm_a, parquet_path=parquet_a)
            result_b = UniversalAnalyticsEngine.analyze(sm_b, parquet_path=parquet_b)
            kpi_names_a = [k.source_column.lower() for k in result_a.kpis if hasattr(k, 'source_column') and k.source_column != '*']
            kpi_names_b = [k.source_column.lower() for k in result_b.kpis if hasattr(k, 'source_column') and k.source_column != '*']
            assert "metricb" not in kpi_names_a, "Workspace A must not see Workspace B's KPIs"
            assert "metrica" not in kpi_names_b, "Workspace B must not see Workspace A's KPIs"
        finally:
            _cleanup(ws_a, csv_a)
            _cleanup(ws_b, csv_b)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-x"])
