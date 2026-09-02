from pathlib import Path
from typing import Any, Dict, List, Optional
import math
import duckdb

from app.database.duckdb_engine import DuckDBEngine, _validate_parquet_path
from app.ingestion.semantic_profiler import SemanticDataProfiler
from app.logging.logger import get_logger
logger = get_logger(__name__)


class ChartEngine:
    """
    Universal Automatic AI Visualization Engine.
    Inspects column data types and cardinality to automatically generate all feasible visualizations.
    """

    _CHART_CACHE: Dict[str, List[Dict[str, Any]]] = {}

    @classmethod
    def generate_from_parquet(cls, parquet_path: Path, semantic_profile: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        try:
            mtime = parquet_path.stat().st_mtime
        except Exception:
            mtime = 0
        cache_key = f"{parquet_path}_{mtime}"
        if cache_key in cls._CHART_CACHE:
            return cls._CHART_CACHE[cache_key]

        path_str = _validate_parquet_path(parquet_path)
        con = DuckDBEngine.get_connection()
        try:
            schema_rows = con.execute("DESCRIBE SELECT * FROM read_parquet(?)", [path_str]).fetchall()
            schema = {r[0]: r[1] for r in schema_rows}

            NUMERIC_TYPES = {"BIGINT", "INTEGER", "SMALLINT", "TINYINT", "DOUBLE", "FLOAT", "DECIMAL", "HUGEINT", "REAL"}
            DATE_TYPES = {"DATE", "TIMESTAMP", "TIMESTAMPTZ"}

            measures = []
            dimensions = []
            temporal = []
            categorical_cols = []

            for col, dtype in schema.items():
                dtype_up = str(dtype).upper().split("(")[0]
                col_lower = col.lower()

                if dtype_up in DATE_TYPES or any(k in col_lower for k in ["date", "timestamp", "time", "year", "month"]):
                    temporal.append(col)
                elif dtype_up in NUMERIC_TYPES and not any(k in col_lower for k in ["_id", "row_id", "index"]):
                    measures.append(col)
                elif any(k in col_lower for k in ["status", "type", "mode", "category", "segment", "class"]):
                    categorical_cols.append(col)
                elif not any(k in col_lower for k in ["_id", "row_id", "index"]):
                    dimensions.append(col)

            charts = []
            primary_measure = measures[0] if measures else None
            m_esc = f'"{primary_measure}"' if primary_measure else "COUNT(*)"

            # Chart 1: Time-series trend
            if temporal and primary_measure:
                t_col = temporal[0]
                try:
                    sql = f"""
                    SELECT
                        STRFTIME(CAST("{t_col}" AS TIMESTAMP), '%Y-%m') as period,
                        SUM({m_esc}) as value
                    FROM read_parquet('{path_str}')
                    WHERE "{t_col}" IS NOT NULL
                    GROUP BY period
                    ORDER BY period ASC
                    LIMIT 24
                    """
                    rows = con.execute(sql).fetchall()
                    if rows:
                        data = []
                        for r in rows:
                            if r[0]:
                                try:
                                    val = float(r[1] or 0)
                                    if not math.isnan(val) and not math.isinf(val):
                                        cat_str = str(r[0])
                                        data.append({
                                            "x_field": cat_str,
                                            "y_field": round(val, 2),
                                            "label": cat_str,
                                            "value": round(val, 2),
                                            "period": cat_str,
                                            "category": cat_str,
                                            "frequency": round(val, 2),
                                        })
                                except (TypeError, ValueError):
                                    continue
                        if data:
                            charts.append({
                                "id": "time_series_trend",
                                "type": "area",
                                "title": f"Time-Series Trend: {primary_measure.replace('_', ' ').title()}",
                                "available": True,
                                "x_axis": "period",
                                "y_axis": "value",
                                "x_field": "period",
                                "y_field": "value",
                                "source_column": primary_measure,
                                "dimension_column": t_col,
                                "data": data,
                                "business_interpretation": f"Tracks {primary_measure.replace('_', ' ').title()} over time to identify seasonal patterns and forecast future values.",
                                "confidence": 0.92,
                                "evidence": f"DuckDB temporal aggregation on {t_col}",
                            })
                except Exception as e:
                    logger.warning(f"[ChartEngine TS Warning] {e}")

            # Chart 2: Top categories / dimensions breakdown
            target_dims = categorical_cols or dimensions
            if target_dims and primary_measure:
                d_col = target_dims[0]
                try:
                    sql = f"""
                    SELECT CAST("{d_col}" AS VARCHAR) as cat, SUM({m_esc}) as value
                    FROM read_parquet('{path_str}')
                    WHERE "{d_col}" IS NOT NULL
                    GROUP BY 1
                    ORDER BY value DESC
                    LIMIT 10
                    """
                    rows = con.execute(sql).fetchall()
                    if rows:
                        data = []
                        for r in rows:
                            if r[0]:
                                try:
                                    val = float(r[1] or 0)
                                    if not math.isnan(val) and not math.isinf(val):
                                        cat_str = str(r[0])[:24]
                                        data.append({
                                            "x_field": cat_str,
                                            "y_field": round(val, 2),
                                            "label": cat_str,
                                            "value": round(val, 2),
                                            "category": cat_str,
                                            "period": cat_str,
                                            "frequency": round(val, 2),
                                        })
                                except (TypeError, ValueError):
                                    continue
                        if data:
                            charts.append({
                                "id": "primary_dimension_breakdown",
                                "type": "bar",
                                "title": f"Top {d_col.replace('_', ' ').title()}s by {primary_measure.replace('_', ' ').title()}",
                                "available": True,
                                "x_axis": "category",
                                "y_axis": "value",
                                "x_field": "category",
                                "y_field": "value",
                                "source_column": primary_measure,
                                "dimension_column": d_col,
                                "data": data,
                                "business_interpretation": f"Identifies the highest-performing {d_col.replace('_', ' ').title()} segments by {primary_measure.replace('_', ' ').title()}.",
                                "confidence": 0.90,
                                "evidence": f"DuckDB GROUP BY aggregation on {d_col}",
                            })
                except Exception as e:
                    logger.warning(f"[ChartEngine Dim Warning] {e}")

            # Chart 3: Secondary dimension / record count breakdown
            if len(target_dims) > 1 and primary_measure:
                d_col2 = target_dims[1]
                try:
                    sql = f"""
                    SELECT CAST("{d_col2}" AS VARCHAR) as cat, COUNT(*) as frequency
                    FROM read_parquet('{path_str}')
                    WHERE "{d_col2}" IS NOT NULL
                    GROUP BY 1
                    ORDER BY frequency DESC
                    LIMIT 8
                    """
                    rows = con.execute(sql).fetchall()
                    if rows:
                        data = []
                        for r in rows:
                            if r[0]:
                                try:
                                    val = float(r[1] or 0)
                                    if not math.isnan(val) and not math.isinf(val):
                                        cat_str = str(r[0])[:24]
                                        data.append({
                                            "x_field": cat_str,
                                            "y_field": round(val, 2),
                                            "label": cat_str,
                                            "value": round(val, 2),
                                            "category": cat_str,
                                            "period": cat_str,
                                            "frequency": round(val, 2),
                                        })
                                except (TypeError, ValueError):
                                    continue
                        if data:
                            charts.append({
                                "id": "secondary_dimension_breakdown",
                                "type": "horizontal_bar",
                                "title": f"Record Count by {d_col2.replace('_', ' ').title()}",
                                "available": True,
                                "x_axis": "category",
                                "y_axis": "value",
                                "x_field": "category",
                                "y_field": "value",
                                "source_column": primary_measure,
                                "dimension_column": d_col2,
                                "data": data,
                                "business_interpretation": f"Shows distribution density across {d_col2.replace('_', ' ').title()} segments.",
                                "confidence": 0.88,
                                "evidence": f"DuckDB COUNT(*) GROUP BY {d_col2}",
                            })
                except Exception as e:
                    logger.warning(f"[ChartEngine Dim2 Warning] {e}")

            # Chart 4: Secondary measure breakdown
            if len(measures) > 1 and target_dims:
                sec_measure = measures[1]
                d_col = target_dims[0]
                try:
                    sql = f"""
                    SELECT CAST("{d_col}" AS VARCHAR) as cat, SUM("{sec_measure}") as value
                    FROM read_parquet('{path_str}')
                    WHERE "{d_col}" IS NOT NULL
                    GROUP BY 1
                    ORDER BY value DESC
                    LIMIT 8
                    """
                    rows = con.execute(sql).fetchall()
                    if rows:
                        data = []
                        for r in rows:
                            if r[0]:
                                try:
                                    val = float(r[1] or 0)
                                    if not math.isnan(val) and not math.isinf(val):
                                        cat_str = str(r[0])[:24]
                                        data.append({
                                            "x_field": cat_str,
                                            "y_field": round(val, 2),
                                            "label": cat_str,
                                            "value": round(val, 2),
                                            "category": cat_str,
                                            "period": cat_str,
                                            "frequency": round(val, 2),
                                        })
                                except (TypeError, ValueError):
                                    continue
                        if data:
                            charts.append({
                                "id": "secondary_measure_breakdown",
                                "type": "bar",
                                "title": f"{sec_measure.replace('_', ' ').title()} by {d_col.replace('_', ' ').title()}",
                                "available": True,
                                "x_axis": "category",
                                "y_axis": "value",
                                "x_field": "category",
                                "y_field": "value",
                                "source_column": sec_measure,
                                "dimension_column": d_col,
                                "data": data,
                                "business_interpretation": f"Compares secondary metric {sec_measure.replace('_', ' ').title()} across {d_col.replace('_', ' ').title()} segments.",
                                "confidence": 0.88,
                                "evidence": f"DuckDB SUM({sec_measure}) GROUP BY {d_col}",
                            })
                except Exception as e:
                    logger.warning(f"[ChartEngine SecMeasure Warning] {e}")

            # Chart 5: Categorical / status distribution
            if categorical_cols and primary_measure:
                target_status = categorical_cols[0]
                try:
                    sql = f"""
                    SELECT CAST("{target_status}" AS VARCHAR) as cat, SUM({m_esc}) as value
                    FROM read_parquet('{path_str}')
                    WHERE "{target_status}" IS NOT NULL
                    GROUP BY 1
                    ORDER BY value DESC
                    LIMIT 6
                    """
                    rows = con.execute(sql).fetchall()
                    if rows:
                        data = []
                        for r in rows:
                            if r[0]:
                                try:
                                    val = float(r[1] or 0)
                                    if not math.isnan(val) and not math.isinf(val):
                                        cat_str = str(r[0])[:24]
                                        data.append({
                                            "x_field": cat_str,
                                            "y_field": round(val, 2),
                                            "label": cat_str,
                                            "value": round(val, 2),
                                            "category": cat_str,
                                            "period": cat_str,
                                            "frequency": round(val, 2),
                                        })
                                except (TypeError, ValueError):
                                    continue
                        if data:
                            charts.append({
                                "id": "status_distribution",
                                "type": "pie",
                                "title": f"Distribution by {target_status.replace('_', ' ').title()}",
                                "available": True,
                                "x_axis": "category",
                                "y_axis": "value",
                                "x_field": "category",
                                "y_field": "value",
                                "source_column": primary_measure,
                                "dimension_column": target_status,
                                "data": data,
                                "business_interpretation": f"Proportional breakdown of {primary_measure.replace('_', ' ').title()} across {target_status.replace('_', ' ').title()} states.",
                                "confidence": 0.85,
                                "evidence": f"DuckDB PIE GROUP BY {target_status}",
                            })
                except Exception as e:
                    logger.warning(f"[ChartEngine Pie Warning] {e}")

        except Exception as e:
            logger.error(f"[ChartEngine Global Exception] {e}")
        finally:
            con.close()

        cls._CHART_CACHE[cache_key] = charts
        return charts
