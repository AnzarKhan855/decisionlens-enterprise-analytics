from typing import Dict, Any, List, Optional
from pathlib import Path

from app.analytics.semantic_analytics import SemanticAnalyticsEngine
from app.ingestion.semantic_profiler import SemanticDataProfiler


class DashboardGenerator:
    """
    Universal Dynamic Dashboard Generator.
    Generates domain-agnostic KPIs from the dataset profile.
    Never forces retail-specific KPIs onto non-retail datasets.
    """

    @classmethod
    def detect_domain(cls, parquet_path: Path, semantic_profile: Optional[Dict[str, Any]] = None) -> str:
        from app.ingestion.domain_classifier import DatasetDomainClassifier
        res = DatasetDomainClassifier.classify(parquet_path)
        return res["domain"]

    @classmethod
    def generate_domain_kpis(cls, parquet_path: Path, domain: str, profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        total_rows = profile.get("total_rows", 0)
        measures = profile.get("column_categories", {}).get("measures", [])
        ds_name = parquet_path.name

        if not measures:
            return [
                {"name": "Total Records", "value": f"{total_rows:,}", "available": True, "status": "Verified", "source_dataset": ds_name, "insight": f"Dataset contains {total_rows:,} verified records."},
                {"name": "Metrics", "value": "Unavailable", "available": False, "status": "Missing Numeric Columns", "source_dataset": ds_name, "reason": "This dataset does not contain numeric measure columns for KPI generation."}
            ]

        kpis = []
        for m in measures[:4]:
            stats = profile.get("measure_stats", {}).get(m, {})
            total_val = stats.get("sum", 0)
            kpis.append({
                "name": m.replace("_", " ").title(),
                "value": f"{total_val:,.2f}",
                "available": True,
                "status": "Derived Metric",
                "source_dataset": ds_name,
                "source_column": m,
                "formula": f"SUM({m})",
                "rows_analyzed": total_rows,
                "insight": f"Calculated as sum of {m} across {total_rows:,} verified rows."
            })

        kpis.append({
            "name": "Total Records",
            "value": f"{total_rows:,}",
            "available": True,
            "status": "Verified",
            "source_dataset": ds_name,
            "source_column": "*",
            "formula": "COUNT(*)",
            "rows_analyzed": total_rows,
            "insight": f"Dataset contains {total_rows:,} verified records."
        })

        return kpis
