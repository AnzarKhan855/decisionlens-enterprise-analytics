from typing import Any, Dict, List

from app.semantic_model.core import Hierarchy


GEO_HIERARCHY_LEVELS = ["country", "state", "city", "zip", "region"]
ORG_HIERARCHY_LEVELS = ["department", "division", "team", "manager", "region"]
CATEGORY_HIERARCHY_LEVELS = ["category", "subcategory", "type", "group", "segment"]
TIME_HIERARCHY_LEVELS = ["year", "quarter", "month", "day", "hour"]

HIERARCHY_PATTERNS = {
    "Geography": GEO_HIERARCHY_LEVELS,
    "Organization": ORG_HIERARCHY_LEVELS,
    "Category": CATEGORY_HIERARCHY_LEVELS,
    "Time": TIME_HIERARCHY_LEVELS,
}


def detect_hierarchies(table_name: str, columns: List[str]) -> List[Hierarchy]:
    hierarchies = []
    col_lower = [c.lower() for c in columns]

    for hierarchy_type, keywords in HIERARCHY_PATTERNS.items():
        matched_cols = [c for c in col_lower if any(k in c for k in keywords)]
        if len(matched_cols) >= 2:
            hierarchies.append(Hierarchy(
                hierarchy_type=hierarchy_type,
                levels=matched_cols[:4],
                table=table_name,
                description=f"{hierarchy_type} rollup hierarchy across {len(matched_cols)} levels"
            ))

    return hierarchies