import tempfile
from pathlib import Path
import pandas as pd
import uuid

from app.database.storage import ParquetStorageManager
from app.database.duckdb_engine import DuckDBEngine
from app.ingestion.generic_loader import GenericDataLoader
from app.ingestion.semantic_profiler import SemanticDataProfiler
from app.ingestion.validator import DataValidator
from app.ingestion.dataset_detector import DatasetDetector


def test_phase1_pipeline():
    # 1. Create a dummy test DataFrame representing sales transactions
    df = pd.DataFrame({
        "order_id": [f"ORD-{i}" for i in range(1, 101)],
        "transaction_date": pd.date_range(start="2026-01-01", periods=100, freq="D").astype(str),
        "region": ["North", "South", "East", "West"] * 25,
        "revenue": [100.5 * i for i in range(1, 101)],
        "quantity": [i % 5 + 1 for i in range(1, 101)],
        "status": ["Completed", "Pending", "Shipped"] * 33 + ["Completed"]
    })

    # Save to temp CSV
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        csv_path = Path(tmp.name)
        df.to_csv(csv_path, index=False)

    dataset_id = str(uuid.uuid4())

    try:
        # 2. Convert CSV to Parquet
        parquet_path = GenericDataLoader.convert_to_parquet(csv_path, dataset_id)
        assert parquet_path.exists(), "Parquet file should be created"

        # 3. DuckDB Query Verification
        row_count = DuckDBEngine.get_row_count(parquet_path)
        assert row_count == 100, f"Expected 100 rows, got {row_count}"

        schema = DuckDBEngine.get_schema(parquet_path)
        assert "revenue" in schema
        assert "region" in schema

        # 4. Semantic Profiler Verification
        profile = SemanticDataProfiler.profile(parquet_path)
        assert profile["total_rows"] == 100
        assert profile["total_columns"] == 6

        categories = profile["column_categories"]
        assert "revenue" in categories["measures"]
        assert "quantity" in categories["measures"]
        assert "region" in categories["dimensions"]
        assert "transaction_date" in categories["temporal"] or "order_id" in categories["identifiers"]

        # 5. Dataset Health Validator
        val_report = DataValidator.validate(parquet_path)
        assert val_report["health_score"] > 80, f"Expected high health score, got {val_report['health_score']}"

        # 6. Detector Test
        detector_res = DatasetDetector.detect_from_parquet(parquet_path)
        assert detector_res["dataset_type"] in ["Retail & E-Commerce", "General Business Analytics"]

    finally:
        # Clean up files
        if csv_path.exists():
            csv_path.unlink()
        ParquetStorageManager.delete_dataset_files(dataset_id)
