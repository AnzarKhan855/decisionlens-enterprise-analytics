import re
from typing import Any, Dict, List
from pathlib import Path

from app.database.duckdb_engine import DuckDBEngine
from app.ingestion.domain_classifier import DatasetDomainClassifier


class DatasetDetector:
    """
    Legacy Dataset Category Detector.
    Delegates to DatasetDomainClassifier for v10.0 multi-domain classification.
    """

    @staticmethod
    def detect_from_parquet(parquet_path: Path) -> Dict[str, Any]:
        result = DatasetDomainClassifier.classify(parquet_path)
        return {
            "dataset_type": result["domain"],
            "confidence": result["confidence"],
            "scores": {},
            "reason": result.get("reason", ""),
            "matched_columns": result.get("matched_columns", [])
        }