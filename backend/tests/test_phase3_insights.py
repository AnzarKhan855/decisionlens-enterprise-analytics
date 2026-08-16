import tempfile
from pathlib import Path
import pandas as pd
import uuid

from app.database.storage import ParquetStorageManager
from app.ingestion.generic_loader import GenericDataLoader
from app.ingestion.semantic_profiler import SemanticDataProfiler

from app.analytics.anomaly_engine import StatisticalAnomalyEngine
from app.analytics.variance_engine import VarianceDecompositionEngine
from app.analytics.auto_insights import AutoInsights


def test_phase3_insights_pipeline():
    # 1. Create a dataset with baseline data + 2 severe spike anomalies
    dates = pd.date_range(start="2026-01-01", periods=30, freq="D").astype(str)
    revenue = [100.0] * 30
    revenue[10] = 5000.0  # Severe Spike Anomaly 1
    revenue[25] = 4500.0  # Severe Spike Anomaly 2

    df = pd.DataFrame({
        "order_id": [f"ORD-{i}" for i in range(1, 31)],
        "order_date": dates,
        "region": ["East"] * 20 + ["West"] * 10,
        "revenue": revenue
    })

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        csv_path = Path(tmp.name)
        df.to_csv(csv_path, index=False)

    dataset_id = str(uuid.uuid4())

    try:
        # Convert to Parquet
        parquet_path = GenericDataLoader.convert_to_parquet(csv_path, dataset_id)
        profile = SemanticDataProfiler.profile(parquet_path)

        # 2. Test Statistical Anomaly Engine
        anomalies = StatisticalAnomalyEngine.detect_anomalies(parquet_path, "order_date", "revenue")
        assert len(anomalies) >= 2, f"Expected at least 2 anomalies, got {len(anomalies)}"
        periods = [a["period"] for a in anomalies]
        assert dates[10] in periods or dates[25] in periods

        # 3. Test Variance Decomposition Engine
        variance = VarianceDecompositionEngine.analyze_drivers(parquet_path, "region", "revenue")
        assert variance["top_driver"]["category"] == "East"
        assert variance["top_driver"]["contribution_percentage"] > 50.0

        # 4. Test AutoInsights Generator
        insights = AutoInsights.generate_from_parquet(parquet_path, profile)
        assert len(insights) >= 3
        insight_text = " ".join(insights)
        assert "anomalies" in insight_text.lower() or "records" in insight_text.lower()

    finally:
        if csv_path.exists():
            csv_path.unlink()
        ParquetStorageManager.delete_dataset_files(dataset_id)
