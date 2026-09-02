import sys
import json
from pathlib import Path

backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.services.workspace_service import EnterpriseWorkspaceManager
from app.services.dynamic_dashboard_service import get_dynamic_dashboard
from app.database.storage import STORAGE_DIR
from app.database.duckdb_engine import DuckDBEngine

def run_verify():
    # 1. Ensure a valid active workspace with ingested table exists
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    real_parquet = STORAGE_DIR / "retail_sales.parquet"
    conn = DuckDBEngine.get_connection()
    conn.execute(f"COPY (SELECT 'ORD-001' AS order_id, 'CUST-10' AS customer_id, 150.50 AS sales_amount, DATE '2026-07-01' AS order_date) TO '{real_parquet.as_posix()}' (FORMAT PARQUET)")
    conn.close()

    active_ws_id = "ws-enterprise-retail"
    EnterpriseWorkspaceManager.create_or_get_workspace(active_ws_id, "Enterprise Retail Operations")
    EnterpriseWorkspaceManager.register_table(
        active_ws_id,
        "sales",
        [{"name": "order_id", "type": "VARCHAR"}, {"name": "customer_id", "type": "VARCHAR"}, {"name": "sales_amount", "type": "FLOAT"}, {"name": "order_date", "type": "DATE"}],
        4,
        str(real_parquet)
    )
    EnterpriseWorkspaceManager.set_active_workspace(active_ws_id)

    # 2. Execute get_dynamic_dashboard for active workspace
    dashboard_res = get_dynamic_dashboard(dataset_id=active_ws_id)

    # 3. Print exact JSON response
    print(json.dumps(dashboard_res, indent=2, default=str))

if __name__ == "__main__":
    run_verify()
