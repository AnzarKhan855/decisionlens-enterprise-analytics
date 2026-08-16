from pathlib import Path
from typing import Any, Dict, List, Optional

from app.analytics.semantic_analytics import SemanticAnalyticsEngine
from app.ingestion.semantic_profiler import SemanticDataProfiler


class DynamicKPIEngine:
    """
    Universal Empirical Dynamic KPI Engine.
    Strictly derives all metrics from actual uploaded dataset columns.
    """

    @staticmethod
    def generate_from_parquet(parquet_path: Path, semantic_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not semantic_profile:
            semantic_profile = SemanticDataProfiler.profile(parquet_path)

        kpi_summary = SemanticAnalyticsEngine.get_summary_kpis(parquet_path, semantic_profile)
        total_rows = kpi_summary["total_records"]
        dataset_name = parquet_path.name
        measures = semantic_profile["column_categories"].get("measures", [])

        primary_highlights = []

        if measures:
            for m in measures[:3]:
                m_stats = kpi_summary["metrics"].get(m, {})
                total_val = m_stats.get("sum", 0)
                primary_highlights.append({
                    "name": m.replace("_", " ").title(),
                    "value": f"{total_val:,.2f}",
                    "available": True,
                    "status": "Derived from Dataset",
                    "source_dataset": dataset_name,
                    "source_column": m,
                    "formula": f"SUM({m})",
                    "rows_analyzed": total_rows,
                    "insight": f"Calculated as total sum of '{m}' across {total_rows:,} verified rows."
                })
        else:
            primary_highlights.append({
                "name": "Metrics",
                "value": "Unavailable",
                "available": False,
                "status": "Missing Numeric Columns",
                "source_dataset": dataset_name,
                "source_column": "None",
                "formula": "N/A",
                "rows_analyzed": total_rows,
                "reason": "This dataset does not contain numeric measure columns for KPI generation."
            })
            primary_highlights.append({
                "name": "Total Record Count",
                "value": f"{total_rows:,}",
                "available": True,
                "status": "Verified",
                "source_dataset": dataset_name,
                "source_column": "*",
                "formula": "COUNT(*)",
                "rows_analyzed": total_rows,
                "insight": "Total verified records in dataset."
            })

        return {
            "total_records": total_rows,
            "primary_highlights": primary_highlights,
            "dataset_name": dataset_name,
            "measures_found": measures,
        }
