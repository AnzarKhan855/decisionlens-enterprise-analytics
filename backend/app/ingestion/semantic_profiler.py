from pathlib import Path
from typing import Any, Dict, List, Optional
import re
import time
import threading

from app.database.duckdb_engine import DuckDBEngine
from app.cache.memory_cache import TTLCache

_profile_cache = TTLCache(maxsize=128, ttl=600)

_profile_lock = threading.Lock()

class SemanticDataProfiler:
    """
    Domain-Agnostic Semantic Profiler & Intelligence Layer with
    batched DuckDB queries and TTL-based caching for sub-second profiling.
    """

    ID_KEYWORDS = {
        "id", "uuid", "guid", "code", "number", "no", "index", "key", "pk", "fk",
        "invoiceno", "stockcode", "customerid", "orderid", "transid", "sku", "receiptno"
    }
    DATE_KEYWORDS = {"date", "time", "timestamp", "year", "month", "day", "quarter", "dt", "created", "updated"}

    IDENTIFIER_SUFFIXES = {"_id", "id", "no", "code", "sku", "uuid", "key"}

    @staticmethod
    def classify_table(filename: str, total_rows: int, measures: List[str], dimensions: List[str], columns: List[str]) -> Dict[str, Any]:
        fn_clean = filename.lower()
        if any(k in fn_clean for k in ["translation", "mapping", "codes", "zipcode", "lookup", "ref_", "reference", "currency"]):
            return {"table_type": "Lookup Table", "is_lookup": True, "purpose": "Descriptive Mapping", "explanation": "This dataset supports other datasets by providing descriptive mappings."}
        if len(measures) >= 2 or any(k in fn_clean for k in ["order", "payment", "transaction", "sale", "invoice", "item"]):
            return {"table_type": "Fact Table", "is_lookup": False, "purpose": "Core Business Operations & Metrics", "explanation": "Contains quantitative metrics, transactions, and performance data."}
        if any(k in fn_clean for k in ["customer", "product", "seller", "user", "employee", "account", "store"]):
            return {"table_type": "Dimension Table", "is_lookup": False, "purpose": "Entity Master Directory", "explanation": "Contains descriptive master entity profiles."}
        return {"table_type": "Dimension Table", "is_lookup": False, "purpose": "General Attribute Directory", "explanation": "Contains general descriptive attributes."}

    @classmethod
    def classify_column(cls, column_name: str, duckdb_type: str, total_rows: int, distinct_count: int, null_count: int) -> str:
        from app.semantic_model.measure_detector import MEASURE_AGGREGATION_MAP as _MEASURE_AGGREGATION_MAP
        _MEASURE_KEYWORDS = set(_MEASURE_AGGREGATION_MAP.get("sum", []) + _MEASURE_AGGREGATION_MAP.get("avg", []))

        col_clean = re.sub(r"[^a-z0-9]", "", column_name.lower())
        type_upper = duckdb_type.upper()
        if any(dt in type_upper for dt in ["DATE", "TIME", "TIMESTAMP"]):
            return "temporal"
        if any(kw in col_clean for kw in ["date", "timestamp", "datetime", "invoicedate", "orderdate"]):
            return "temporal"
        if any(col_clean.endswith(s) or s == col_clean for s in cls.IDENTIFIER_SUFFIXES):
            return "identifier"
        if any(kw in col_clean for kw in _MEASURE_KEYWORDS):
            return "measure"
        uniqueness_ratio = distinct_count / total_rows if total_rows > 0 else 0
        if uniqueness_ratio > 0.85:
            return "identifier"
        numeric_types = ["BIGINT", "INTEGER", "SMALLINT", "TINYINT", "DOUBLE", "FLOAT", "DECIMAL", "HUGEINT", "REAL"]
        if any(nt in type_upper for nt in numeric_types):
            if distinct_count <= 10 and not any(kw in col_clean for kw in _MEASURE_KEYWORDS):
                return "dimension"
            return "measure"
        return "dimension"

    @classmethod
    def profile(cls, parquet_path: Path) -> Dict[str, Any]:
        cache_key = str(parquet_path)
        cached = _profile_cache.get(cache_key)
        if cached is not None:
            return cached

        schema = DuckDBEngine.get_schema(parquet_path)
        total_rows = DuckDBEngine.get_row_count(parquet_path)

        path_str = str(parquet_path).replace("\\", "/")
        columns = list(schema.items())

        classified_columns = {"measures": [], "dimensions": [], "temporal": [], "identifiers": []}
        columns_profile = {}

        temporal_cols = [c[0] for c in columns if any(dt in c[1].upper() for dt in ["DATE", "TIME", "TIMESTAMP"])]
        numeric_cols = [c[0] for c in columns if any(nt in c[1].upper() for nt in ["BIGINT", "INTEGER", "SMALLINT", "TINYINT", "DOUBLE", "FLOAT", "DECIMAL", "HUGEINT", "REAL"])]
        other_cols = [c[0] for c in columns if c[0] not in temporal_cols and c[0] not in numeric_cols]

        def _safe_key(c: str) -> str:
            return re.sub(r'[^a-zA-Z0-9_]', '_', c)

        if temporal_cols:
            temporal_exprs = []
            for col in temporal_cols:
                col_esc = f'"{col}"'
                ck = _safe_key(col)
                temporal_exprs.append(f'COUNT(DISTINCT {col_esc}) as dist_{ck}, COUNT(*) - COUNT({col_esc}) as null_{ck}, MIN({col_esc}) as min_{ck}, MAX({col_esc}) as max_{ck}')
            sql = f"SELECT {', '.join(temporal_exprs)} FROM read_parquet('{path_str}')"
            row = DuckDBEngine.query(sql)[0]
            for col in temporal_cols:
                col_key = _safe_key(col)
                dist_cnt = row.get(f"dist_{col_key}", 0)
                null_cnt = row.get(f"null_{col_key}", 0)
                category = "temporal"
                columns_profile[col] = {"data_type": schema[col], "category": category, "distinct_count": dist_cnt, "null_count": null_cnt, "null_percentage": round((null_cnt / total_rows * 100), 2) if total_rows > 0 else 0, "min_date": str(row.get(f"min_{col_key}")), "max_date": str(row.get(f"max_{col_key}"))}
                classified_columns["temporal"].append(col)

        if numeric_cols:
            num_exprs = []
            for col in numeric_cols:
                col_esc = f'"{col}"'
                ck = _safe_key(col)
                num_exprs.append(f'COUNT({col_esc}) as cnt_{ck}, SUM({col_esc}) as sum_{ck}, COUNT(*) - COUNT({col_esc}) as null_{ck}, COUNT(DISTINCT {col_esc}) as dist_{ck}, MIN({col_esc}) as min_{ck}, MAX({col_esc}) as max_{ck}, AVG({col_esc}) as avg_{ck}, STDDEV_SAMP({col_esc}) as std_{ck}')
            if total_rows > 100000:
                sql = f"SELECT {', '.join(num_exprs)} FROM read_parquet('{path_str}') USING SAMPLE 50000"
            else:
                sql = f"SELECT {', '.join(num_exprs)} FROM read_parquet('{path_str}')"
            row = DuckDBEngine.query(sql)[0]
            for col in numeric_cols:
                col_key = _safe_key(col)
                dist_cnt = row.get(f"dist_{col_key}", 0)
                null_cnt = row.get(f"null_{col_key}", 0)
                category = cls.classify_column(col, schema[col], total_rows, dist_cnt, null_cnt)
                raw_sum = row.get(f"sum_{col_key}")
                col_sum = float(raw_sum) if raw_sum is not None else 0.0
                if abs(col_sum) < 1e-9:
                    col_sum = 0.0

                raw_mean = row.get(f"avg_{col_key}")
                col_mean = float(raw_mean) if raw_mean is not None else 0.0
                if abs(col_mean) < 1e-9:
                    col_mean = 0.0

                columns_profile[col] = {
                    "data_type": schema[col],
                    "category": category,
                    "distinct_count": dist_cnt,
                    "null_count": null_cnt,
                    "null_percentage": round((null_cnt / total_rows * 100), 2) if total_rows > 0 else 0,
                    "stats": {
                        "count": row.get(f"cnt_{col_key}", 0),
                        "sum": round(col_sum, 4),
                        "min": float(row.get(f"min_{col_key}")) if row.get(f"min_{col_key}") is not None else None,
                        "max": float(row.get(f"max_{col_key}")) if row.get(f"max_{col_key}") is not None else None,
                        "mean": round(col_mean, 4),
                        "stddev": round(float(row.get(f"std_{col_key}")), 4) if row.get(f"std_{col_key}") is not None else None,
                        "q25": float(row.get(f"q25_{col_key}")) if row.get(f"q25_{col_key}") is not None else None,
                        "median": float(row.get(f"med_{col_key}")) if row.get(f"med_{col_key}") is not None else None,
                        "q75": float(row.get(f"q75_{col_key}")) if row.get(f"q75_{col_key}") is not None else None,
                    }
                }
                key_map = {"measure": "measures", "dimension": "dimensions", "temporal": "temporal", "identifier": "identifiers"}
                classified_columns[key_map.get(category, "dimensions")].append(col)

        if other_cols:
            cat_exprs = []
            for col in other_cols:
                col_esc = f'"{col}"'
                ck = _safe_key(col)
                cat_exprs.append(f'COUNT(DISTINCT {col_esc}) as dist_{ck}, COUNT(*) - COUNT({col_esc}) as null_{ck}')
            sql = f"SELECT {', '.join(cat_exprs)} FROM read_parquet('{path_str}')"
            row = DuckDBEngine.query(sql)[0]
            for col in other_cols:
                col_key = _safe_key(col)
                dist_cnt = row.get(f"dist_{col_key}", 0)
                null_cnt = row.get(f"null_{col_key}", 0)
                category = cls.classify_column(col, schema[col], total_rows, dist_cnt, null_cnt)
                columns_profile[col] = {"data_type": schema[col], "category": category, "distinct_count": dist_cnt, "null_count": null_cnt, "null_percentage": round((null_cnt / total_rows * 100), 2) if total_rows > 0 else 0}
                key_map = {"measure": "measures", "dimension": "dimensions", "temporal": "temporal", "identifier": "identifiers"}
                classified_columns[key_map.get(category, "dimensions")].append(col)

        meaningful_dimensions = [d for d in classified_columns["dimensions"] if not any(id_kw in d.lower() for id_kw in ["id", "no", "num", "code", "sku"])]
        if not meaningful_dimensions:
            meaningful_dimensions = classified_columns["dimensions"]
        classified_columns["meaningful_dimensions"] = meaningful_dimensions

        # Apply retail semantic mapping if available
        retail_mapping = None
        try:
            from app.retail.retail_semantic_mapper import RetailSemanticMapper
            retail_mapping = RetailSemanticMapper.map({"columns": columns_profile, "total_rows": total_rows, "column_categories": classified_columns})
        except Exception:
            pass

        table_meta = cls.classify_table(parquet_path.name, total_rows, classified_columns["measures"], classified_columns["dimensions"], list(schema.keys()))

        preview = DuckDBEngine.preview(parquet_path, limit=10)

        measure_stats_dict = {
            col: col_prof["stats"] for col, col_prof in columns_profile.items() if "stats" in col_prof
        }

        res = {
            "total_rows": total_rows,
            "total_columns": len(schema),
            "table_meta": table_meta,
            "column_categories": classified_columns,
            "columns": columns_profile,
            "measure_stats": measure_stats_dict,
            "preview": preview,
            "retail_mapping": retail_mapping,
        }

        with _profile_lock:
            _profile_cache.set(cache_key, res, ttl=600)
        return res
