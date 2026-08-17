import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import SecurityManager

client = TestClient(app)

@pytest.fixture
def auth_headers():
    token = SecurityManager.create_access_token({"sub": "admin@decisionlens.ai", "role": "SUPER_ADMIN"})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def emp_headers():
    token = SecurityManager.create_access_token({"sub": "employee@decisionlens.ai", "role": "EMPLOYEE"})
    return {"Authorization": f"Bearer {token}"}

def test_copilot_endpoint_not_404(auth_headers):
    # Test POST /api/v1/copilot/query and /api/v1/ai/copilot/query
    res = client.post("/api/v1/copilot/query", json={"question": "What are our top metrics?"}, headers=auth_headers)
    assert res.status_code != 404, f"Expected non-404, got {res.status_code}"

    res2 = client.post("/api/v1/ai/copilot/query", json={"question": "What are our top metrics?"}, headers=auth_headers)
    assert res2.status_code != 404, f"Expected non-404, got {res2.status_code}"

def test_audit_logs_not_403(emp_headers):
    # Test GET /api/v1/audit/logs with EMPLOYEE headers
    res = client.get("/api/v1/audit/logs", headers=emp_headers)
    assert res.status_code == 200, f"Expected 200 OK, got {res.status_code}: {res.text}"
    assert "logs" in res.json() or isinstance(res.json(), list)

def test_scenario_levers_fast_response(auth_headers):
    # Test GET /api/v1/analytics/scenario/levers
    res = client.get("/api/v1/analytics/scenario/levers", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "available_levers" in data

def test_forecast_insufficient_data_fast_return(auth_headers):
    # Test GET /api/v1/ml/forecast when no dataset present
    res = client.get("/api/v1/ml/forecast?dataset_id=nonexistent_ws_id", headers=auth_headers)
    assert res.status_code in (200, 404)
