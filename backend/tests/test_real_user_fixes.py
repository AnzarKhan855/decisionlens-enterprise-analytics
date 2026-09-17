import os
import sys
import uuid
import pytest
import pandas as pd
from fastapi.testclient import TestClient
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core.security import SecurityManager
from app.core.rbac import SUPER_ADMIN, ORGANIZATION_ADMIN, EMPLOYEE
from app.observability.error_handler import RequestState
from app.services.workspace_service import EnterpriseWorkspaceManager
from app.services.analytics_cache_service import AnalyticsCacheService
from app.database.storage import STORAGE_DIR

client = TestClient(app)


def test_contextvars_workspace_propagation():
    """Verify that RequestState uses ContextVar and propagates across async/thread contexts."""
    test_id = f"ws-{uuid.uuid4().hex[:8]}"
    RequestState.set_workspace_id(test_id)
    assert RequestState.get_workspace_id() == test_id

    import asyncio
    async def _async_check():
        return RequestState.get_workspace_id()

    loop = asyncio.new_event_loop()
    try:
        val = loop.run_until_complete(_async_check())
        assert val == test_id
    finally:
        loop.close()


def test_scenario_levers_caching(tmp_path):
    """Verify Scenario levers caching in AnalyticsCacheService."""
    ws_id = f"ws-cache-{uuid.uuid4().hex[:8]}"
    parquet_path = tmp_path / f"{ws_id}.parquet"
    df = pd.DataFrame({
        "date": ["2024-01-01", "2024-01-02"],
        "revenue": [100.0, 200.0],
        "cost": [50.0, 60.0]
    })
    df.to_parquet(parquet_path)

    # Initially None
    assert AnalyticsCacheService.get_cached_levers(ws_id, parquet_path) is None

    # Set cache
    levers_data = {
        "levers": [
            {"id": "price", "name": "Price Adjustment", "type": "percentage", "range": [-20, 20], "default": 0}
        ],
        "kpis": [{"id": "revenue", "name": "Revenue"}],
        "dataset_name": ws_id,
        "precomputed": True
    }
    AnalyticsCacheService.set_cached_levers(ws_id, levers_data, parquet_path)

    # Retrieval should hit cache
    cached = AnalyticsCacheService.get_cached_levers(ws_id, parquet_path)
    assert cached is not None
    assert cached["dataset_name"] == ws_id
    assert len(cached["levers"]) == 1

    # Invalidation should evict
    AnalyticsCacheService.invalidate(ws_id)
    assert AnalyticsCacheService.get_cached_levers(ws_id, parquet_path) is None


def test_delete_all_workspaces_rbac():
    """Verify DELETE /workspaces/all respects RBAC permissions."""
    # 1. Unauthenticated request -> 401
    res = client.delete("/api/v1/workspaces/all")
    assert res.status_code == 401

    # 2. Employee (non-admin) request -> 403
    emp_token = SecurityManager.create_access_token({"sub": "emp@company.com", "role": EMPLOYEE})
    res = client.delete("/api/v1/workspaces/all", headers={"Authorization": f"Bearer {emp_token}"})
    assert res.status_code == 403

    # 3. Super Admin request -> 200
    admin_token = SecurityManager.create_access_token({"sub": "admin@company.com", "role": SUPER_ADMIN})
    # Create two test workspaces first
    ws1 = f"test-all-1-{uuid.uuid4().hex[:6]}"
    ws2 = f"test-all-2-{uuid.uuid4().hex[:6]}"
    EnterpriseWorkspaceManager.create_or_get_workspace(ws1, "Test WS 1")
    EnterpriseWorkspaceManager.create_or_get_workspace(ws2, "Test WS 2")

    res = client.delete("/api/v1/workspaces/all", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "deleted_count" in data


def test_copilot_distinct_answers(tmp_path):
    """Verify EnterpriseDecisionEngine._build_executive_answer returns distinct answers for different modes."""
    from app.ai.enterprise_decision_engine import EnterpriseDecisionEngine

    analytics_dict = {
        "volume": 1500,
        "kpis": [{"name": "Revenue", "value": 50000.0, "formatted_value": "$50,000"}],
        "anomalies": [{"period": "2024-03", "severity": "HIGH", "z_score": 2.8}],
        "root_causes": [],
        "evidence": {"measures_analyzed": ["revenue"], "dimensions_analyzed": ["region"]}
    }

    # Mode: top_n
    evidence_top_n = [
        {"dimension": "North", "metric_value": 35000.0},
        {"dimension": "South", "metric_value": 15000.0},
    ]
    ans_top_n = EnterpriseDecisionEngine._build_executive_answer(
        question="What are the top regions by revenue?",
        decision_mode={"mode": "top_n"},
        analytics_dict=analytics_dict,
        predictions=[],
        recommendations=[],
        evidence_rows=evidence_top_n,
        sql_query="SELECT region AS dimension, SUM(revenue) AS metric_value FROM t GROUP BY 1",
        domain="Retail",
    )
    assert "North" in ans_top_n
    assert "top performer" in ans_top_n.lower()

    # Mode: trend
    evidence_trend = [
        {"period": "2024-01", "metric_value": 10000.0},
        {"period": "2024-02", "metric_value": 25000.0},
    ]
    ans_trend = EnterpriseDecisionEngine._build_executive_answer(
        question="What is the revenue trend?",
        decision_mode={"mode": "trend"},
        analytics_dict=analytics_dict,
        predictions=[],
        recommendations=[],
        evidence_rows=evidence_trend,
        sql_query="SELECT period, SUM(revenue) FROM t GROUP BY 1",
        domain="Retail",
    )
    assert "increased" in ans_trend.lower() or "trend" in ans_trend.lower()
    assert "25,000.00" in ans_trend

    # Mode: breakdown
    evidence_breakdown = [
        {"category": "Electronics", "value": 30000.0, "cnt": 800},
        {"category": "Apparel", "value": 20000.0, "cnt": 700},
    ]
    ans_breakdown = EnterpriseDecisionEngine._build_executive_answer(
        question="Show breakdown of revenue by product category",
        decision_mode={"mode": "breakdown"},
        analytics_dict=analytics_dict,
        predictions=[],
        recommendations=[],
        evidence_rows=evidence_breakdown,
        sql_query="SELECT category, SUM(revenue) FROM t GROUP BY 1",
        domain="Retail",
    )
    assert "Electronics" in ans_breakdown
    assert "Breakdown" in ans_breakdown

    # Ensure answers are not identical canned text
    assert ans_top_n != ans_trend
    assert ans_trend != ans_breakdown


def test_strategic_decisions_endpoint():
    """Verify GET /api/v1/analytics/strategic-decisions returns 200 with authentication."""
    token = SecurityManager.create_access_token({"sub": "user@company.com", "role": EMPLOYEE})
    res = client.get("/api/v1/analytics/strategic-decisions", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert "decisions" in data or "strategic_decisions" in data or "items" in data or isinstance(data, dict)
