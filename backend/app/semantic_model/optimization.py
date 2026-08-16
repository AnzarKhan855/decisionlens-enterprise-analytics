from typing import Any, Dict, List, Optional

from app.semantic_model.core import SemanticModel


MAX_PARQUET_FILES_FOR_FULL_PROFILE = 500
MAX_COLUMNS_FOR_PROFILE = 20
PARALLEL_WORKERS = 4
CHUNK_SIZE_ROWS = 100000


def optimize_for_scale(
    tables_meta: List[Dict[str, Any]],
    total_tables: int
) -> Dict[str, Any]:
    optimizations = {
        "parallel_profiling_enabled": total_tables > 10,
        "chunked_reading_enabled": True,
        "column_profile_cap": MAX_COLUMNS_FOR_PROFILE,
        "relationship_discovery_limit": min(total_tables, 200),
        "glossary_term_limit": 50,
        "lineage_node_limit": 500,
    }

    if total_tables > MAX_PARQUET_FILES_FOR_FULL_PROFILE:
        optimizations["profiling_strategy"] = "sampled"
        optimizations["sample_ratio"] = 0.1
    else:
        optimizations["profiling_strategy"] = "full"

    large_tables = [
        t for t in tables_meta
        if t.get("row_count", 0) > 1_000_000
    ]
    if large_tables:
        optimizations["large_table_count"] = len(large_tables)
        optimizations["large_table_strategy"] = "lazy_load_with_column_projection"

    return optimizations


def get_optimized_table_list(
    tables_meta: List[Dict[str, Any]],
    max_tables: int = 200
) -> List[Dict[str, Any]]:
    if len(tables_meta) <= max_tables:
        return tables_meta
    return sorted(
        tables_meta, key=lambda t: t.get("row_count", 0), reverse=True
    )[:max_tables]


def estimate_memory_footprint(tables_meta: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_rows = sum(t.get("row_count", 0) for t in tables_meta)
    total_columns = sum(len(t.get("columns", [])) for t in tables_meta)
    total_relationships = 0

    return {
        "estimated_total_rows": total_rows,
        "estimated_total_columns": total_columns,
        "estimated_relationships": total_relationships,
        "memory_profile": "large" if total_rows > 10_000_000 else "medium" if total_rows > 1_000_000 else "standard",
    }