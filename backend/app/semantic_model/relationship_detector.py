from typing import Any, Dict, List, Optional

from app.semantic_model.core import Relationship, RelationshipCardinality


def _is_join_key(col_name: str) -> bool:
    col_lower = col_name.lower()
    return (
        col_lower.endswith("_id") or
        col_lower == "id" or
        col_lower == "product_category_name" or
        "category" in col_lower
    )


def discover_relationships(
    con: Any,
    tables_meta: List[Dict[str, Any]],
    max_tables: int = 200
) -> List[Relationship]:
    relationships = []
    if len(tables_meta) < 2:
        return relationships

    limited_tables = tables_meta
    if len(tables_meta) > max_tables:
        limited_tables = sorted(
            tables_meta, key=lambda t: t.get("row_count", 0), reverse=True
        )[:max_tables]

    col_name_index: Dict[str, List[str]] = {}
    for t in limited_tables:
        t_name = t["table_name"]
        for c in t.get("columns", []):
            c_name = c["name"]
            if _is_join_key(c_name):
                col_name_index.setdefault(c_name, []).append(t_name)

    verified_columns = set()
    for col_name, table_names in col_name_index.items():
        if len(table_names) < 2:
            continue
        t1 = table_names[0]
        t2 = table_names[1]
        try:
            overlap_query = (
                f'SELECT COUNT(DISTINCT a."{col_name}") as common_cnt '
                f'FROM "{t1}" a '
                f'JOIN "{t2}" b ON CAST(a."{col_name}" AS VARCHAR) = CAST(b."{col_name}" AS VARCHAR)'
            )
            res = con.execute(overlap_query).fetchone()
            common_cnt = res[0] if res else 0
            if common_cnt > 0:
                verified_columns.add(col_name)
        except Exception:
            pass

    seen_pairs = set()
    for col_name in verified_columns:
        table_names = col_name_index[col_name]
        for idx in range(len(table_names)):
            for jdx in range(len(table_names)):
                if idx == jdx:
                    continue
                t1 = table_names[idx]
                t2 = table_names[jdx]
                pair_key = tuple(sorted([f"{t1}.{col_name}", f"{t2}.{col_name}"]))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                confidence = 90
                if "translation" in t2.lower() or "translation" in t1.lower():
                    confidence = 85

                cardinality = (
                    RelationshipCardinality.MANY_TO_ONE.value
                    if "translation" in t2.lower() or "translation" in t1.lower()
                    else RelationshipCardinality.ONE_TO_MANY.value
                )

                relationships.append(Relationship(
                    from_table=t1,
                    from_column=col_name,
                    to_table=t2,
                    to_column=col_name,
                    cardinality=cardinality,
                    confidence_score=confidence,
                    status="ACTIVE_JOIN",
                    relationship_type="foreign_key"
                ))

    return relationships


def clear_relationship_cache():
    pass