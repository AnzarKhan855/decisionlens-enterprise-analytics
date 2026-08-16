"""Quick test of copilot API endpoints with dataset_id."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Get active workspace to use as dataset_id
from app.services.workspace_service import EnterpriseWorkspaceManager
ws_id = EnterpriseWorkspaceManager.get_active_workspace_id()
print(f"Active workspace: {ws_id}")

# Test /ai/query with dataset_id = workspace_id
print("\n=== Testing /ai/query with dataset_id ===")
resp = client.post("/api/v1/ai/query", json={
    "dataset_id": ws_id,
    "question": "What are the top 3 strategic recommendations based on the data?"
})
print(f"Status: {resp.status_code}")
if resp.status_code != 200:
    print(f"Error: {resp.text}")
else:
    data = resp.json()
    results = data.get("results", {})
    print(f"Results keys: {list(results.keys())}")
    print(f"Answer preview: {str(results.get('answer', ''))[:300]}")

# Test /copilot/query
print("\n=== Testing /copilot/query ===")
resp2 = client.post("/api/v1/copilot/query", json={
    "dataset_id": ws_id,
    "question": "What are the top 3 strategic recommendations based on the data?"
})
print(f"Status: {resp2.status_code}")
if resp2.status_code != 200:
    print(f"Error: {resp2.text[:500]}")
else:
    data2 = resp2.json()
    print(f"Answer preview: {str(data2.get('answer', ''))[:300]}")
    print(f"Confidence: {data2.get('confidence')}")
    print(f"Status: {data2.get('status')}")
