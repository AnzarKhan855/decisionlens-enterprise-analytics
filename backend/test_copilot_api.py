"""Quick test of copilot API endpoints."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Test /ai/query
print("=== Testing /ai/query ===")
resp = client.post("/api/v1/ai/query", json={
    "dataset_id": None,
    "question": "What are the top 3 strategic recommendations based on the data?"
})
print(f"Status: {resp.status_code}")
print(f"Response keys: {list(resp.json().keys())}")
print(f"Has results: {'results' in resp.json()}")
if resp.status_code != 200:
    print(f"Error: {resp.text}")
else:
    data = resp.json()
    results = data.get("results", {})
    print(f"Results keys: {list(results.keys())}")
    print(f"Answer preview: {str(results.get('answer', ''))[:200]}")

print()

# Test /copilot/query
print("=== Testing /copilot/query ===")
resp2 = client.post("/api/v1/copilot/query", json={
    "dataset_id": None,
    "question": "What are the top 3 strategic recommendations based on the data?"
})
print(f"Status: {resp2.status_code}")
print(f"Response keys: {list(resp2.json().keys())}")
if resp2.status_code != 200:
    print(f"Error: {resp2.text}")
else:
    data2 = resp2.json()
    print(f"Answer preview: {str(data2.get('answer', ''))[:200]}")
    print(f"Confidence: {data2.get('confidence')}")
    print(f"Status: {data2.get('status')}")
