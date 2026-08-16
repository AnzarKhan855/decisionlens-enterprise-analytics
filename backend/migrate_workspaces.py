import json
import os
from pathlib import Path
from typing import Dict, Any, List

_BASE_DIR = Path(__file__).resolve().parent
WORKSPACES_FILE = _BASE_DIR / "storage" / "workspaces.json"
ACTIVE_WORKSPACE_FILE = _BASE_DIR / "storage" / "active_workspace.json"
DELETED_WORKSPACES_FILE = _BASE_DIR / "storage" / "deleted_workspaces.json"


def migrate():
    print("==================================================", flush=True)
    print("DECISIONLENS v10.0 WORKSPACE CONSOLIDATION MIGRATION", flush=True)
    print("==================================================", flush=True)

    if not WORKSPACES_FILE.exists():
        print("[Migration] No storage/workspaces.json found. Nothing to migrate.", flush=True)
        return

    with open(WORKSPACES_FILE, "r") as f:
        try:
            raw_data = json.load(f)
        except Exception as e:
            print(f"[Migration Error] Could not parse workspaces.json: {e}", flush=True)
            return

    total_initial = len(raw_data)
    print(f"[Migration] Total raw workspace entries found: {total_initial}", flush=True)

    # Load deleted set
    deleted_set = set()
    if DELETED_WORKSPACES_FILE.exists():
        try:
            with open(DELETED_WORKSPACES_FILE, "r") as f:
                deleted_set = set(json.load(f))
        except Exception:
            pass

    # Category buckets for consolidation
    consolidated: Dict[str, Dict[str, Any]] = {}

    def get_target_workspace_id(domain: str, name: str) -> tuple[str, str]:
        d_lower = domain.lower()
        if "cyber" in d_lower or "security" in d_lower or "log" in d_lower:
            return "ws-cybersecurity-ops", "Cybersecurity Operations Workspace"
        elif "health" in d_lower or "patient" in d_lower or "clinical" in d_lower:
            return "ws-healthcare-analytics", "Healthcare Analytics Workspace"
        elif "edu" in d_lower or "student" in d_lower or "academic" in d_lower:
            return "ws-education-academic", "Education & Academic Workspace"
        elif "hr" in d_lower or "employee" in d_lower or "workforce" in d_lower:
            return "ws-human-resources", "Human Resources Workforce Workspace"
        elif "finance" in d_lower or "bank" in d_lower or "ledger" in d_lower:
            return "ws-finance-banking", "Finance & Banking Operations Workspace"
        elif "order" in d_lower:
            return "ws-enterprise-retail", "Enterprise Retail & E-Commerce Workspace"
        else:
            return "ws-business-operations", "Enterprise Business Operations Workspace"

    # Iterate over all workspace entries and merge tables into consolidated Business Workspaces
    tables_migrated_count = 0
    for ws_id, ws in raw_data.items():
        if ws_id in deleted_set or not isinstance(ws, dict):
            continue

        domain = ws.get("industry") or ws.get("domain") or "Enterprise Domain"
        name = ws.get("name") or ws_id
        target_id, target_title = get_target_workspace_id(domain, name)

        if target_id not in consolidated:
            consolidated[target_id] = {
                "workspace_id": target_id,
                "name": target_title,
                "industry": domain,
                "domain": domain,
                "business_type": "Enterprise Data Operations",
                "business_model": "Multi-Table Data Platform",
                "health_score": ws.get("health_score", 88),
                "data_quality_pct": ws.get("data_quality_pct", 88),
                "ai_ready": True,
                "forecast_ready": True,
                "time_range": "Active Period",
                "connected_tables_count": 0,
                "tables": [],
                "relationships": [],
                "semantic_model": {
                    "fact_tables": [],
                    "dimension_tables": [],
                    "lookup_tables": [],
                    "reference_tables": []
                },
                "lineage": [],
                "status": "Ready",
                "owner": "Enterprise Administrator",
                "last_refresh": "Just now"
            }

        target_ws = consolidated[target_id]
        tables = ws.get("tables", [])

        # If entry had no tables listed, create a table entry from parquet if file exists
        if not tables:
            tbl_name = name.lower().replace(" ", "_").replace("-", "_")
            parquet_path = _BASE_DIR / "storage" / "parquet" / f"{tbl_name}.parquet"
            if parquet_path.exists():
                tables.append({
                    "table_name": tbl_name,
                    "columns": [],
                    "rows": 0,
                    "file_path": str(parquet_path)
                })

        for t in tables:
            t_name = t.get("table_name")
            if not t_name:
                continue

            existing_names = [et["table_name"] for et in target_ws["tables"]]
            if t_name not in existing_names:
                target_ws["tables"].append(t)
                tables_migrated_count += 1
                if t_name not in target_ws["semantic_model"]["fact_tables"]:
                    target_ws["semantic_model"]["fact_tables"].append(t_name)

        target_ws["connected_tables_count"] = len(target_ws["tables"])
        target_ws["total_records"] = sum(t.get("rows", 0) for t in target_ws["tables"])

    # Write consolidated workspaces to storage/workspaces.json
    WORKSPACES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(WORKSPACES_FILE, "w") as f:
        json.dump(consolidated, f, indent=2)

    # Set active workspace to first consolidated workspace
    active_ws_id = list(consolidated.keys())[0] if consolidated else None
    if active_ws_id:
        ACTIVE_WORKSPACE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(ACTIVE_WORKSPACE_FILE, "w") as f:
            json.dump({"active_workspace_id": active_ws_id}, f)

    print(f"[Migration Summary] Initial Workspaces: {total_initial} -> Consolidated Workspaces: {len(consolidated)}", flush=True)
    print(f"[Migration Summary] Total Tables Preserved: {tables_migrated_count}", flush=True)
    print(f"[Migration Summary] Active Workspace Set To: '{active_ws_id}'", flush=True)
    print("==================================================", flush=True)


if __name__ == "__main__":
    migrate()
