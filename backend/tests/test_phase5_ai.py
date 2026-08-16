import tempfile
from pathlib import Path
import pandas as pd
import uuid

from app.database.storage import ParquetStorageManager
from app.ingestion.generic_loader import GenericDataLoader
from app.ai.universal_copilot_brain import UniversalAIBrain


def test_phase5_ai_pipeline():
    df = pd.DataFrame({
        "order_id": [f"ORD-{i}" for i in range(1, 41)],
        "region": ["North", "South", "East", "West"] * 10,
        "revenue": [100.0 * i for i in range(1, 41)]
    })

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        csv_path = Path(tmp.name)
        df.to_csv(csv_path, index=False)

    dataset_id = str(uuid.uuid4())

    try:
        parquet_path = GenericDataLoader.convert_to_parquet(csv_path, dataset_id)

        # Test Intent 1: Top Performer
        res1 = UniversalAIBrain.query(
            question="Which region generated the highest revenue?",
            dataset_id=dataset_id,
        )
        sql_used = res1.get("support", {}).get("sql_used", "")
        assert "SELECT" in sql_used
        assert len(res1.get("evidence", [])) > 0

        # Test Intent 2: Summary
        res2 = UniversalAIBrain.query(
            question="What is the total revenue?",
            dataset_id=dataset_id,
        )
        assert "SELECT" in res2.get("support", {}).get("sql_used", "")
        assert len(res2.get("evidence", [])) > 0

    finally:
        if csv_path.exists():
            csv_path.unlink()
        ParquetStorageManager.delete_dataset_files(dataset_id)
