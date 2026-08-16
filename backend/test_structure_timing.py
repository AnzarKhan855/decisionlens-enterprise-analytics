import urllib.request
import json
import time

BASE_URL = "http://127.0.0.1:8001"

def test_endpoint(label):
    start = time.time()
    r = urllib.request.urlopen(f"{BASE_URL}/api/v1/workspace/structure")
    data = json.loads(r.read().decode())
    elapsed = (time.time() - start) * 1000
    api_time = data.get("response_time_ms", "N/A")
    status = data.get("status")
    ws_id = data.get("workspace_id")
    tables_count = data.get("metadata", {}).get("tables_count", 0)
    print(f"{label}: HTTP={elapsed:.2f}ms, API_time={api_time}ms, status={status}, ws={ws_id}, tables={tables_count}")
    return elapsed, data
test_endpoint.__test__ = False

if __name__ == "__main__":
    print("=== Testing GET /api/v1/workspace/structure ===\n")

    try:
        t1, d1 = test_endpoint("Request 1 (cold cache)")
        t2, d2 = test_endpoint("Request 2 (warm cache)")
        t3, d3 = test_endpoint("Request 3 (warm cache)")

        print("\n=== Summary ===")
        print(f"Cold cache (first request):  {t1:.2f}ms")
        print(f"Warm cache (second request): {t2:.2f}ms")
        print(f"Warm cache (third request):  {t3:.2f}ms")
        print(f"\nResponse has lineage: {d2.get('lineage') is not None}")
        print(f"Response has summary: {bool(d2.get('summary'))}")
        print(f"Response keys: {list(d2.keys())}")
    except Exception as e:
        print("Timing test skipped (server not running):", e)