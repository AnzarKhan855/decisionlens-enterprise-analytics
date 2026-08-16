from pathlib import Path
from typing import Any, Dict

from app.database.duckdb_engine import DuckDBEngine
from app.ingestion.semantic_profiler import SemanticDataProfiler


class DataValidator:
    """
    Validates Parquet datasets via DuckDB to assess missing values, empty strings,
    numeric anomalies, and compute an overall dataset Health Score (0-100).
    """

    @staticmethod
    def validate(parquet_path: Path) -> Dict[str, Any]:
        profile = SemanticDataProfiler.profile(parquet_path)
        total_rows = profile["total_rows"]

        health_score = 100
        issues = []

        missing_summary = {}
        negative_summary = {}
        empty_string_summary = {}

        for col_name, meta in profile["columns"].items():
            null_pct = meta["null_percentage"]
            null_cnt = meta["null_count"]
            missing_summary[col_name] = null_cnt

            if null_pct > 50:
                health_score -= 15
                issues.append(f"Column '{col_name}' has >50% missing values ({null_pct}%).")
            elif null_pct > 20:
                health_score -= 5

            # Check numeric negatives if measure
            if meta["category"] == "measure" and "stats" in meta:
                min_val = meta["stats"].get("min")
                if min_val is not None and min_val < 0:
                    col_esc = f'"{col_name}"'
                    path_str = str(parquet_path).replace("\\", "/")
                    sql = f"SELECT COUNT(*) as neg_cnt FROM read_parquet('{path_str}') WHERE {col_esc} < 0"
                    neg_cnt = int(DuckDBEngine.query(sql)[0]["neg_cnt"])
                    if neg_cnt > 0:
                        negative_summary[col_name] = neg_cnt
                        health_score -= 5
                        issues.append(f"Measure '{col_name}' contains {neg_cnt} negative values.")

            # Check empty strings if dimension
            if meta["category"] in ["dimension", "identifier"] and "VARCHAR" in meta["data_type"].upper():
                col_esc = f'"{col_name}"'
                path_str = str(parquet_path).replace("\\", "/")
                sql = f"SELECT COUNT(*) as empty_cnt FROM read_parquet('{path_str}') WHERE TRIM({col_esc}) = ''"
                empty_cnt = int(DuckDBEngine.query(sql)[0]["empty_cnt"])
                if empty_cnt > 0:
                    empty_string_summary[col_name] = empty_cnt
                    health_score -= 3

        health_score = max(0, min(100, health_score))

        return {
            "health_score": health_score,
            "total_rows": total_rows,
            "missing_values": missing_summary,
            "negative_numeric_values": negative_summary,
            "empty_strings": empty_string_summary,
            "issues": issues,
            "semantic_profile": profile
        }
