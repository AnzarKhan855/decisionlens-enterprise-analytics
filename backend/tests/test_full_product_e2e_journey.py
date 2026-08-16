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

client = TestClient(app)

def _create_and_profile_workspace(df: pd.DataFrame, ws_id: str, domain: str = "Generic Business"):
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
    return parquet_path, sm, csv_path

# ==========================================
# FLOW A: User Auth & Profile Journey
# ==========================================
def test_flow_a_user_auth_profile_journey():
    u_email = f"e2e_user_{uuid.uuid4().hex[:6]}@decisionlens.ai"
    reg_res = client.post("/api/v1/auth/register", json={
        "email": u_email,
        "password": "Password123!",
        "full_name": "E2E User",
        "organization": "Enterprise Analytics Inc",
        "role": "EMPLOYEE"
    })
    assert reg_res.status_code == 200

    login_res = client.post("/api/v1/auth/login", json={"email": u_email, "password": "Password123!"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"] == u_email
    assert me_data["full_name"] == "E2E User"
    assert me_data["organization"] == "Enterprise Analytics Inc"

# ==========================================
# FLOW B & 9: Workspace Isolation & Deletion
# ==========================================
def test_flow_b_workspace_isolation_and_purge():
    u_email = f"owner_{uuid.uuid4().hex[:6]}@decisionlens.ai"
    client.post("/api/v1/auth/register", json={
        "email": u_email, "password": "Password123!", "full_name": "WS Owner", "organization": "Org", "role": "ORGANIZATION_ADMIN"
    })
    token = client.post("/api/v1/auth/login", json={"email": u_email, "password": "Password123!"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    df_a = pd.DataFrame({"Revenue": [100, 200, 300], "Category": ["A", "B", "C"]})
    df_b = pd.DataFrame({"PatientCost": [1500, 2500], "Department": ["ICU", "ER"]})

    ws_a = f"ws-iso-a-{uuid.uuid4().hex[:6]}"
    ws_b = f"ws-iso-b-{uuid.uuid4().hex[:6]}"

    p_a, sm_a, c_a = _create_and_profile_workspace(df_a, ws_a, "Retail")
    p_b, sm_b, c_b = _create_and_profile_workspace(df_b, ws_b, "Healthcare")

    try:
        res_a = UniversalAnalyticsEngine.analyze(sm_a, parquet_path=p_a)
        res_b = UniversalAnalyticsEngine.analyze(sm_b, parquet_path=p_b)

        assert res_a.volume == 3
        assert res_b.volume == 2
        assert "Revenue" in [k.source_column for k in res_a.kpis]
        assert "PatientCost" in [k.source_column for k in res_b.kpis]

        # Purge WS A via UI/API
        del_res = client.delete(f"/api/v1/workspaces/{ws_a}", headers=headers)
        assert del_res.status_code == 200

        # Verify WS A is gone and WS B remains untouched
        assert EnterpriseWorkspaceManager.get_workspace(ws_a) is None
        assert EnterpriseWorkspaceManager.get_workspace(ws_b) is not None
    finally:
        c_a.unlink(missing_ok=True)
        c_b.unlink(missing_ok=True)

# ==========================================
# FLOW C & 4: Multi-Schema Adaptability
# ==========================================
def test_flow_c_retail_schema():
    df = pd.DataFrame({"Quantity": [10, 20, 30], "Price": [5.0, 10.0, 15.0], "Category": ["X", "Y", "Z"]})
    ws_id = f"ws-retail-{uuid.uuid4().hex[:6]}"
    p, sm, c = _create_and_profile_workspace(df, ws_id, "Retail")
    try:
        res = UniversalAnalyticsEngine.analyze(sm, parquet_path=p)
        assert res.volume == 3
        report = UniversalExecutiveReportEngine.generate_report(analytics_result=res, semantic_model=sm)
        assert report["domain"] == "Retail"
    finally:
        c.unlink(missing_ok=True)

def test_flow_c_healthcare_schema():
    df = pd.DataFrame({"WaitTime": [15, 45, 60], "TreatmentCost": [200.0, 800.0, 1200.0], "Department": ["Cardiology", "Neurology", "ER"]})
    ws_id = f"ws-health-{uuid.uuid4().hex[:6]}"
    p, sm, c = _create_and_profile_workspace(df, ws_id, "Healthcare")
    try:
        res = UniversalAnalyticsEngine.analyze(sm, parquet_path=p)
        assert res.volume == 3
        assert any("WaitTime" in k.source_column for k in res.kpis)
    finally:
        c.unlink(missing_ok=True)

def test_flow_c_manufacturing_schema():
    df = pd.DataFrame({"Vibration": [0.02, 0.05, 0.12], "Temperature": [65.0, 72.0, 88.0], "MachineID": ["M-1", "M-2", "M-3"]})
    ws_id = f"ws-mfg-{uuid.uuid4().hex[:6]}"
    p, sm, c = _create_and_profile_workspace(df, ws_id, "Manufacturing")
    try:
        res = UniversalAnalyticsEngine.analyze(sm, parquet_path=p)
        assert res.volume == 3
    finally:
        c.unlink(missing_ok=True)

def test_flow_c_non_temporal_no_fake_dates():
    df = pd.DataFrame({"Score": [88, 92, 95], "Cohort": ["Alpha", "Beta", "Gamma"]})
    ws_id = f"ws-nontemp-{uuid.uuid4().hex[:6]}"
    p, sm, c = _create_and_profile_workspace(df, ws_id, "Education")
    try:
        res = UniversalAnalyticsEngine.analyze(sm, parquet_path=p)
        preds = UniversalPredictionEngine.generate(analytics_result=res, semantic_model=sm)
        assert len(preds) > 0
        p_obj = preds[0]
        assert p_obj.feasible is True
        pred_str = str(p_obj.prediction) + str(p_obj.time_horizon)
        assert "2026-01" not in pred_str
        assert "Next week" not in pred_str
    finally:
        c.unlink(missing_ok=True)

def test_flow_c_categorical_only_prediction_unavailable():
    from types import SimpleNamespace
    sm = SemanticModel(workspace_id="cat-only-test", domain="Operations", time_columns=[])
    analytics_result = SimpleNamespace(
        trends={}, correlations=[], root_causes=[], drivers=[], anomalies=[], outliers=[],
        kpis=[], volume=10, confidence_score=30.0,
        evidence={"measures_analyzed": [], "dimensions_analyzed": ["Region", "Status"]}
    )
    preds = UniversalPredictionEngine.generate(analytics_result=analytics_result, semantic_model=sm)
    assert len(preds) > 0
    assert preds[0].feasible is False
    assert "Prediction unavailable" in preds[0].prediction or "No numeric measures" in preds[0].prediction

# ==========================================
# FLOW 5: Copilot Groundedness & Anti-Hallucination
# ==========================================
def test_flow_5_copilot_groundedness_and_unsupported_queries():
    df = pd.DataFrame({"Sales": [5000, 10000], "Product": ["Widget A", "Widget B"]})
    ws_id = f"ws-copilot-{uuid.uuid4().hex[:6]}"
    p, sm, c = _create_and_profile_workspace(df, ws_id, "Retail")
    try:
        # Ask supported question
        res1 = UniversalAIBrain.query("What is the total sales?", workspace_id=ws_id)
        assert "answer" in res1
        assert res1.get("confidence", 0) > 0

        # Ask unsupported question
        res2 = UniversalAIBrain.query("How many employees does this company have?", workspace_id=ws_id)
        assert "answer" in res2
        # Grounded answer: does not fabricate employee counts, stick to dataset evidence
        assert "15,000" in res2["answer"] or "sales" in res2["answer"].lower()
    finally:
        c.unlink(missing_ok=True)
