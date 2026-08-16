import sys
import json
import zipfile
import io
from pathlib import Path

backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

import requests

BASE_URL = "http://127.0.0.1:8000/api/v1"

def run_phase_audit():
    print("==================================================", flush=True)
    print("PHASE 1 - 8 AUDIT & TRACE", flush=True)
    print("==================================================", flush=True)

    # Create a test ZIP archive containing 2 CSV files
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr(
            "orders.csv",
            "order_id,customer_id,sales_amount,order_date\n"
            "ORD-901,CUST-90,500.00,2026-07-31\n"
            "ORD-902,CUST-91,750.00,2026-07-31\n"
        )
        zf.writestr(
            "customers.csv",
            "customer_id,customer_name,city,state\n"
            "CUST-90,Acme Enterprise,New York,NY\n"
            "CUST-91,Global Logistics,Chicago,IL\n"
        )
    zip_bytes = zip_buffer.getvalue()

    # PHASE 1: POST /api/v1/workspace/upload-zip
    files = {"file": ("enterprise_dataset.zip", zip_bytes, "application/zip")}
    data = {"workspace_name": "Audit Test Enterprise Workspace"}

    upload_res = requests.post(f"{BASE_URL}/workspace/upload-zip", files=files, data=data)
    print(f"\n[PHASE 3 API] POST /workspace/upload-zip: HTTP {upload_res.status_code}")
    upload_json = upload_res.json()
    print(f"Upload Response JSON:\n{json.dumps(upload_json, indent=2)}")

    uploaded_ws_id = upload_json.get("workspace_id") or upload_json.get("active_workspace")
    uploaded_ws_name = upload_json.get("workspace_name")

    # PHASE 3: GET /api/v1/workspaces
    ws_list_res = requests.get(f"{BASE_URL}/workspaces")
    print(f"\n[PHASE 3 API] GET /workspaces: HTTP {ws_list_res.status_code}")
    ws_list_json = ws_list_res.json()
    print(f"Workspaces List JSON:\n{json.dumps(ws_list_json, indent=2)}")

    # PHASE 3: GET /api/v1/workspace/active
    act_res = requests.get(f"{BASE_URL}/workspace/active")
    print(f"\n[PHASE 3 API] GET /workspace/active: HTTP {act_res.status_code}")
    act_json = act_res.json()
    print(f"Active Workspace JSON:\n{json.dumps(act_json, indent=2)}")
    active_ws_id = act_json.get("workspace_id") or act_json.get("workspace", {}).get("workspace_id")

    # PHASE 3: GET /api/v1/workspace/structure
    struct_res = requests.get(f"{BASE_URL}/workspace/structure?workspace_id={active_ws_id}")
    print(f"\n[PHASE 3 API] GET /workspace/structure: HTTP {struct_res.status_code}")
    struct_json = struct_res.json()
    print(f"Structure JSON:\n{json.dumps(struct_json, indent=2)}")

    # PHASE 3: GET /api/v1/dashboard/dynamic
    dash_res = requests.get(f"{BASE_URL}/dashboard/dynamic?workspace_id={active_ws_id}")
    print(f"\n[PHASE 3 API] GET /dashboard/dynamic?workspace_id={active_ws_id}: HTTP {dash_res.status_code}")
    dash_json = dash_res.json()
    print(f"Dashboard JSON:\n{json.dumps(dash_json, indent=2, default=str)}")

    # PHASE 6: DuckDB & Parquet inspection
    from app.database.duckdb_engine import DuckDBEngine
    from app.database.storage import STORAGE_DIR
    from app.services.workspace_service import EnterpriseWorkspaceManager

    print("\n--- PHASE 6: DUCKDB & PARQUET INSPECTION ---")
    parquet_files = list(STORAGE_DIR.glob("*.parquet"))
    print(f"Parquet files in STORAGE_DIR ({STORAGE_DIR}):")
    for pf in parquet_files:
        print(f"  - {pf.name} (size: {pf.stat().st_size} bytes)")

    conn = DuckDBEngine.get_connection()
    try:
        tables_res = conn.execute("SHOW TABLES").fetchall()
        print(f"DuckDB Registered Tables: {tables_res}")
    except Exception as e:
        print(f"DuckDB SHOW TABLES error: {e}")
    finally:
        conn.close()

    # PHASE 7: Semantic Model inspection
    from app.analytics.unified_semantic_model import UnifiedSemanticModelBuilder
    sem_model = UnifiedSemanticModelBuilder.build_workspace_semantic_model(workspace_id=active_ws_id, force_rebuild=False)
    print("\n--- PHASE 7: SEMANTIC MODEL INSPECTION ---")
    print(f"Semantic Model Workspace ID: '{sem_model.get('workspace_id')}'")
    print(f"Table Count:                 {sem_model.get('tables_count')}")
    print(f"Active Joins Count:          {sem_model.get('active_joins_count')}")
    print(f"Fact Tables:                 {sem_model.get('fact_tables')}")
    print(f"Dimension Tables:            {sem_model.get('dimension_tables')}")

    # PHASE 1 SUMMARY TABLE
    print("\n==================================================")
    print("PHASE 1 IDENTIFIER SYNCHRONIZATION AUDIT:")
    print(f"1. uploaded workspace_id:                '{uploaded_ws_id}'")
    print(f"2. uploaded workspace_name:              '{uploaded_ws_name}'")
    print(f"3. active workspace_id (/workspace/active): '{active_ws_id}'")
    print(f"4. semantic model workspace_id:          '{sem_model.get('workspace_id')}'")
    print(f"5. dashboard workspace_exists:           {dash_json.get('workspace_exists')}")
    print(f"6. dashboard total_rows:                 {dash_json.get('total_rows')}")
    print(f"7. Identifiers Match:                    {uploaded_ws_id == active_ws_id == sem_model.get('workspace_id')}")
    print("==================================================")

if __name__ == "__main__":
    run_phase_audit()
