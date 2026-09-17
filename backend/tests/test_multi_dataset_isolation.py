import pytest
import pandas as pd
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.services.workspace_service import EnterpriseWorkspaceManager
from app.database.storage import ParquetStorageManager, STORAGE_DIR
from app.analytics.universal_engine import UniversalAnalyticsEngine
from app.semantic_model.core import SemanticModel
from app.services.enterprise_strategy_engine import EnterpriseStrategyEngine
from app.ai.universal_copilot_brain import UniversalAIBrain
from app.services.dynamic_dashboard_service import get_dynamic_dashboard


@pytest.fixture
def client():
    return TestClient(app)


def test_multi_dataset_isolation_and_strategy(client, tmp_path):
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Prepare Retail dataset (Workspace A)
    ws_a_id = "ws-retail-test-iso"
    df_retail = pd.DataFrame({
        "order_id": [f"ORD-{i:03d}" for i in range(1, 101)],
        "category": ["Electronics", "Fashion", "Home", "Books"] * 25,
        "price": [19.99 + i * 2.5 for i in range(100)],
        "freight_value": [5.0 + (i % 5) for i in range(100)],
    })
    parquet_a = STORAGE_DIR / f"{ws_a_id}__orders.parquet"
    df_retail.to_parquet(parquet_a, index=False)

    EnterpriseWorkspaceManager.create_or_get_workspace(ws_a_id, "Retail Test Workspace", industry="Retail")
    EnterpriseWorkspaceManager.register_table(
        ws_a_id,
        "orders",
        [{"name": c, "type": "VARCHAR"} for c in df_retail.columns],
        len(df_retail),
        str(parquet_a)
    )

    # 2. Prepare Cybersecurity dataset (Workspace B)
    ws_b_id = "ws-cyber-test-iso"
    df_cyber = pd.DataFrame({
        "incident_id": [f"INC-{i:04d}" for i in range(1, 121)],
        "attack_vector": ["DDoS", "Phishing", "Malware", "Brute Force"] * 30,
        "threat_level": [1 + (i % 5) for i in range(120)],
        "packet_count": [1000 * (i + 1) for i in range(120)],
        "latency_ms": [15.5 + (i * 0.5) for i in range(120)],
    })
    parquet_b = STORAGE_DIR / f"{ws_b_id}__incidents.parquet"
    df_cyber.to_parquet(parquet_b, index=False)

    EnterpriseWorkspaceManager.create_or_get_workspace(ws_b_id, "Cybersecurity Test Workspace", industry="Cybersecurity")
    EnterpriseWorkspaceManager.register_table(
        ws_b_id,
        "incidents",
        [{"name": c, "type": "VARCHAR"} for c in df_cyber.columns],
        len(df_cyber),
        str(parquet_b)
    )

    try:
        # 3. Test Parquet Resolution Isolation
        path_a = ParquetStorageManager.get_parquet_path_for_workspace(ws_a_id)
        path_b = ParquetStorageManager.get_parquet_path_for_workspace(ws_b_id)
        assert path_a is not None and "retail" in path_a.name
        assert path_b is not None and "cyber" in path_b.name
        assert path_a != path_b

        # 4. Test Dynamic Dashboard Isolation
        dash_a = get_dynamic_dashboard(workspace_id=ws_a_id)
        dash_b = get_dynamic_dashboard(workspace_id=ws_b_id)

        # Check KPIs for Workspace A
        kpi_names_a = [k.get("name") if isinstance(k, dict) else getattr(k, "name", "") for k in dash_a.get("kpis", [])]
        assert any("price" in str(k).lower() or "freight" in str(k).lower() or "record" in str(k).lower() for k in kpi_names_a)
        assert not any("packet" in str(k).lower() or "latency" in str(k).lower() for k in kpi_names_a)

        # Check KPIs for Workspace B
        kpi_names_b = [k.get("name") if isinstance(k, dict) else getattr(k, "name", "") for k in dash_b.get("kpis", [])]
        assert any("packet" in str(k).lower() or "latency" in str(k).lower() or "threat" in str(k).lower() for k in kpi_names_b)
        assert not any("price" in str(k).lower() or "freight" in str(k).lower() for k in kpi_names_b)

        # 5. Test Strategy Module & Recommendation Evidence
        strat_a = EnterpriseStrategyEngine.analyze(ws_a_id)
        strat_b = EnterpriseStrategyEngine.analyze(ws_b_id)

        assert strat_a is not None
        assert strat_b is not None

        # Strategy for Cyber must have valid recommendations
        recs_b = strat_b.get("recommendations", [])
        assert len(recs_b) > 0, "Cybersecurity dataset must have strategic recommendations"

        # 6. Test Copilot Parquet Resolution Isolation
        copilot_path_a = UniversalAIBrain._resolve_parquet_path(workspace_id=ws_a_id)
        copilot_path_b = UniversalAIBrain._resolve_parquet_path(workspace_id=ws_b_id)
        assert copilot_path_a == path_a
        assert copilot_path_b == path_b
        assert copilot_path_a != copilot_path_b

    finally:
        EnterpriseWorkspaceManager.delete_workspace(ws_a_id)
        EnterpriseWorkspaceManager.delete_workspace(ws_b_id)
        if parquet_a.exists():
            parquet_a.unlink(missing_ok=True)
        if parquet_b.exists():
            parquet_b.unlink(missing_ok=True)
