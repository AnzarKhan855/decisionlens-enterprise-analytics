import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import SecurityManager

client = TestClient(app)

@pytest.fixture
def auth_headers():
    token = SecurityManager.create_access_token({"sub": "admin@decisionlens.ai", "role": "SUPER_ADMIN"})
    return {"Authorization": f"Bearer {token}"}

def test_cache_control_headers(auth_headers):
    res = client.get("/api/v1/health")
    assert res.headers.get("Cache-Control") == "no-cache, no-store, must-revalidate, max-age=0"
    assert res.headers.get("Pragma") == "no-cache"

def test_copilot_distinct_answers_for_different_questions(auth_headers):
    questions = [
        "What is the total sales?",
        "Which category performs best?",
        "What is average profit?",
        "What trends do you see?",
        "What anomalies exist?",
        "What should management do?",
        "Forecast future sales.",
        "What are the biggest risks?",
        "Compare category by sales.",
        "Give me an executive board summary."
    ]

    answers = []
    for q in questions:
        res = client.post("/api/v1/copilot/query", json={"question": q}, headers=auth_headers)
        assert res.status_code == 200, f"Query failed for question '{q}': {res.status_code}"
        data = res.json()
        assert "answer" in data
        answers.append(data["answer"])

    # Verify answers are NOT all identical across 10 distinct questions
    unique_answers = set(answers)
    assert len(unique_answers) > 1, f"Copilot returned identical answers across all questions! Unique count: {len(unique_answers)}"

def test_scenario_levers_endpoint(auth_headers):
    res = client.get("/api/v1/analytics/scenario/levers", headers=auth_headers)
    assert res.status_code == 200
    assert "available_levers" in res.json()

def test_reports_executive_endpoint(auth_headers):
    res = client.get("/api/v1/reports/executive", headers=auth_headers)
    assert res.status_code == 200
    assert "report_title" in res.json() or "sections" in res.json()
