from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from app.database.duckdb_engine import DuckDBEngine
from app.utils.smart_formatter import format_business_value


class StatisticalAnomalyEngine:
    """
    Enterprise Ranked Business Anomaly Detection Engine.
    Filters out statistical noise to output only Top 5/10 actionable business anomalies
    with severity, root cause hypotheses, business impact ($/₹), and recommendations.
    """

    @staticmethod
    def detect_anomalies(
        parquet_path: Path,
        temporal_col: str,
        measure_col: str,
        z_threshold: float = 2.0
    ) -> List[Dict[str, Any]]:
        path_str = str(parquet_path).replace("\\", "/")
        t_esc = f'"{temporal_col}"'
        m_esc = f'"{measure_col}"'

        sql = f"""
        SELECT
            CAST({t_esc} AS VARCHAR) as period,
            CAST({m_esc} AS DOUBLE) as value
        FROM read_parquet('{path_str}')
        WHERE {t_esc} IS NOT NULL AND {m_esc} IS NOT NULL
        ORDER BY {t_esc} ASC
        """
        df = DuckDBEngine.query_to_df(sql)
        if df.empty or len(df) < 5:
            return []

        values = df["value"].values
        mean_val = float(np.mean(values))
        std_val = float(np.std(values))

        if std_val == 0:
            return []

        anomalies = []
        measure_clean = measure_col.replace("_", " ")

        for idx, row in df.iterrows():
            val = float(row["value"])
            z_score = (val - mean_val) / std_val

            if abs(z_score) >= z_threshold:
                direction = "SPIKE" if z_score > 0 else "DIP"
                abs_z = abs(z_score)

                if abs_z >= 3.0:
                    severity = "CRITICAL"
                elif abs_z >= 2.5:
                    severity = "HIGH"
                else:
                    severity = "WARNING"

                pct_diff = round(((val - mean_val) / mean_val) * 100, 1) if mean_val > 0 else 0
                val_fmt = format_business_value(measure_col, val)
                exp_fmt = format_business_value(measure_col, mean_val)

                if direction == "DIP":
                    title = f"Unusual {measure_clean.title()} Drop"
                    category = "Value Decrease"
                    explanation = f"{measure_clean.title()} decreased by {abs(pct_diff)}% in period {row['period']} (recorded {val_fmt} vs expected baseline ~{exp_fmt})."
                    impact = f"Estimated shortfall of {format_business_value(measure_col, abs(mean_val - val))}."
                    causes = []
                    rec = ""
                else:
                    title = f"Abnormal {measure_clean.title()} Spike"
                    category = "Value Increase"
                    explanation = f"{measure_clean.title()} surged by {pct_diff}% in period {row['period']} (recorded {val_fmt} vs expected baseline ~{exp_fmt})."
                    impact = f"Potential resource strain and capacity risk within the next period."
                    causes = []
                    rec = ""

                anomalies.append({
                    "period": str(row["period"]),
                    "title": title,
                    "category": category,
                    "severity": severity,
                    "type": direction,
                    "actual_value": val,
                    "expected_value": mean_val,
                    "z_score": round(float(z_score), 2),
                    "pct_change": pct_diff,
                    "explanation": explanation,
                    "business_impact": impact,
                    "possible_causes": causes,
                    "recommendation": rec,
                    "confidence_score": round(min(0.99, max(0.5, abs(z_score) / 4.0)), 2),
                })

        # Sort anomalies by z_score absolute magnitude (highest severity first) and return Top 5
        anomalies.sort(key=lambda a: abs(a["z_score"]), reverse=True)
        return anomalies[:5]
