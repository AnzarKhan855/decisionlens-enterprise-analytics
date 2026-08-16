import tempfile
from pathlib import Path
import pandas as pd
import uuid

from app.database.storage import ParquetStorageManager
from app.ingestion.generic_loader import GenericDataLoader
from app.ml.prediction_engine import UniversalPredictionEngine
from app.analytics.universal_engine import UniversalAnalyticsEngine
from app.semantic_model.core import SemanticModel
from app.services.dynamic_dashboard_service import get_dynamic_dashboard


def test_phase4_ml_pipeline():
    # 1. Create 60-day synthetic demand & revenue time-series
    dates = pd.date_range(start="2026-01-01", periods=60, freq="D").astype(str)
    df = pd.DataFrame({
        "tx_id": [f"TX-{i}" for i in range(1, 61)],
        "tx_date": dates,
        "region": ["North", "South", "East", "West"] * 15,
        "revenue": [200.0 + (i * 12.0) for i in range(1, 61)],
        "quantity": [i % 7 + 1 for i in range(1, 61)]
    })

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        csv_path = Path(tmp.name)
        df.to_csv(csv_path, index=False)

    dataset_id = str(uuid.uuid4())

    try:
        parquet_path = GenericDataLoader.convert_to_parquet(csv_path, dataset_id)

        # 2. Test UniversalAnalyticsEngine produces predictions
        sm = SemanticModel(workspace_id=dataset_id, domain="Generic Business", dataset_type="Unknown")
        analytics = UniversalAnalyticsEngine.analyze(sm, parquet_path=parquet_path)
        predictions = UniversalPredictionEngine.generate(
            analytics_result=analytics,
            semantic_model=sm,
        )
        assert len(predictions) > 0, "Engine must produce at least one prediction"
        first = predictions[0]
        assert hasattr(first, "model_type")
        assert hasattr(first, "prediction")
        assert hasattr(first, "confidence")
        assert hasattr(first, "evidence")
        assert hasattr(first, "business_impact")
        assert hasattr(first, "time_horizon")
        assert hasattr(first, "risk_level")
        assert hasattr(first, "recommended_action")
        assert hasattr(first, "assumptions")
        assert 0.0 <= first.confidence <= 1.0

        # 3. Test Dynamic Dashboard Payload
        dashboard = get_dynamic_dashboard(dataset_id)
        assert "predictions" in dashboard
        assert "ml_forecast" in dashboard
        assert "ml_segmentation" in dashboard

    finally:
        if csv_path.exists():
            csv_path.unlink()
        ParquetStorageManager.delete_dataset_files(dataset_id)
