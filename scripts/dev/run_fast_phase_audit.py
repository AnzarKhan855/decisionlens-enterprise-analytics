import sys
import json
import zipfile
import io
from pathlib import Path

backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

import requests

BASE_URL = "http://127.0.0.1:8000/api/v1"

def run_fast_audit():
    print("==================================================", flush=True)
    print("PHASE 1 - 10 AUDIT & TRACE SUMMARY", flush=True)
    print("==================================================", flush=True)

    # 1. GET /api/v1/workspace/active
    act_res = requests.get(f"{BASE_URL}/workspace/active")
    print(f"\n[GET /workspace/active] HTTP {act_res.status_code}")
    act_json = act_res.json()
    active_ws_id = act_json.get("workspace_id") or act_json.get("workspace", {}).get("workspace_id")
    print(f"Active Workspace ID: '{active_ws_id}'")

    # 2. GET /api/v1/workspaces
    ws_res = requests.get(f"{BASE_URL}/workspaces")
    print(f"\n[GET /workspaces] HTTP {ws_res.status_code}")
    ws_json = ws_res.json()
    print(f"Total Workspaces Count: {ws_json.get('total_count')}")

    # 3. GET /api/v1/dashboard/dynamic?workspace_id=<active_ws_id>
    dash_res = requests.get(f"{BASE_URL}/dashboard/dynamic?workspace_id={active_ws_id}")
    print(f"\n[GET /dashboard/dynamic?workspace_id={active_ws_id}] HTTP {dash_res.status_code}")
    dash_json = dash_res.json()

    print("\nDASHBOARD API RESPONSE:")
    print(f"status:           '{dash_json.get('status')}'")
    print(f"workspace_exists: {dash_json.get('workspace_exists')}")
    print(f"dataset_type:     '{dash_json.get('dataset_type')}'")
    print(f"total_rows:       {dash_json.get('total_rows')}")
    print(f"total_columns:    {dash_json.get('total_columns')}")
    print(f"kpis_count:       {len(dash_json.get('kpis', []))}")
    print(f"charts_count:     {len(dash_json.get('charts', []))}")
    print(f"executive_briefing: {dash_json.get('executive_briefing', {}).get('greeting') if dash_json.get('executive_briefing') else None}")

    print("\n==================================================")
    print("PHASE 1 - 10 AUDIT CONCLUSION:")
    print(f"Active Workspace ID:             '{active_ws_id}'")
    print(f"Dashboard workspace_exists:      {dash_json.get('workspace_exists')}")
    print(f"Dashboard Data Present:          {dash_json.get('workspace_exists') == True}")
    print("==================================================")

if __name__ == "__main__":
    run_fast_audit()
