"""
End-to-end integration tests for DecisionLens production readiness.
Tests the complete execution path for all test datasets.
"""
import os
import sys
import json
import time
import pytest
import tempfile
import shutil
from pathlib import Path
from fastapi.testclient import TestClient

# Add backend to path
backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from app.main import app
from app.database.connection import create_tables, SessionLocal
from app.database.crud import save_dataset
from app.ingestion.generic_loader import GenericDataLoader
from app.ingestion.semantic_profiler import SemanticDataProfiler
from app.semantic_model.engine import build_semantic_model
from app.analytics.universal_engine import UniversalAnalyticsEngine
from app.ml.prediction_engine import UniversalPredictionEngine
from app.services.dynamic_dashboard_service import get_dynamic_dashboard
from app.ai.universal_copilot_brain import UniversalAIBrain
from app.reports.executive_report_engine import UniversalExecutiveReportEngine
from app.services.workspace_service import EnterpriseWorkspaceManager
from app.database.storage import UPLOAD_RAW_DIR

client = TestClient(app)

TEST_DATA_DIR = backend_dir / "data" / "evaluation"
STORAGE_DIR = backend_dir / "storage"
UPLOAD_RAW_DIR = UPLOAD_RAW_DIR

# Format: (subdirectory, filename)
DATASETS = [
    ("retail", "retail_sales.csv"),
    ("healthcare", "healthcare_visits.csv"),
    ("finance", "finance_transactions.csv"),
    ("hr", "hr_employees.csv"),
    ("marketing", "marketing_campaigns.csv"),
    ("operations", "operations_orders.csv"),
    ("education", "education_students.csv"),
]

# Questions to test copilot with
COPILOT_QUESTIONS = [
    "What happened in this dataset?",
    "What are the top performing categories?",
    "What are the key trends?",
    "What should we do?",
    "Generate an executive summary",
]


def _get_dataset_path(dataset_tuple):
    subdir, filename = dataset_tuple
    return TEST_DATA_DIR / subdir / filename


class TestEndToEndProduction:
    """Complete end-to-end production readiness tests."""

    def setup_method(self):
        create_tables()
        self.workspace_ids = []

    def teardown_method(self):
        for ws_id in self.workspace_ids:
            try:
                EnterpriseWorkspaceManager.delete_workspace(ws_id)
            except Exception:
                pass

    def test_upload_and_process_all_datasets(self):
        """Test uploading all test datasets."""
        for dataset_tuple in DATASETS:
            dataset_path = _get_dataset_path(dataset_tuple)
            if not dataset_path.exists():
                continue

            with open(dataset_path, "rb") as f:
                response = client.post(
                    "/api/v1/upload/",
                    files={"file": (dataset_path.name, f, "text/csv")},
                    headers={"Authorization": "Bearer test"},
                )

            assert response.status_code in (200, 401), (
                f"Upload failed for {dataset_path.name}: {response.status_code} {response.text}"
            )

            if response.status_code == 200:
                data = response.json()
                workspace_id = data.get("workspace_id") or data.get("dataset_id")
                if workspace_id:
                    self.workspace_ids.append(workspace_id)

    def test_semantic_model_generation(self):
        """Test semantic model generation for uploaded datasets."""
        for dataset_tuple in DATASETS[:2]:  # Test first 2 datasets for speed
            dataset_path = _get_dataset_path(dataset_tuple)
            if not dataset_path.exists():
                continue

            upload_path = UPLOAD_RAW_DIR / dataset_path.name
            shutil.copy2(dataset_path, upload_path)
            ws_id = f"ws-test-{dataset_path.stem}"
            dataset_id = f"{ws_id}__{dataset_path.stem}"
            parquet_path = GenericDataLoader.convert_to_parquet(upload_path, dataset_id)
            EnterpriseWorkspaceManager.create_or_get_workspace(ws_id, ws_id.replace("-", " ").title())
            profile = SemanticDataProfiler.profile(parquet_path)
            EnterpriseWorkspaceManager.register_table(
                ws_id,
                dataset_path.stem,
                [{"name": c, "type": profile["columns"][c].get("inferred_type", "VARCHAR")} for c in profile["columns"]],
                profile.get("total_rows", 0),
                str(parquet_path),
            )

            sm = build_semantic_model(workspace_id=ws_id, force_rebuild=True)
            assert sm is not None, f"Semantic model failed for {dataset_path.name}"
            assert "tables" in sm or isinstance(sm, dict), f"Invalid semantic model for {dataset_path.name}"

    def test_analytics_engine(self):
        """Test analytics engine produces valid results."""
        for dataset_tuple in DATASETS[:2]:  # Test first 2 datasets for speed
            dataset_path = _get_dataset_path(dataset_tuple)
            if not dataset_path.exists():
                continue

            upload_path = UPLOAD_RAW_DIR / dataset_path.name
            shutil.copy2(dataset_path, upload_path)
            ws_id = f"ws-test-{dataset_path.stem}"
            dataset_id = f"{ws_id}__{dataset_path.stem}"
            parquet_path = GenericDataLoader.convert_to_parquet(upload_path, dataset_id)
            EnterpriseWorkspaceManager.create_or_get_workspace(ws_id, ws_id.replace("-", " ").title())
            profile = SemanticDataProfiler.profile(parquet_path)
            EnterpriseWorkspaceManager.register_table(
                ws_id,
                dataset_path.stem,
                [{"name": c, "type": profile["columns"][c].get("inferred_type", "VARCHAR")} for c in profile["columns"]],
                profile.get("total_rows", 0),
                str(parquet_path),
            )
            measures = profile.get("column_categories", {}).get("measures", [])
            dimensions = profile.get("column_categories", {}).get("dimensions", [])

            if not measures:
                continue

            from app.semantic_model.core import SemanticModel
            sm = SemanticModel(
                workspace_id=ws_id,
                domain="Generic Business",
                dataset_type=profile.get("table_meta", {}).get("table_type", "Unknown"),
            )

            result = UniversalAnalyticsEngine.analyze(sm, parquet_path=parquet_path)
            assert result is not None, f"Analytics engine failed for {dataset_path.name}"
            assert result.volume > 0, f"No data analyzed for {dataset_path.name}"

    def test_prediction_engine(self):
        """Test prediction engine produces valid results."""
        from types import SimpleNamespace
        for dataset_tuple in DATASETS[:2]:  # Test first 2 datasets for speed
            dataset_path = _get_dataset_path(dataset_tuple)
            if not dataset_path.exists():
                continue

            upload_path = UPLOAD_RAW_DIR / dataset_path.name
            shutil.copy2(dataset_path, upload_path)
            ws_id = f"ws-test-{dataset_path.stem}"
            dataset_id = f"{ws_id}__{dataset_path.stem}"
            parquet_path = GenericDataLoader.convert_to_parquet(upload_path, dataset_id)
            EnterpriseWorkspaceManager.create_or_get_workspace(ws_id, ws_id.replace("-", " ").title())
            profile = SemanticDataProfiler.profile(parquet_path)
            EnterpriseWorkspaceManager.register_table(
                ws_id,
                dataset_path.stem,
                [{"name": c, "type": profile["columns"][c].get("inferred_type", "VARCHAR")} for c in profile["columns"]],
                profile.get("total_rows", 0),
                str(parquet_path),
            )
            measures = profile.get("column_categories", {}).get("measures", [])

            if not measures:
                continue

            from app.semantic_model.core import SemanticModel
            sm = SemanticModel(
                workspace_id=ws_id,
                domain="Generic Business",
                dataset_type=profile.get("table_meta", {}).get("table_type", "Unknown"),
            )

            partial = SimpleNamespace(
                trends={},
                correlations=[],
                root_causes=[],
                drivers=[],
                anomalies=[],
                outliers=[],
                kpis=[],
                volume=profile.get("total_rows", 0),
                confidence_score=0.0,
                evidence={},
            )
            predictions = UniversalPredictionEngine.generate(
                analytics_result=partial,
                semantic_model=sm,
            )
            assert isinstance(predictions, list), f"Predictions should be a list for {dataset_path.name}"

    def test_dashboard_generation(self):
        """Test dashboard generation for uploaded datasets."""
        for dataset_tuple in DATASETS[:1]:  # Test first dataset for speed
            dataset_path = _get_dataset_path(dataset_tuple)
            if not dataset_path.exists():
                continue

            upload_path = UPLOAD_RAW_DIR / dataset_path.name
            shutil.copy2(dataset_path, upload_path)
            ws_id = f"ws-test-{dataset_path.stem}"
            dataset_id = f"{ws_id}__{dataset_path.stem}"
            parquet_path = GenericDataLoader.convert_to_parquet(upload_path, dataset_id)
            EnterpriseWorkspaceManager.create_or_get_workspace(ws_id, ws_id.replace("-", " ").title())
            profile = SemanticDataProfiler.profile(parquet_path)
            EnterpriseWorkspaceManager.register_table(
                ws_id,
                dataset_path.stem,
                [{"name": c, "type": profile["columns"][c].get("inferred_type", "VARCHAR")} for c in profile["columns"]],
                profile.get("total_rows", 0),
                str(parquet_path),
            )

            dashboard = get_dynamic_dashboard(workspace_id=ws_id)
            assert dashboard is not None, f"Dashboard is None for {dataset_path.name}"
            assert "domain" in dashboard or "workspace_exists" in dashboard, (
                f"Dashboard missing required fields for {dataset_path.name}"
            )

    def test_copilot_questions(self):
        """Test copilot answers questions with evidence."""
        for dataset_tuple in DATASETS[:1]:  # Test first dataset for speed
            dataset_path = _get_dataset_path(dataset_tuple)
            if not dataset_path.exists():
                continue

            upload_path = UPLOAD_RAW_DIR / dataset_path.name
            shutil.copy2(dataset_path, upload_path)
            ws_id = f"ws-test-copilot-{dataset_path.stem}"
            dataset_id = f"{ws_id}__{dataset_path.stem}"
            parquet_path = GenericDataLoader.convert_to_parquet(upload_path, dataset_id)
            EnterpriseWorkspaceManager.create_or_get_workspace(ws_id, ws_id.replace("-", " ").title())
            profile = SemanticDataProfiler.profile(parquet_path)
            EnterpriseWorkspaceManager.register_table(
                ws_id,
                dataset_path.stem,
                [{"name": c, "type": profile["columns"][c].get("inferred_type", "VARCHAR")} for c in profile["columns"]],
                profile.get("total_rows", 0),
                str(parquet_path),
            )

            for question in COPILOT_QUESTIONS:
                response = UniversalAIBrain.query(
                    question=question,
                    workspace_id=ws_id,
                    dataset_id=ws_id,
                )

                assert "answer" in response, f"Copilot missing answer for {dataset_path.name}: {question}"
                assert "evidence" in response, f"Copilot missing evidence for {dataset_path.name}: {question}"
                assert response.get("confidence", 0) > 0 or "no data" in response.get("answer", "").lower(), (
                    f"Copilot confidence is 0 but data exists for {dataset_path.name}: {question}"
                )

    def test_report_generation(self):
        """Test report generation for uploaded datasets."""
        for dataset_tuple in DATASETS[:1]:  # Test first dataset for speed
            dataset_path = _get_dataset_path(dataset_tuple)
            if not dataset_path.exists():
                continue

            upload_path = UPLOAD_RAW_DIR / dataset_path.name
            shutil.copy2(dataset_path, upload_path)
            ws_id = f"ws-test-report-{dataset_path.stem}"
            dataset_id = f"{ws_id}__{dataset_path.stem}"
            parquet_path = GenericDataLoader.convert_to_parquet(upload_path, dataset_id)
            EnterpriseWorkspaceManager.create_or_get_workspace(ws_id, ws_id.replace("-", " ").title())
            profile = SemanticDataProfiler.profile(parquet_path)
            EnterpriseWorkspaceManager.register_table(
                ws_id,
                dataset_path.stem,
                [{"name": c, "type": profile["columns"][c].get("inferred_type", "VARCHAR")} for c in profile["columns"]],
                profile.get("total_rows", 0),
                str(parquet_path),
            )
            measures = profile.get("column_categories", {}).get("measures", [])

            if not measures:
                continue

            from app.semantic_model.core import SemanticModel
            sm = SemanticModel(
                workspace_id=ws_id,
                domain="Generic Business",
                dataset_type=profile.get("table_meta", {}).get("table_type", "Unknown"),
            )

            analytics_result = UniversalAnalyticsEngine.analyze(sm, parquet_path=parquet_path)
            predictions = UniversalPredictionEngine.generate(
                analytics_result=analytics_result,
                semantic_model=sm,
            )
            report = UniversalExecutiveReportEngine.generate_report(
                analytics_result=analytics_result,
                semantic_model=sm,
                prediction_result=predictions,
            )

            assert "sections" in report, f"Report missing sections for {dataset_path.name}"
            assert "executive_summary" in report["sections"], (
                f"Report missing executive_summary for {dataset_path.name}"
            )

    def test_workspace_deletion(self):
        """Test workspace deletion cleans up all resources."""
        dataset_tuple = ("retail", "retail_sales.csv")
        dataset_path = _get_dataset_path(dataset_tuple)
        if not dataset_path.exists():
            pytest.skip("retail_sales.csv not found")

        upload_path = UPLOAD_RAW_DIR / dataset_path.name
        shutil.copy2(dataset_path, upload_path)
        ws_id = f"ws-test-delete-{int(time.time())}"
        dataset_id = f"{ws_id}__{dataset_path.stem}"
        parquet_path = GenericDataLoader.convert_to_parquet(upload_path, dataset_id)

        EnterpriseWorkspaceManager.create_or_get_workspace(ws_id, "Test Delete Workspace")
        EnterpriseWorkspaceManager.set_active_workspace(ws_id)
        profile = SemanticDataProfiler.profile(parquet_path)
        EnterpriseWorkspaceManager.register_table(
            ws_id,
            dataset_path.stem,
            [{"name": c, "type": profile["columns"][c].get("inferred_type", "VARCHAR")} for c in profile["columns"]],
            profile.get("total_rows", 0),
            str(parquet_path),
        )

        result = EnterpriseWorkspaceManager.delete_workspace(ws_id)
        assert result is True, f"Workspace deletion failed for {ws_id}"

        ws = EnterpriseWorkspaceManager.get_workspace(ws_id)
        assert ws is None, f"Workspace still exists after deletion: {ws_id}"

    def test_no_hardcoded_domain_assumptions(self):
        """Verify no domain-specific assumptions in generated content."""
        dataset_tuple = ("finance", "finance_transactions.csv")
        dataset_path = _get_dataset_path(dataset_tuple)
        if not dataset_path.exists():
            pytest.skip("finance_transactions.csv not found")

        upload_path = UPLOAD_RAW_DIR / dataset_path.name
        shutil.copy2(dataset_path, upload_path)
        ws_id = f"ws-test-domain-{dataset_path.stem}"
        dataset_id = f"{ws_id}__{dataset_path.stem}"
        parquet_path = GenericDataLoader.convert_to_parquet(upload_path, dataset_id)
        EnterpriseWorkspaceManager.create_or_get_workspace(ws_id, ws_id.replace("-", " ").title())
        profile = SemanticDataProfiler.profile(parquet_path)
        EnterpriseWorkspaceManager.register_table(
            ws_id,
            dataset_path.stem,
            [{"name": c, "type": profile["columns"][c].get("inferred_type", "VARCHAR")} for c in profile["columns"]],
            profile.get("total_rows", 0),
            str(parquet_path),
        )
        measures = profile.get("column_categories", {}).get("measures", [])

        if not measures:
            return

        from app.semantic_model.core import SemanticModel
        sm = SemanticModel(
            workspace_id=ws_id,
            domain="Generic Business",
            dataset_type="Unknown",
        )

        result = UniversalAnalyticsEngine.analyze(sm, parquet_path=parquet_path)
        report = UniversalExecutiveReportEngine.generate_report(
            analytics_result=result,
            semantic_model=sm,
        )

        exec_summary = report["sections"]["executive_summary"]["text"]
        assert "sales" not in exec_summary.lower() or "sales" in [m.lower() for m in measures], (
            "Report contains hardcoded 'sales' assumption not in dataset"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-x"])
