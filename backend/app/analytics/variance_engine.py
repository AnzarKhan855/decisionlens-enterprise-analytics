from pathlib import Path
from typing import Any, Dict, List, Optional

from app.database.duckdb_engine import DuckDBEngine


class VarianceDecompositionEngine:
    """
    Variance Decomposition & Driver Attribution Engine.
    Calculates top dimensional contributors to metric sums and identifies concentration risks (80/20 rule).
    """

    @staticmethod
    def analyze_drivers(
        parquet_path: Path,
        dimension_col: str,
        measure_col: str,
        top_n: int = 5
    ) -> Dict[str, Any]:
        path_str = str(parquet_path).replace("\\", "/")
        d_esc = f'"{dimension_col}"'
        m_esc = f'"{measure_col}"'

        sql_total = f"SELECT SUM({m_esc}) as grand_total FROM read_parquet('{path_str}') WHERE {m_esc} IS NOT NULL"
        tot_res = DuckDBEngine.query(sql_total)
        grand_total = float(tot_res[0]["grand_total"]) if tot_res and tot_res[0].get("grand_total") is not None else 0

        if grand_total == 0:
            return {"dimension": dimension_col, "measure": measure_col, "grand_total": 0, "drivers": []}

        sql_drivers = f"""
        SELECT
            CAST({d_esc} AS VARCHAR) as category,
            SUM({m_esc}) as category_total
        FROM read_parquet('{path_str}')
        WHERE {d_esc} IS NOT NULL AND {m_esc} IS NOT NULL
        GROUP BY 1
        ORDER BY category_total DESC
        LIMIT {top_n}
        """
        res = DuckDBEngine.query(sql_drivers)

        drivers = []
        cumulative_pct = 0.0

        for r in res:
            cat_sum = float(r["category_total"]) if r.get("category_total") is not None else 0
            pct = round((cat_sum / grand_total) * 100, 2)
            cumulative_pct += pct

            drivers.append({
                "category": str(r["category"]),
                "amount": round(cat_sum, 2),
                "contribution_percentage": pct,
                "cumulative_percentage": round(cumulative_pct, 2)
            })

        top_driver = drivers[0] if drivers else None
        has_concentration_risk = top_driver is not None and top_driver["contribution_percentage"] >= 40.0

        return {
            "dimension": dimension_col,
            "measure": measure_col,
            "grand_total": round(grand_total, 2),
            "top_driver": top_driver,
            "has_concentration_risk": has_concentration_risk,
            "drivers": drivers
        }
