import tempfile
from pathlib import Path
import pandas as pd
import uuid

from app.database.storage import ParquetStorageManager
from app.database.duckdb_engine import DuckDBEngine
from app.ingestion.generic_loader import GenericDataLoader
from app.ingestion.semantic_profiler import SemanticDataProfiler

from app.analytics.semantic_analytics import SemanticAnalyticsEngine
from app.analytics.dynamic_kpis import DynamicKPIEngine
from app.analytics.chart_engine import ChartEngine
from app.services.dynamic_dashboard_service import get_dynamic_dashboard


def test_phase2_analytics_pipeline():
    # 1. Create dummy financial dataset
    df = pd.DataFrame({
        "tx_id": [f"TX-{i}" for i in range(1, 51)],
        "tx_date": pd.date_range(start="2026-01-01", periods=50, freq="D").astype(str),
        "department": ["Engineering", "Sales", "Marketing", "HR", "Finance"] * 10,
        "expense": [500.0 * i for i in range(1, 51)],
        "budget_allocated": [1000.0 * i for i in range(1, 51)],
        "status": ["Approved", "Pending", "Rejected"] * 16 + ["Approved", "Pending"]
    })

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        csv_path = Path(tmp.name)
        df.to_csv(csv_path, index=False)

    dataset_id = str(uuid.uuid4())

    try:
        # Convert to Parquet
        parquet_path = GenericDataLoader.convert_to_parquet(csv_path, dataset_id)
        profile = SemanticDataProfiler.profile(parquet_path)

        # 2. Test Semantic Analytics Engine
        kpi_summary = SemanticAnalyticsEngine.get_summary_kpis(parquet_path, profile)
        assert kpi_summary["total_records"] == 50
        assert "expense" in kpi_summary["metrics"]
        assert kpi_summary["metrics"]["expense"]["sum"] > 0

        # 3. Test Time-Series Trend
        trend = SemanticAnalyticsEngine.get_time_series_trend(parquet_path, "tx_date", "expense")
        assert len(trend) == 50
        assert "period" in trend[0] and "value" in trend[0]

        # 4. Test Dimension Breakdown
        breakdown = SemanticAnalyticsEngine.get_dimension_breakdown(parquet_path, "department", "expense")
        assert len(breakdown) == 5
        assert breakdown[0]["category"] in ["Engineering", "Sales", "Marketing", "HR", "Finance"]

        # 5. Test Dynamic KPI Engine
        kpis = DynamicKPIEngine.generate_from_parquet(parquet_path, profile)
        assert kpis["total_records"] == 50
        assert len(kpis["primary_highlights"]) > 0

        # 6. Test Chart Engine
        charts = ChartEngine.generate_from_parquet(parquet_path, profile)
        assert len(charts) >= 2
        chart_types = [c["type"] for c in charts]
        assert "area" in chart_types or "bar" in chart_types

    finally:
        if csv_path.exists():
            csv_path.unlink()
        ParquetStorageManager.delete_dataset_files(dataset_id)
