from pathlib import Path
from typing import Optional

from app.semantic_model.domain_detector import classify_domain, DOMAIN_KEYWORDS
from app.semantic_model.core import BusinessDomain
from app.database.duckdb_engine import DuckDBEngine


class DatasetDomainClassifier:
    """
    DecisionLens v10.0 Enterprise Multi-Domain AI Dataset Classifier.
    Delegates to semantic_model.domain_detector.classify_domain for
    the single source of truth domain classification.
    """

    DOMAINS = {d.value: kws for d, kws in DOMAIN_KEYWORDS.items()}

    @classmethod
    def classify(cls, parquet_path: Path, filename: Optional[str] = None) -> dict:
        schema = DuckDBEngine.get_schema(parquet_path)
        if not schema:
            return {
                "domain": "Unknown Dataset",
                "confidence": 0.0,
                "reason": "Could not read schema from Parquet file.",
                "matched_columns": []
            }

        raw_columns = list(schema.keys())
        measures = [
            c for c, t in schema.items()
            if any(nt in t.upper() for nt in ["BIGINT", "INTEGER", "SMALLINT", "TINYINT", "DOUBLE", "FLOAT", "DECIMAL", "HUGEINT", "REAL"])
            and not c.lower().endswith("_id")
        ]

        return classify_domain(
            table_name=filename or parquet_path.name,
            columns=raw_columns,
            measures=measures,
        )
