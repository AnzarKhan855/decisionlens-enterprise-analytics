import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import time
import uuid
import tempfile
import pandas as pd

from app.ingestion.generic_loader import GenericDataLoader
from app.semantic_model.core import SemanticModel
from app.analytics.universal_engine import UniversalAnalyticsEngine
from app.services.dynamic_dashboard_service import get_dynamic_dashboard
from app.reports.executive_report_engine import UniversalExecutiveReportEngine
from app.reports.role_based_report_engine import RoleBasedReportEngine
from app.services.enterprise_strategy_engine import EnterpriseStrategyEngine

def run_profiling():
    dates = pd.date_range(start="2026-01-01", periods=100, freq="D").astype(str)
    df = pd.DataFrame({
        "tx_id": [f"TX-{i}" for i in range(1, 101)],
        "tx_date": dates,
        "region": ["North", "South", "East", "West"] * 25,
        "revenue": [200.0 + (i * 12.0) for i in range(1, 101)],
        "quantity": [i % 7 + 1 for i in range(1, 101)]
    })

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        csv_path = Path(tmp.name)
        df.to_csv(csv_path, index=False)

    dataset_id = str(uuid.uuid4())
    workspace_id = dataset_id

    try:
        parquet_path = GenericDataLoader.convert_to_parquet(csv_path, dataset_id)

        t0 = time.perf_counter()
        dashboard, analytics_result = get_dynamic_dashboard(
            dataset_id=dataset_id,
            workspace_id=workspace_id,
            return_analytics_result=True
        )
        t1 = time.perf_counter()
        print(f"[Profiling] get_dynamic_dashboard took: {(t1 - t0)*1000:.2f} ms")

        sm = analytics_result.semantic_model if analytics_result else SemanticModel(workspace_id=workspace_id)
        predictions = getattr(analytics_result, "predictions", []) if analytics_result else []

        t2 = time.perf_counter()
        exec_report = UniversalExecutiveReportEngine.generate_report(
            analytics_result=analytics_result,
            semantic_model=sm,
            prediction_result=predictions,
        )
        t3 = time.perf_counter()
        print(f"[Profiling] UniversalExecutiveReportEngine.generate_report took: {(t3 - t2)*1000:.2f} ms")

        t4 = time.perf_counter()
        role_report = RoleBasedReportEngine.generate_report(
            analytics_result=analytics_result,
            semantic_model=sm,
            audience="CEO",
            predictions=predictions,
        )
        t5 = time.perf_counter()
        print(f"[Profiling] RoleBasedReportEngine.generate_report took: {(t5 - t4)*1000:.2f} ms")

        t6 = time.perf_counter()
        strat_report = EnterpriseStrategyEngine.analyze(workspace_id)
        t7 = time.perf_counter()
        print(f"[Profiling] EnterpriseStrategyEngine.analyze took: {(t7 - t6)*1000:.2f} ms")

        # Second call (Warm Cache)
        t8 = time.perf_counter()
        dashboard2, analytics_result2 = get_dynamic_dashboard(
            dataset_id=dataset_id,
            workspace_id=workspace_id,
            return_analytics_result=True
        )
        t9 = time.perf_counter()
        print(f"[Profiling] get_dynamic_dashboard (Warm Cache) took: {(t9 - t8)*1000:.2f} ms")

        t10 = time.perf_counter()
        role_report2 = RoleBasedReportEngine.generate_report(
            analytics_result=analytics_result2 or analytics_result,
            semantic_model=sm,
            audience="CEO",
            predictions=predictions,
        )
        t11 = time.perf_counter()
        print(f"[Profiling] RoleBasedReportEngine.generate_report (Warm Cache) took: {(t11 - t10)*1000:.2f} ms")

    finally:
        csv_path.unlink(missing_ok=True)

if __name__ == "__main__":
    run_profiling()
