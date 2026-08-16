import pytest
import tempfile
import uuid
import pandas as pd
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.ingestion.generic_loader import GenericDataLoader
from app.ingestion.semantic_profiler import SemanticDataProfiler
from app.services.workspace_service import EnterpriseWorkspaceManager
from app.analytics.universal_engine import UniversalAnalyticsEngine
from app.semantic_model.core import SemanticModel
from app.ml.prediction_engine import UniversalPredictionEngine
from app.reports.executive_report_engine import UniversalExecutiveReportEngine
from app.ai.universal_copilot_brain import UniversalAIBrain
from app.ai.enterprise_decision_engine import EnterpriseDecisionEngine
from app.schemas.analytics import AnalyticsResult, KPIMetric, RiskItem, OpportunityItem, Recommendation, HealthScore, BusinessAnomaly, RootCause, DistributionItem, TrendPoint, Prediction, SegmentComparison

client = TestClient(app)


def _create_workspace(df: pd.DataFrame, ws_id: str, domain: str = "Retail & E-Commerce"):
    csv_path = Path(tempfile.mktemp(suffix=".csv"))
    df.to_csv(csv_path, index=False)
    dataset_id = f"{ws_id}__data"
    parquet_path = GenericDataLoader.convert_to_parquet(csv_path, dataset_id)
    EnterpriseWorkspaceManager.create_or_get_workspace(ws_id, f"Test {ws_id}")
    EnterpriseWorkspaceManager.set_active_workspace(ws_id)
    profile = SemanticDataProfiler.profile(parquet_path)
    EnterpriseWorkspaceManager.register_table(
        ws_id, "test_table",
        [{"name": col, "type": "VARCHAR" if df[col].dtype == "object" else "FLOAT"} for col in df.columns],
        len(df), str(parquet_path)
    )
    sm = SemanticModel(workspace_id=ws_id, domain=domain, dataset_type=domain)
    return parquet_path, sm, csv_path, profile


# ==========================================
# A. Evidence Contract
# ==========================================

class TestEvidenceContract:
    def test_list_of_dicts_passthrough(self):
        rows = [{"metric_value": 100, "category": "A"}]
        result = EnterpriseDecisionEngine._normalize_evidence_rows(rows)
        assert result == [{"metric_value": 100, "category": "A"}]

    def test_empty_list(self):
        result = EnterpriseDecisionEngine._normalize_evidence_rows([])
        assert result == []

    def test_none_returns_empty(self):
        result = EnterpriseDecisionEngine._normalize_evidence_rows(None)
        assert result == []

    def test_tuple_converted_to_dict(self):
        rows = [("A", 100)]
        result = EnterpriseDecisionEngine._normalize_evidence_rows(rows)
        assert result == [{"col_0": "A", "col_1": 100}]

    def test_malformed_string_dropped(self):
        rows = ["bad_row", {"valid": True}]
        result = EnterpriseDecisionEngine._normalize_evidence_rows(rows)
        assert result == [{"valid": True}]

    def test_non_list_returns_empty(self):
        result = EnterpriseDecisionEngine._normalize_evidence_rows("not_a_list")
        assert result == []

    def test_universal_brain_normalize(self):
        rows = [{"metric_value": 100}]
        result = UniversalAIBrain._normalize_evidence_rows(rows)
        assert result == [{"metric_value": 100}]


# ==========================================
# B. Executive Report Contract
# ==========================================

class TestExecutiveReportContract:
    def test_dict_kpis_normalized_to_kpi_metric(self):
        df = pd.DataFrame({
            "sales": [100, 200, 300],
            "category": ["A", "B", "C"],
        })
        ws_id = f"ws-rpt-{uuid.uuid4().hex[:6]}"
        p, sm, c, _ = _create_workspace(df, ws_id, "Retail & E-Commerce")
        try:
            analytics = UniversalAnalyticsEngine.analyze(sm, parquet_path=p)
            analytics_dict = analytics.to_dict()
            report = UniversalExecutiveReportEngine.generate_report(
                analytics_result=analytics_dict,
                semantic_model=sm,
            )
            assert "sections" in report
            assert "error" not in report["sections"].get("executive_summary", {}), "executive_summary must not error"
            assert "error" not in report["sections"].get("business_health", {}), "business_health must not error"
            assert "error" not in report["sections"].get("primary_metrics", {}), "primary_metrics must not error"
            assert "error" not in report["sections"].get("dimension_analysis", {}), "dimension_analysis must not error"
            assert "error" not in report["sections"].get("dimension_distributions", {}), "dimension_distributions must not error"
        finally:
            c.unlink(missing_ok=True)

    def test_dataclass_input_unchanged(self):
        df = pd.DataFrame({
            "sales": [100, 200, 300],
            "category": ["A", "B", "C"],
        })
        ws_id = f"ws-rpt2-{uuid.uuid4().hex[:6]}"
        p, sm, c, _ = _create_workspace(df, ws_id, "Retail & E-Commerce")
        try:
            analytics = UniversalAnalyticsEngine.analyze(sm, parquet_path=p)
            report = UniversalExecutiveReportEngine.generate_report(
                analytics_result=analytics,
                semantic_model=sm,
            )
            assert "sections" in report
            assert report["generation_status"] == "complete"
        finally:
            c.unlink(missing_ok=True)


# ==========================================
# C. Prediction Target Selection
# ==========================================

class TestPredictionTargetSelection:
    def test_single_numeric_column_used(self):
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=30),
            "value": range(30),
        })
        ws_id = f"ws-pred1-{uuid.uuid4().hex[:6]}"
        p, sm, c, _ = _create_workspace(df, ws_id, "Generic Business")
        try:
            analytics = UniversalAnalyticsEngine.analyze(sm, parquet_path=p)
            predictions = UniversalPredictionEngine.generate(analytics, sm)
            assert len(predictions) > 0, "Should generate predictions with single numeric column"
            feasible = [p for p in predictions if getattr(p, "feasible", False)]
            assert len(feasible) > 0, "At least one prediction should be feasible"
        finally:
            c.unlink(missing_ok=True)

    def test_quantity_price_derives_revenue(self):
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=30),
            "quantity": [10 + i for i in range(30)],
            "price": [5.0 + i * 0.1 for i in range(30)],
        })
        ws_id = f"ws-pred2-{uuid.uuid4().hex[:6]}"
        p, sm, c, _ = _create_workspace(df, ws_id, "Retail & E-Commerce")
        try:
            analytics = UniversalAnalyticsEngine.analyze(sm, parquet_path=p)
            predictions = UniversalPredictionEngine.generate(analytics, sm)
            feasible = [p for p in predictions if getattr(p, "feasible", False)]
            assert len(feasible) > 0, "Should derive revenue from quantity * price"
        finally:
            c.unlink(missing_ok=True)

    def test_salary_experience_score(self):
        df = pd.DataFrame({
            "employee_id": range(1, 51),
            "experience_years": [1 + i * 0.5 for i in range(50)],
            "performance_score": [60 + i for i in range(50)],
            "salary": [30000 + i * 500 for i in range(50)],
        })
        ws_id = f"ws-pred3-{uuid.uuid4().hex[:6]}"
        p, sm, c, _ = _create_workspace(df, ws_id, "Human Resources")
        try:
            analytics = UniversalAnalyticsEngine.analyze(sm, parquet_path=p)
            predictions = UniversalPredictionEngine.generate(analytics, sm)
            feasible = [p for p in predictions if getattr(p, "feasible", False)]
            assert len(feasible) > 0, "Should predict with salary/experience/score"
        finally:
            c.unlink(missing_ok=True)

    def test_marks_attendance(self):
        df = pd.DataFrame({
            "student_id": range(1, 51),
            "attendance_pct": [70 + i * 0.5 for i in range(50)],
            "marks": [50 + i for i in range(50)],
        })
        ws_id = f"ws-pred4-{uuid.uuid4().hex[:6]}"
        p, sm, c, _ = _create_workspace(df, ws_id, "Education")
        try:
            analytics = UniversalAnalyticsEngine.analyze(sm, parquet_path=p)
            predictions = UniversalPredictionEngine.generate(analytics, sm)
            feasible = [p for p in predictions if getattr(p, "feasible", False)]
            assert len(feasible) > 0, "Should predict with marks/attendance"
        finally:
            c.unlink(missing_ok=True)

    def test_revenue_cost_profit(self):
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=30),
            "revenue": [1000 + i * 10 for i in range(30)],
            "cost": [600 + i * 5 for i in range(30)],
        })
        ws_id = f"ws-pred5-{uuid.uuid4().hex[:6]}"
        p, sm, c, _ = _create_workspace(df, ws_id, "Finance")
        try:
            analytics = UniversalAnalyticsEngine.analyze(sm, parquet_path=p)
            predictions = UniversalPredictionEngine.generate(analytics, sm)
            feasible = [p for p in predictions if getattr(p, "feasible", False)]
            assert len(feasible) > 0, "Should predict with revenue/cost"
        finally:
            c.unlink(missing_ok=True)


# ==========================================
# D. Copilot End-to-End
# ==========================================

class TestCopilotE2E:
    def test_overall_performance(self):
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=30),
            "sales": [100 + i * 5 for i in range(30)],
            "category": ["A", "B", "C"] * 10,
        })
        ws_id = f"ws-cop1-{uuid.uuid4().hex[:6]}"
        p, sm, c, _ = _create_workspace(df, ws_id, "Retail & E-Commerce")
        try:
            response = UniversalAIBrain.query(
                question="What is the overall performance?",
                workspace_id=ws_id,
            )
            assert "answer" in response
            assert len(response["answer"]) > 0
            assert "evidence" in response
        finally:
            c.unlink(missing_ok=True)

    def test_kpi_question(self):
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=30),
            "sales": [100 + i * 5 for i in range(30)],
        })
        ws_id = f"ws-cop2-{uuid.uuid4().hex[:6]}"
        p, sm, c, _ = _create_workspace(df, ws_id, "Retail & E-Commerce")
        try:
            response = UniversalAIBrain.query(
                question="What are the most important KPIs?",
                workspace_id=ws_id,
            )
            assert "answer" in response
            assert len(response["answer"]) > 0
        finally:
            c.unlink(missing_ok=True)

    def test_comparison_question(self):
        df = pd.DataFrame({
            "category": ["A", "B", "C"] * 10,
            "sales": [100, 200, 300] * 10,
        })
        ws_id = f"ws-cop3-{uuid.uuid4().hex[:6]}"
        p, sm, c, _ = _create_workspace(df, ws_id, "Retail & E-Commerce")
        try:
            response = UniversalAIBrain.query(
                question="Which category is performing best?",
                workspace_id=ws_id,
            )
            assert "answer" in response
            assert len(response["answer"]) > 0
        finally:
            c.unlink(missing_ok=True)

    def test_root_cause_question(self):
        df = pd.DataFrame({
            "region": ["North", "South", "East", "West"] * 10,
            "sales": [100, 200, 150, 80] * 10,
        })
        ws_id = f"ws-cop4-{uuid.uuid4().hex[:6]}"
        p, sm, c, _ = _create_workspace(df, ws_id, "Retail & E-Commerce")
        try:
            response = UniversalAIBrain.query(
                question="Why is the North region performing best?",
                workspace_id=ws_id,
            )
            assert "answer" in response
            assert len(response["answer"]) > 0
        finally:
            c.unlink(missing_ok=True)

    def test_forecast_question(self):
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=30),
            "sales": [100 + i * 2 for i in range(30)],
        })
        ws_id = f"ws-cop5-{uuid.uuid4().hex[:6]}"
        p, sm, c, _ = _create_workspace(df, ws_id, "Retail & E-Commerce")
        try:
            response = UniversalAIBrain.query(
                question="Give me a forecast for next month.",
                workspace_id=ws_id,
            )
            assert "answer" in response
            assert len(response["answer"]) > 0
        finally:
            c.unlink(missing_ok=True)


# ==========================================
# E. Multi-Turn Conversation
# ==========================================

class TestMultiTurnConversation:
    def test_five_turn_conversation(self):
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=30),
            "sales": [100 + i * 5 for i in range(30)],
            "category": ["A", "B", "C"] * 10,
        })
        ws_id = f"ws-mt-{uuid.uuid4().hex[:6]}"
        session_id = f"session-{uuid.uuid4().hex[:6]}"
        p, sm, c, _ = _create_workspace(df, ws_id, "Retail & E-Commerce")
        try:
            history = []
            q1 = UniversalAIBrain.query(
                question="What is the overall performance?",
                workspace_id=ws_id,
                session_id=session_id,
                conversation_history=history,
            )
            history.append({"role": "user", "content": "What is the overall performance?"})
            history.append({"role": "assistant", "content": q1.get("answer", "")})
            assert "answer" in q1
            assert len(q1["answer"]) > 0

            q2 = UniversalAIBrain.query(
                question="Why?",
                workspace_id=ws_id,
                session_id=session_id,
                conversation_history=history,
            )
            history.append({"role": "user", "content": "Why?"})
            history.append({"role": "assistant", "content": q2.get("answer", "")})
            assert "answer" in q2
            assert len(q2["answer"]) > 0

            q3 = UniversalAIBrain.query(
                question="What should I do?",
                workspace_id=ws_id,
                session_id=session_id,
                conversation_history=history,
            )
            assert "answer" in q3
            assert len(q3["answer"]) > 0

            q4 = UniversalAIBrain.query(
                question="What happens if I increase the main driver by 10%?",
                workspace_id=ws_id,
                session_id=session_id,
                conversation_history=history,
            )
            assert "answer" in q4
            assert len(q4["answer"]) > 0

            q5 = UniversalAIBrain.query(
                question="Is that risky?",
                workspace_id=ws_id,
                session_id=session_id,
                conversation_history=history,
            )
            assert "answer" in q5
            assert len(q5["answer"]) > 0
        finally:
            c.unlink(missing_ok=True)
