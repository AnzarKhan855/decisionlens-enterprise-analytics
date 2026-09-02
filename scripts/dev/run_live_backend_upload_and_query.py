import sys
import json
from pathlib import Path

backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app
from app.services.workspace_service import EnterpriseWorkspaceManager

client = TestClient(app)

def run_real_upload_and_query():
    print("==================================================", flush=True)
    print("LIVE BACKEND EXECUTION & LOG TRACE", flush=True)
    print("==================================================", flush=True)

    # 1. Perform Real Upload via API Client
    print("\n--- [LOG: UPLOAD REQUEST] ---", flush=True)
    csv_content = (
        "order_id,customer_id,sales_amount,order_date\n"
        "ORD-001,CUST-10,150.50,2026-07-01\n"
        "ORD-002,CUST-11,299.00,2026-07-02\n"
        "ORD-003,CUST-12,450.75,2026-07-03\n"
        "ORD-004,CUST-10,120.00,2026-07-04\n"
    )
    files = {"file": ("test_sales.csv", csv_content.encode("utf-8"), "text/csv")}

    upload_res = client.post("/api/v1/upload/", files=files)
    print(f"Upload HTTP Status: {upload_res.status_code}", flush=True)
    upload_json = upload_res.json()
    print(f"Upload Response Payload:\n{json.dumps(upload_json, indent=2)}", flush=True)

    ws_id = upload_json.get("workspace_id") or upload_json.get("active_workspace") or "ws-enterprise-retail"

    # 2. Perform Real Workspace Activation via API Client
    print("\n--- [LOG: WORKSPACE ACTIVATION] ---", flush=True)
    activate_res = client.post(f"/api/v1/workspaces/{ws_id}/activate")
    print(f"Activation HTTP Status: {activate_res.status_code}", flush=True)
    print(f"Activation Response Payload:\n{json.dumps(activate_res.json(), indent=2)}", flush=True)

    active_ws_id = EnterpriseWorkspaceManager.get_active_workspace_id()
    print(f"Active Workspace ID in Backend Registry: '{active_ws_id}'", flush=True)

    # 3. Perform Dashboard Request via API Client
    print("\n--- [LOG: DASHBOARD REQUEST] ---", flush=True)
    print(f"Executing: GET /api/v1/dashboard/dynamic?workspace_id={active_ws_id}", flush=True)
    dash_res = client.get(f"/api/v1/dashboard/dynamic?workspace_id={active_ws_id}")
    print(f"Dashboard HTTP Status: {dash_res.status_code}", flush=True)

    dash_json = dash_res.json()

    print("\n==================================================", flush=True)
    print("EXACT JSON RETURNED BY GET /api/v1/dashboard/dynamic:", flush=True)
    print("==================================================", flush=True)
    print(json.dumps(dash_json, indent=2), flush=True)
    print("==================================================", flush=True)

if __name__ == "__main__":
    run_real_upload_and_query()
