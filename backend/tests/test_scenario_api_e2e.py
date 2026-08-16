"""
End-to-end verification for BUG 8: Data-driven Scenario Simulator.

Tests the actual API endpoints against real workspace/dataset fixtures.
"""
import sys
import os
import json
import tempfile
import shutil
import uuid
from pathlib import Path

# Ensure backend is on path
backend_dir = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_e2e.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key")

from fastapi.testclient import TestClient

from app.main import app
from app.database.connection import create_tables, SessionLocal
from app.database.crud import get_latest_dataset, create_user, get_user_by_email
from app.database.storage import ParquetStorageManager, UPLOAD_RAW_DIR
from app.ingestion.generic_loader import GenericDataLoader
from app.ingestion.semantic_profiler import SemanticDataProfiler
from app.semantic_model.engine import build_semantic_model
from app.services.workspace_service import EnterpriseWorkspaceManager
from app.core.security import SecurityManager
from app.core.rbac import ORGANIZATION_ADMIN, SUPER_ADMIN

client = TestClient(app)


def _setup_workspace(df, ws_id: str, dataset_name: str = "data.csv"):
    """Persist a dataframe as a parquet dataset and register it."""
    ParquetStorageManager.ensure_directories()
    UPLOAD_RAW_DIR.mkdir(parents=True, exist_ok=True)

    raw_path = UPLOAD_RAW_DIR / dataset_name
    df.to_csv(raw_path, index=False)

    dataset_id = f"{ws_id}__{dataset_name.replace('.csv', '')}"
    parquet_path = GenericDataLoader.convert_to_parquet(raw_path, dataset_id)

    EnterpriseWorkspaceManager.create_or_get_workspace(ws_id, ws_id.replace("-", " ").title())
    profile = SemanticDataProfiler.profile(parquet_path)
    EnterpriseWorkspaceManager.register_table(
        ws_id,
        dataset_name.replace(".csv", ""),
        [{"name": c, "type": profile["columns"][c].get("inferred_type", "VARCHAR")} for c in profile["columns"]],
        profile.get("total_rows", 0),
        str(parquet_path),
    )

    build_semantic_model(workspace_id=ws_id, force_rebuild=True)
    return ws_id, dataset_id, parquet_path


def _create_test_token() -> str:
    """Create a valid JWT token for testing."""
    db = SessionLocal()
    try:
        user = get_user_by_email(db, "test-scenario@decisionlens.ai")
        if not user:
            hashed = SecurityManager.hash_password("testpass123")
            user = create_user(
                db,
                email="test-scenario@decisionlens.ai",
                hashed_password=hashed,
                full_name="Scenario Test User",
                role="ADMIN",
            )
        token = SecurityManager.create_access_token(
            data={"sub": user.email, "role": user.role}
        )
        return token
    finally:
        db.close()


def _auth_headers():
    return {"Authorization": f"Bearer {_create_test_token()}"}


def _get_levers(dataset_id: str = None):
    url = "/api/v1/analytics/scenario/levers"
    if dataset_id:
        url += f"?dataset_id={dataset_id}"
    resp = client.get(url, headers=_auth_headers())
    return resp.status_code, resp.json() if resp.status_code < 500 else resp.text


def _simulate(changes: list, dataset_id: str = None):
    url = "/api/v1/analytics/scenario/simulate"
    if dataset_id:
        url += f"?dataset_id={dataset_id}"
    resp = client.post(url, json={"changes": changes}, headers=_auth_headers())
    return resp.status_code, resp.json() if resp.status_code < 500 else resp.text


class TestScenarioAPIEndToEnd:
    """End-to-end API tests for the data-driven scenario simulator."""

    def setup_method(self):
        create_tables()
        self.workspace_ids = []

    def teardown_method(self):
        for ws_id in self.workspace_ids:
            try:
                EnterpriseWorkspaceManager.delete_workspace(ws_id)
            except Exception:
                pass

    def test_retail_dataset_produces_quantity_and_price_levers(self):
        """A. Retail-like dataset should produce Quantity + Price levers."""
        import pandas as pd

        df = pd.DataFrame({
            "Invoice": range(1000),
            "StockCode": [f"SKU{i%100}" for i in range(1000)],
            "Quantity": [1 + (i % 10) for i in range(1000)],
            "Price": [1.0 + (i % 50) * 0.1 for i in range(1000)],
            "Country": ["UK", "US", "DE", "FR", "ES"] * 200,
        })

        ws_id = f"ws-retail-{uuid.uuid4().hex[:8]}"
        self.workspace_ids.append(ws_id)
        _, dataset_id, _ = _setup_workspace(df, ws_id)

        status, data = _get_levers(dataset_id)
        assert status == 200, f"Lever discovery failed: {data}"
        levers = [l["column"] for l in data.get("available_levers", [])]
        assert "Quantity" in levers, f"Quantity should be a lever, got {levers}"
        assert "Price" in levers, f"Price should be a lever, got {levers}"
        assert data["scenario_capability"]["supported"] is True

        # Simulate +10% Quantity
        status2, sim = _simulate([{"lever_id": "quantity", "change_pct": 10}], dataset_id)
        assert status2 == 200, f"Simulation failed: {sim}"
        assert "Quantity" in sim.get("baseline", {})
        assert "Quantity" in sim.get("scenario", {})
        assert sim["baseline"]["Quantity"] > 0
        assert abs(sim["scenario"]["Quantity"] - sim["baseline"]["Quantity"] * 1.1) < 0.01

    def test_manufacturing_dataset_produces_operational_levers(self):
        """B. Manufacturing dataset should produce Temperature + Vibration + Pressure."""
        import pandas as pd

        factory_vals = ["Factory-A", "Factory-B", "Factory-C"] * 67
        df = pd.DataFrame({
            "MachineID": [f"MCH-{i%20:03d}" for i in range(200)],
            "Temperature": [65.0 + (i % 10) * 2 for i in range(200)],
            "Vibration": [0.1 + (i % 5) * 0.05 for i in range(200)],
            "Pressure": [100.0 + (i % 8) * 5 for i in range(200)],
            "Factory": factory_vals[:200],
        })

        ws_id = f"ws-mfg-{uuid.uuid4().hex[:8]}"
        self.workspace_ids.append(ws_id)
        _, dataset_id, _ = _setup_workspace(df, ws_id)

        status, data = _get_levers(dataset_id)
        assert status == 200, f"Lever discovery failed: {data}"
        levers = [l["column"] for l in data.get("available_levers", [])]
        assert "Temperature" in levers, f"Temperature should be a lever, got {levers}"
        assert "Vibration" in levers, f"Vibration should be a lever, got {levers}"
        assert "Pressure" in levers, f"Pressure should be a lever, got {levers}"
        assert "MachineID" not in levers, f"MachineID must be excluded, got {levers}"
        assert "Factory" not in levers, f"Factory must be excluded, got {levers}"

        status2, sim = _simulate([{"lever_id": "temperature", "change_pct": 5}], dataset_id)
        assert status2 == 200, f"Simulation failed: {sim}"
        assert "Temperature" in sim.get("baseline", {})

    def test_healthcare_dataset_produces_numeric_levers(self):
        """C. Healthcare dataset should produce Age + WaitTime + TreatmentCost."""
        import pandas as pd

        df = pd.DataFrame({
            "PatientID": [f"P{i:04d}" for i in range(100)],
            "Age": [20 + (i % 5) * 10 for i in range(100)],
            "WaitTime": [10 + (i % 12) * 10 for i in range(100)],
            "TreatmentCost": [100.0 + (i % 10) * 500 for i in range(100)],
            "Department": ["Cardiology", "Neurology", "Orthopedics", "Pediatrics"] * 25,
        })

        ws_id = f"ws-health-{uuid.uuid4().hex[:8]}"
        self.workspace_ids.append(ws_id)
        _, dataset_id, _ = _setup_workspace(df, ws_id)

        status, data = _get_levers(dataset_id)
        assert status == 200, f"Lever discovery failed: {data}"
        levers = [l["column"] for l in data.get("available_levers", [])]
        assert "Age" in levers, f"Age should be a lever, got {levers}"
        assert "WaitTime" in levers, f"WaitTime should be a lever, got {levers}"
        assert "TreatmentCost" in levers, f"TreatmentCost should be a lever, got {levers}"
        assert "PatientID" not in levers, f"PatientID must be excluded, got {levers}"
        assert "Department" not in levers, f"Department must be excluded, got {levers}"

    def test_categorical_only_dataset_returns_unsupported(self):
        """D. Categorical-only dataset must return supported=false, not an error."""
        import pandas as pd

        df = pd.DataFrame({
            "Region": ["North", "South", "East", "West"] * 25,
            "Category": ["A", "B", "C", "D", "E"] * 20,
            "Status": ["Active", "Inactive", "Pending"] * 33 + ["Active"],
        })

        ws_id = f"ws-cat-{uuid.uuid4().hex[:8]}"
        self.workspace_ids.append(ws_id)
        _, dataset_id, _ = _setup_workspace(df, ws_id)

        status, data = _get_levers(dataset_id)
        assert status == 200, f"Lever discovery failed: {data}"
        assert len(data.get("available_levers", [])) == 0
        assert data["scenario_capability"]["supported"] is False

        # Simulation with empty changes should also work
        status2, sim = _simulate([], dataset_id)
        assert status2 == 200, f"Simulation failed: {sim}"

    def test_identifier_heavy_dataset_excludes_ids(self):
        """E. Numeric identifiers must be excluded; Amount must be available."""
        import pandas as pd

        df = pd.DataFrame({
            "CustomerID": [f"CUST-{i}" for i in range(100)],
            "TransactionID": [f"TXN-{i}" for i in range(100)],
            "Amount": [10.0 + (i % 20) * 2 for i in range(100)],
            "Region": ["US", "EU", "APAC"] * 33 + ["US"],
        })

        ws_id = f"ws-id-{uuid.uuid4().hex[:8]}"
        self.workspace_ids.append(ws_id)
        _, dataset_id, _ = _setup_workspace(df, ws_id)

        status, data = _get_levers(dataset_id)
        assert status == 200, f"Lever discovery failed: {data}"
        levers = [l["column"] for l in data.get("available_levers", [])]
        assert "Amount" in levers, f"Amount should be a lever, got {levers}"
        assert "CustomerID" not in levers, f"CustomerID must be excluded, got {levers}"
        assert "TransactionID" not in levers, f"TransactionID must be excluded, got {levers}"

    def test_zero_values_are_genuine_data(self):
        """F. Zero values should be treated as genuine data, not missing."""
        import pandas as pd

        df = pd.DataFrame({
            "Metric": [0.0] * 50 + [1.0 + i for i in range(50)],
            "Category": ["A", "B"] * 50,
        })

        ws_id = f"ws-zero-{uuid.uuid4().hex[:8]}"
        self.workspace_ids.append(ws_id)
        _, dataset_id, _ = _setup_workspace(df, ws_id)

        status, data = _get_levers(dataset_id)
        assert status == 200, f"Lever discovery failed: {data}"
        levers = [l["column"] for l in data.get("available_levers", [])]
        assert "Metric" in levers, f"Metric should be a lever even with zeros, got {levers}"

    def test_simulation_with_multiple_levers(self):
        """G. Multiple simultaneous levers should be simulatable."""
        import pandas as pd

        df = pd.DataFrame({
            "MetricA": [10.0 + (i % 10) for i in range(100)],
            "MetricB": [5.0 + (i % 8) * 0.5 for i in range(100)],
        })

        ws_id = f"ws-multi-{uuid.uuid4().hex[:8]}"
        self.workspace_ids.append(ws_id)
        _, dataset_id, _ = _setup_workspace(df, ws_id)

        status, data = _get_levers(dataset_id)
        assert status == 200, f"Lever discovery failed: {data}"
        levers = [l["column"] for l in data.get("available_levers", [])]
        assert "MetricA" in levers
        assert "MetricB" in levers

        status2, sim = _simulate([
            {"lever_id": "metrica", "change_pct": 10},
            {"lever_id": "metricb", "change_pct": -5},
        ], dataset_id)
        assert status2 == 200, f"Simulation failed: {sim}"
        assert len(sim.get("applied_changes", [])) == 2

    def test_invalid_lever_id_handled_safely(self):
        """H. Invalid lever IDs should be ignored safely."""
        import pandas as pd

        df = pd.DataFrame({"Metric": [1.0, 2.0, 3.0]})

        ws_id = f"ws-inv-{uuid.uuid4().hex[:8]}"
        self.workspace_ids.append(ws_id)
        _, dataset_id, _ = _setup_workspace(df, ws_id)

        status, sim = _simulate([{"lever_id": "nonexistent", "change_pct": 10}], dataset_id)
        assert status == 200, f"Simulation failed: {sim}"
        assert len(sim.get("applied_changes", [])) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
