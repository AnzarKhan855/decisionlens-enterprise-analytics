import tempfile
import pandas as pd
import uuid
from pathlib import Path

from app.ai.universal_copilot_brain import UniversalAIBrain
from app.ingestion.generic_loader import GenericDataLoader
from app.database.storage import ParquetStorageManager


def test_universal_copilot_brain_top_n():
    df = pd.DataFrame({
        "order_id": ["ORD-" + str(i) for i in range(1, 41)],
        "customer_id": ["CUST-" + str(i % 10 + 1) for i in range(40)],
        "product_category": ["Electronics", "Clothing", "Home", "Books"] * 10,
        "region": ["North", "South", "East", "West"] * 10,
        "sales_amount": [100.0 + i * 10 for i in range(40)],
        "order_date": ["2024-01-15"] * 40,
        "shipping_cost": [5.0, 10.0, 3.0, 8.0] * 10,
    })

    dataset_id = str(uuid.uuid4())
    csv_path = Path(tempfile.mktemp(suffix=".csv"))
    df.to_csv(csv_path, index=False)

    try:
        parquet_path = GenericDataLoader.convert_to_parquet(csv_path, dataset_id)
        response = UniversalAIBrain.query(
            question="What are the top performing product categories?",
            dataset_id=dataset_id,
        )

        assert response["confidence"] > 0, "Confidence must be positive"
        assert response.get("support", {}).get("intent") == "top_n", "Intent should be top_n"
        assert len(response.get("evidence", [])) > 0, "Must have evidence"
        assert response.get("calculation") is not None, "Must have calculation"
    finally:
        if csv_path.exists():
            csv_path.unlink()
        ParquetStorageManager.delete_dataset_files(dataset_id)


def test_no_hallucination_missing_column():
    df = pd.DataFrame({
        "name": ["Alice", "Bob", "Charlie"],
        "age": [25, 30, 35],
        "city": ["NYC", "LA", "Chicago"],
    })

    dataset_id = str(uuid.uuid4())
    csv_path = Path(tempfile.mktemp(suffix=".csv"))
    df.to_csv(csv_path, index=False)

    try:
        parquet_path = GenericDataLoader.convert_to_parquet(csv_path, dataset_id)
        response = UniversalAIBrain.query(
            question="What is the average salary?",
            dataset_id=dataset_id,
        )
        columns = response.get("columns", [])
        assert "salary" not in [c.lower() for c in columns], "Must not reference missing salary column"

        response2 = UniversalAIBrain.query(
            question="What is the total revenue?",
            dataset_id=dataset_id,
        )
        columns2 = response2.get("columns", [])
        assert "revenue" not in [c.lower() for c in columns2], "Must not reference missing revenue column"
    finally:
        if csv_path.exists():
            csv_path.unlink()
        ParquetStorageManager.delete_dataset_files(dataset_id)


def test_domain_detection_generic():
    df = pd.DataFrame({
        "product_id": ["P" + str(i) for i in range(10)],
        "category": ["Electronics", "Clothing", "Home"] * 3 + ["Books"],
        "price": [100.0, 50.0, 75.0, 200.0, 30.0, 45.0, 150.0, 80.0, 60.0, 120.0],
        "quantity_sold": [10, 20, 15, 5, 30, 25, 8, 12, 18, 6],
    })

    dataset_id = str(uuid.uuid4())
    csv_path = Path(tempfile.mktemp(suffix=".csv"))
    df.to_csv(csv_path, index=False)

    try:
        parquet_path = GenericDataLoader.convert_to_parquet(csv_path, dataset_id)
        response = UniversalAIBrain.query(
            question="What are the top performing product categories?",
            dataset_id=dataset_id,
        )
        domain = response.get("support", {}).get("domain", "Unknown")
        assert domain is not None, "Domain must be detected"
    finally:
        if csv_path.exists():
            csv_path.unlink()
        ParquetStorageManager.delete_dataset_files(dataset_id)
