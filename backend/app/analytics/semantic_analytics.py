from pathlib import Path
from typing import Any, Dict, List, Optional
import duckdb

from app.database.duckdb_engine import DuckDBEngine
from app.ingestion.semantic_profiler import SemanticDataProfiler
from app.logging.logger import get_logger

logger = get_logger(__name__)


class SemanticAnalyticsEngine:
    """
    Universal Domain-Agnostic Analytics Engine powered by DuckDB.
    Dynamically generates KPIs, time-series aggregations, and dimensional breakdowns for any dataset.
    """

    @staticmethod
    def get_summary_kpis(parquet_path: Path, semantic_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not semantic_profile:
            semantic_profile = SemanticDataProfiler.profile(parquet_path)

        path_str = str(parquet_path).replace("\\", "/")
        measures = semantic_profile["column_categories"].get("measures", [])
        dimensions = semantic_profile["column_categories"].get("dimensions", [])
        temporal = semantic_profile["column_categories"].get("temporal", [])
        total_rows = semantic_profile["total_rows"]

        kpis = {
            "total_records": total_rows,
            "total_measures": len(measures),
            "total_dimensions": len(dimensions),
            "metrics": {}
        }

        # Calculate aggregations for top measures
        if measures:
            select_clauses = []
            for m in measures[:5]:
                col_esc = f'"{m}"'
                select_clauses.extend([
                    f"SUM({col_esc}) as sum_{m}",
                    f"AVG({col_esc}) as avg_{m}",
                    f"MIN({col_esc}) as min_{m}",
                    f"MAX({col_esc}) as max_{m}"
                ])

            sql = f"SELECT {', '.join(select_clauses)} FROM read_parquet('{path_str}')"
            try:
                res = DuckDBEngine.query(sql)
                if res:
                    r = res[0]
                    for m in measures[:5]:
                        kpis["metrics"][m] = {
                            "sum": round(float(r[f"sum_{m}"]), 2) if r.get(f"sum_{m}") is not None else 0,
                            "avg": round(float(r[f"avg_{m}"]), 2) if r.get(f"avg_{m}") is not None else 0,
                            "min": round(float(r[f"min_{m}"]), 2) if r.get(f"min_{m}") is not None else 0,
                            "max": round(float(r[f"max_{m}"]), 2) if r.get(f"max_{m}") is not None else 0,
                        }
            except Exception as e:
                kpis["metrics_error"] = str(e)

        return kpis

    @staticmethod
    def get_time_series_trend(
        parquet_path: Path,
        temporal_col: str,
        measure_col: str,
        agg_func: str = "SUM"
    ) -> List[Dict[str, Any]]:
        path_str = str(parquet_path).replace("\\", "/")
        t_esc = f'"{temporal_col}"'
        m_esc = f'"{measure_col}"'
        agg = agg_func.upper() if agg_func.upper() in ["SUM", "AVG", "MIN", "MAX", "COUNT"] else "SUM"

        sql = f"""
        SELECT
            CAST({t_esc} AS VARCHAR) as period,
            {agg}({m_esc}) as value
        FROM read_parquet('{path_str}')
        WHERE {t_esc} IS NOT NULL 
          AND TRIM(CAST({t_esc} AS VARCHAR)) != '' 
          AND LOWER(TRIM(CAST({t_esc} AS VARCHAR))) NOT IN ('none', 'null', 'nan', 'nat')
        GROUP BY CAST({t_esc} AS VARCHAR)
        ORDER BY period ASC
        """
        try:
            res = DuckDBEngine.query(sql)
            rows = [
                {
                    "period": str(r.get("period", "")),
                    "value": round(float(r.get("value", 0) or 0), 2),
                }
                for r in res
            ]
            logger.info("[Analytics] Time-series query returned %d rows for %s by %s", len(rows), measure_col, temporal_col)
            return rows
        except Exception as exc:
            logger.error("[Analytics] Time-series query failed for %s by %s: %s", measure_col, temporal_col, exc)
            return []

    @staticmethod
    def get_dimension_breakdown(
        parquet_path: Path,
        dimension_col: str,
        measure_col: Optional[str] = None,
        agg_func: str = "SUM",
        top_n: int = 10
    ) -> List[Dict[str, Any]]:
        path_str = str(parquet_path).replace("\\", "/")
        d_esc = f'"{dimension_col}"'

        if measure_col:
            m_esc = f'"{measure_col}"'
            agg = agg_func.upper() if agg_func.upper() in ["SUM", "AVG", "MIN", "MAX", "COUNT"] else "SUM"
            val_expr = f"{agg}({m_esc})"
        else:
            val_expr = "COUNT(*)"

        sql = f"""
        SELECT
            CAST({d_esc} AS VARCHAR) as category,
            {val_expr} as value
        FROM read_parquet('{path_str}')
        WHERE {d_esc} IS NOT NULL
        GROUP BY category
        ORDER BY value DESC
        LIMIT {top_n}
        """
        res = DuckDBEngine.query(sql)
        return [{"category": str(r["category"]), "value": round(float(r["value"]), 2) if r.get("value") is not None else 0} for r in res]
