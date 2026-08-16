import tempfile
from pathlib import Path
import pandas as pd
import uuid
import pytest

from app.database.storage import ParquetStorageManager
from app.ingestion.generic_loader import GenericDataLoader
from app.ai.universal_copilot_brain import UniversalAIBrain
from app.ai.validation.answer_validator import AnswerValidationLayer
from app.ai.validation.schemas import (
    AnswerValidationRequest,
    EvidenceRecord,
    InsightClaim,
    NumericClaim,
    RecommendationClaim,
    ValidationResult,
)


def _create_test_parquet(df: pd.DataFrame) -> Path:
    dataset_id = str(uuid.uuid4())
    csv_path = Path(tempfile.mktemp(suffix=".csv"))
    df.to_csv(csv_path, index=False)
    parquet_path = GenericDataLoader.convert_to_parquet(csv_path, dataset_id)
    return parquet_path, csv_path, dataset_id


def _cleanup(csv_path: Path, dataset_id: str):
    if csv_path.exists():
        csv_path.unlink()
    ParquetStorageManager.delete_dataset_files(dataset_id)


class TestAnswerValidationLayer:
    def test_valid_sql_backed_answer(self):
        req = AnswerValidationRequest(
            question="What is the total revenue?",
            answer_text="Total revenue is 5000.00 across 40 records.",
            evidence=[
                EvidenceRecord(
                    source="duckdb_sql",
                    query="SELECT SUM(revenue) FROM read_parquet('...')",
                    rows_returned=1,
                    columns_used=["revenue"],
                    tables_used=["sales"],
                    snippet="Total revenue is 5000.00",
                    confidence=0.9,
                )
            ],
            numeric_values=[
                NumericClaim(value="5000.00", context="Total revenue is 5000.00", evidence_ref="duckdb_sql")
            ],
            recommendations=[],
            insights=[],
            sql_query="SELECT SUM(revenue) FROM read_parquet('...')",
            analysis_rows=[{"total_revenue": 5000.0}],
            dataset_columns=["revenue"],
            status="ok",
        )
        result = AnswerValidationLayer.validate(req)
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert result.confidence_score > 0.0

    def test_missing_evidence_rejected(self):
        req = AnswerValidationRequest(
            question="What is the profit?",
            answer_text="Profit is 1000.00.",
            evidence=[],
            numeric_values=[
                NumericClaim(value="1000.00", context="Profit is 1000.00", evidence_ref=None)
            ],
            recommendations=[],
            insights=[],
            sql_query=None,
            analysis_rows=[],
            dataset_columns=[],
            status="ok",
        )
        result = AnswerValidationLayer.validate(req)
        assert result.is_valid is False
        assert len(result.missing_evidence) > 0

    def test_unsupported_question_detected(self):
        req = AnswerValidationRequest(
            question="What is the weather today?",
            answer_text="I cannot determine this from the available columns.",
            evidence=[],
            numeric_values=[],
            recommendations=[],
            insights=[],
            sql_query=None,
            analysis_rows=[],
            dataset_columns=[],
            status="unavailable",
        )
        result = AnswerValidationLayer.validate(req)
        assert result.unsupported_question is True
        assert result.unsupported_reason is not None

    def test_fabrication_risk_detected(self):
        req = AnswerValidationRequest(
            question="What is the forecast?",
            answer_text="The projected forecast is likely to increase by 15% next quarter.",
            evidence=[
                EvidenceRecord(
                    source="duckdb_sql",
                    query="SELECT ...",
                    rows_returned=12,
                    columns_used=["revenue"],
                    tables_used=["sales"],
                    snippet="Historical data contains 12 periods.",
                    confidence=0.8,
                )
            ],
            numeric_values=[
                NumericClaim(value="15", context="increase by 15%", evidence_ref="duckdb_sql")
            ],
            recommendations=[],
            insights=[],
            sql_query="SELECT ...",
            analysis_rows=[{"period": "2024-01", "value": 1000.0}],
            dataset_columns=["revenue"],
            status="ok",
        )
        result = AnswerValidationLayer.validate(req)
        assert len(result.warnings) > 0

    def test_no_fabrication_on_clean_text(self):
        req = AnswerValidationRequest(
            question="How many records?",
            answer_text="The dataset contains 40 total records.",
            evidence=[
                EvidenceRecord(
                    source="duckdb_sql",
                    query="SELECT COUNT(*) FROM read_parquet('...')",
                    rows_returned=1,
                    columns_used=[],
                    tables_used=["sales"],
                    snippet="The dataset contains 40 total records.",
                    confidence=0.95,
                )
            ],
            numeric_values=[
                NumericClaim(value="40", context="contains 40 total records", evidence_ref="duckdb_sql")
            ],
            recommendations=[],
            insights=[],
            sql_query="SELECT COUNT(*) FROM read_parquet('...')",
            analysis_rows=[{"total_records": 40}],
            dataset_columns=[],
            status="ok",
        )
        result = AnswerValidationLayer.validate(req)
        assert result.is_valid is True
        assert result.confidence_score > 0.8


class TestAnalystAgentValidation:
    def test_cybersecurity_no_fake_outcome(self):
        df = pd.DataFrame({
            "src_ip": ["10.0.0.1", "10.0.0.2", "10.0.0.1"],
            "attack_type": ["DDoS", "Phishing", "DDoS"],
            "severity": ["High", "Medium", "High"],
        })
        parquet_path, csv_path, dataset_id = _create_test_parquet(df)
        try:
            result = UniversalAIBrain.query(
                question="What are the top attack types?",
                dataset_id=dataset_id,
            )
            assert "support" in result
            assert result.get("confidence") > 0
            assert result.get("support", {}).get("recommendation", {}).get("confidence", 0) > 0
        finally:
            _cleanup(csv_path, dataset_id)

    def test_education_no_fake_outcome(self):
        df = pd.DataFrame({
            "student_id": range(1, 21),
            "subject": ["Math", "Science", "History"] * 6 + ["Math", "Science"],
            "marks": [85, 90, 78] * 6 + [92, 88],
            "attendance": [95, 80, 85] * 6 + [90, 88],
        })
        parquet_path, csv_path, dataset_id = _create_test_parquet(df)
        try:
            result = UniversalAIBrain.query(
                question="What is the average marks?",
                dataset_id=dataset_id,
            )
            assert "support" in result
            assert result.get("confidence") > 0
        finally:
            _cleanup(csv_path, dataset_id)

    def test_healthcare_no_fake_outcome(self):
        df = pd.DataFrame({
            "patient_id": range(1, 21),
            "diagnosis": ["Flu", "Diabetes", "Hypertension"] * 6 + ["Flu", "Diabetes"],
            "age": [25, 45, 60] * 6 + [30, 50],
        })
        parquet_path, csv_path, dataset_id = _create_test_parquet(df)
        try:
            result = UniversalAIBrain.query(
                question="What are the common diagnoses?",
                dataset_id=dataset_id,
            )
            assert "support" in result
            assert result.get("confidence") > 0
        finally:
            _cleanup(csv_path, dataset_id)


class TestAnalyticsValidation:
    def test_generate_kpis_includes_validation(self):
        import tempfile
        from pathlib import Path
        import pandas as pd
        from app.database.storage import ParquetStorageManager
        from app.ingestion.generic_loader import GenericDataLoader
        from app.semantic_model.kpi_detector import detect_kpis

        df = pd.DataFrame({
            "order_id": range(1, 11),
            "revenue": [100.0 * i for i in range(1, 11)],
            "quantity": [i for i in range(1, 11)],
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

    def test_generate_insights_includes_validation(self):
        import tempfile
        from pathlib import Path
        import pandas as pd
        from app.database.storage import ParquetStorageManager
        from app.ingestion.generic_loader import GenericDataLoader
        from app.analytics.auto_insights import AutoInsights

        df = pd.DataFrame({
            "order_id": range(1, 11),
            "revenue": [100.0 * i for i in range(1, 11)],
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


class TestRAGEvidenceBinding:
    def test_retriever_evidence_binding(self):
        from app.ai.rag.retriever import WorkspaceMetadataRetriever
        from app.ai.rag.vector_store import SimpleMetadataStore

        SimpleMetadataStore.reset()
        SimpleMetadataStore.add_document(
            doc_id="table:test_sales",
            text="Table test_sales has columns: revenue, quantity. Measures: revenue, quantity. Dimensions: region. Temporal: date. Rows: 100.",
            metadata={
                "type": "table",
                "table_name": "test_sales",
                "file_path": "/tmp/test_sales.parquet",
                "columns": ["revenue", "quantity", "region", "date"],
                "measures": ["revenue", "quantity"],
                "dimensions": ["region"],
                "temporal": ["date"],
                "row_count": 100,
                "role": "Fact Table",
            },
        )

        docs = WorkspaceMetadataRetriever.retrieve("revenue by region", top_k=5)
        assert len(docs) > 0
        for d in docs:
            assert "evidence_binding" in d
