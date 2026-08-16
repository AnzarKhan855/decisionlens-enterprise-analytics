import pytest

from app.semantic_model.domain_detector import classify_dataset_type
from app.semantic_model.kpi_detector import detect_kpis
from app.analytics.auto_insights import AutoInsights
from app.analytics.semantic_analytics import SemanticAnalyticsEngine


class TestDatasetDetection:
    def test_revenue_detection(self):
        cols = ["order_id", "customer_id", "product_id", "category", "sales", "price", "order_date"]
        result = classify_dataset_type("uploaded_orders", cols, [])
        assert result["dataset_type"] == "Retail"
        assert result["dataset_type_confidence"] > 0

    def test_cybersecurity_detection(self):
        cols = ["src_ip", "dst_ip", "attack_type", "severity", "port", "protocol"]
        result = classify_dataset_type("security_logs", cols, [])
        assert result["dataset_type"] == "Cybersecurity"
        assert result["dataset_type_confidence"] > 0

    def test_healthcare_detection(self):
        cols = ["patient_id", "diagnosis", "doctor", "hospital", "admission_date", "discharge_date"]
        result = classify_dataset_type("patient_records", cols, [])
        assert result["dataset_type"] == "Healthcare"
        assert result["dataset_type_confidence"] > 0

    def test_education_detection(self):
        cols = ["student_id", "marks", "grade", "subject", "teacher", "attendance"]
        result = classify_dataset_type("student_grades", cols, [])
        assert result["dataset_type"] == "Education"
        assert result["dataset_type_confidence"] > 0

    def test_generic_business(self):
        cols = ["col_a", "col_b", "col_c"]
        result = classify_dataset_type("generic_data", cols, [])
        assert result["dataset_type"] == "Unknown"


class TestKPIGeneration:
    def test_kpis_detected_from_profile(self):
        import tempfile
        from pathlib import Path
        import pandas as pd
        from app.database.storage import ParquetStorageManager
        from app.ingestion.generic_loader import GenericDataLoader

        df = pd.DataFrame({
            "order_id": [f"ORD-{i}" for i in range(1, 51)],
            "sales": [100.0 + i for i in range(50)],
            "customer_id": [f"CUST-{i % 10}" for i in range(50)],
        })
        csv_path = Path(tempfile.mktemp(suffix=".csv"))
        df.to_csv(csv_path, index=False)
        dataset_id = str(__import__("uuid").uuid4())
        parquet_path = GenericDataLoader.convert_to_parquet(csv_path, dataset_id)
        try:
            kpis = detect_kpis(parquet_path)
            assert len(kpis) > 0
            for kpi in kpis:
                assert hasattr(kpi, "name")
                assert hasattr(kpi, "value")
                assert hasattr(kpi, "aggregation")
        finally:
            csv_path.unlink()
            ParquetStorageManager.delete_dataset_files(dataset_id)

    def test_semantic_analytics_kpis(self):
        import tempfile
        from pathlib import Path
        import pandas as pd
        from app.database.storage import ParquetStorageManager
        from app.ingestion.generic_loader import GenericDataLoader

        df = pd.DataFrame({
            "product": ["A", "B", "C"] * 10,
            "sales": [100.0 + i for i in range(30)],
            "quantity": [10 + i for i in range(30)],
        })
        csv_path = Path(tempfile.mktemp(suffix=".csv"))
        df.to_csv(csv_path, index=False)
        dataset_id = str(__import__("uuid").uuid4())
        parquet_path = GenericDataLoader.convert_to_parquet(csv_path, dataset_id)
        try:
            engine = SemanticAnalyticsEngine()
            kpis = engine.get_summary_kpis(parquet_path)
            assert len(kpis) > 0
        finally:
            csv_path.unlink()
            ParquetStorageManager.delete_dataset_files(dataset_id)


class TestInsights:
    def test_auto_insights_structure(self):
        import tempfile
        from pathlib import Path
        import pandas as pd
        from app.database.storage import ParquetStorageManager
        from app.ingestion.generic_loader import GenericDataLoader

        df = pd.DataFrame({
            "order_id": [f"ORD-{i}" for i in range(1, 31)],
            "sales": [100.0 + i * 3.7 for i in range(30)],
            "customer_id": [f"CUST-{i % 5}" for i in range(30)],
        })
        csv_path = Path(tempfile.mktemp(suffix=".csv"))
        df.to_csv(csv_path, index=False)
        dataset_id = str(__import__("uuid").uuid4())
        parquet_path = GenericDataLoader.convert_to_parquet(csv_path, dataset_id)
        try:
            insights = AutoInsights.generate_from_parquet(parquet_path)
            assert isinstance(insights, list)
            assert len(insights) > 0
        finally:
            csv_path.unlink()
            ParquetStorageManager.delete_dataset_files(dataset_id)


class TestBackwardCompatibility:
    def test_semantic_model_kpis(self):
        import tempfile
        from pathlib import Path
        import pandas as pd
        from app.database.storage import ParquetStorageManager
        from app.ingestion.generic_loader import GenericDataLoader

        df = pd.DataFrame({
            "sales": [10, 20, 30],
            "customer_id": ["A", "B", "C"],
        })
        csv_path = Path(tempfile.mktemp(suffix=".csv"))
        df.to_csv(csv_path, index=False)
        dataset_id = str(__import__("uuid").uuid4())
        parquet_path = GenericDataLoader.convert_to_parquet(csv_path, dataset_id)
        try:
            kpis = detect_kpis(parquet_path)
            assert len(kpis) > 0
            assert hasattr(kpis[0], "name")
        finally:
            csv_path.unlink()
            ParquetStorageManager.delete_dataset_files(dataset_id)
