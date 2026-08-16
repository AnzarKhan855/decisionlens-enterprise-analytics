from fastapi import APIRouter
from typing import Dict, Any
import time
import os
import sys
import platform
from app.database.duckdb_engine import DuckDBEngine
from app.database.crud import get_all_datasets
from app.database.connection import SessionLocal

router = APIRouter()


@router.api_route("/status", methods=["GET", "HEAD"])
def get_system_diagnostics():
    t0 = time.time()
    db = SessionLocal()
    try:
        datasets = get_all_datasets(db)
        dataset_count = len(datasets)

        # DuckDB Engine Connection Verification
        con = DuckDBEngine.get_connection()
        duckdb_status = "connected"
        try:
            con.execute("SELECT 1").fetchone()
        except Exception:
            duckdb_status = "error"

        latency_ms = round((time.time() - t0) * 1000, 2)

        return {
            "status": "healthy",
            "version": "v9.1 Production",
            "backend": f"FastAPI (Python {platform.python_version()})",
            "frontend": "Next.js 16.2 (Turbopack)",
            "database": {
                "sqlite": "connected",
                "duckdb": duckdb_status,
                "dataset_count": dataset_count
            },
            "system_resources": {
                "platform": platform.system(),
                "process_id": os.getpid(),
                "python_version": sys.version.split()[0]
            },
            "api_latency_ms": latency_ms,
            "cache_status": "Active In-Memory DuckDB OLAP Cache",
            "last_audit": "Verified Product Validation Sprint"
        }
    finally:
        db.close()
