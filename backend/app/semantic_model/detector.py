from typing import Any, Dict, List, Optional

from app.semantic_model.core import TableRole, SpecializedTableType


LOOKUP_KEYWORDS = [
    "translation", "mapping", "codes", "zipcode", "lookup", "ref_",
    "reference", "currency", "category_name", "dictionary", "code_list",
    "ref_name"
]

LOOKUP_COLUMN_KEYWORDS = [
    "translation", "english", "category_name_english"
]

METADATA_KEYWORDS = ["metadata", "schema", "data_dict", "sys_log"]

REFERENCE_KEYWORDS = ["geolocation", "zipcode", "postcode", "geo_code"]

FACT_KEYWORDS = [
    "transactions", "invoices", "payments", "reviews", "logs", "events",
    "records", "entries", "measurements", "observations", "samples"
]

DIMENSION_KEYWORDS = [
    "user", "account", "employee",
    "patient", "doctor", "member", "subject", "device", "asset", "account"
]

from app.semantic_model.measure_detector import MEASURE_AGGREGATION_MAP as _MEASURE_AGGREGATION_MAP

_MEASURE_KEYWORDS = set(_MEASURE_AGGREGATION_MAP.get("sum", []) + _MEASURE_AGGREGATION_MAP.get("avg", []))

SPECIALIZED_TABLE_RULES = {
    SpecializedTableType.EMPLOYEE_TABLE: {
        "keywords": ["employee", "staff", "hr", "workforce"],
        "columns_required": ["employee_id", "department", "salary"]
    },
    SpecializedTableType.GEOGRAPHIC_TABLE: {
        "keywords": ["geolocation", "zipcode", "postcode", "geo", "location"],
        "columns_required": ["zip_code", "city", "state", "lat", "lng"]
    },
    SpecializedTableType.TIME_TABLE: {
        "keywords": ["calendar", "date", "time", "period"],
        "columns_required": ["date", "day", "month", "year"]
    }
}


def classify_table(
    table_name: str,
    columns: List[str],
    row_count: int,
    measures: List[str]
) -> Dict[str, Any]:
    name_lower = table_name.lower().replace("-", "_")
    col_lower = [c.lower() for c in columns]
    measures_lower = [m.lower() for m in measures]

    # 1. Lookup Table Detection
    is_lookup_by_name = any(kw in name_lower for kw in LOOKUP_KEYWORDS)
    is_lookup_by_cols = any(any(kw in c for kw in LOOKUP_COLUMN_KEYWORDS) for c in col_lower)
    is_product_category_lookup = "product_category_name" in col_lower and len(columns) <= 4

    if is_lookup_by_name or is_lookup_by_cols or is_product_category_lookup:
        return {
            "role": TableRole.LOOKUP.value,
            "is_fact": False,
            "is_analytical": False,
            "is_lookup": True,
            "description": "Reference translation or mapping table used to enrich dimensions.",
            "reason": f"Table '{table_name}' contains lookup mapping data ({len(columns)} columns, {row_count:,} rows)."
        }

    # 2. Metadata / System Table Detection
    if any(kw in name_lower for kw in METADATA_KEYWORDS):
        return {
            "role": TableRole.METADATA.value,
            "is_fact": False,
            "is_analytical": False,
            "is_lookup": False,
            "description": "System or dataset documentation table.",
            "reason": f"Table '{table_name}' contains system metadata."
        }

    # 3. Reference / Geo Table Detection
    if any(kw in name_lower for kw in REFERENCE_KEYWORDS):
        return {
            "role": TableRole.REFERENCE.value,
            "is_fact": False,
            "is_analytical": False,
            "is_lookup": True,
            "description": "Geographic reference master data.",
            "reason": f"Table '{table_name}' contains location reference coordinates."
        }

    # 4. Bridge Table Detection (junction between two entities without measures)
    id_cols = [c for c in col_lower if c.endswith("_id") or c == "id"]
    has_multiple_fk_cols = len(id_cols) >= 2
    no_measures = len(measures) == 0 and not any(m in col_lower for m in _MEASURE_KEYWORDS)
    is_bridge_candidate = has_multiple_fk_cols and len(columns) <= len(id_cols) + 2 and no_measures

    if is_bridge_candidate:
        return {
            "role": TableRole.BRIDGE.value,
            "is_fact": False,
            "is_analytical": False,
            "is_lookup": False,
            "description": "Junction table representing many-to-many relationships.",
            "reason": f"Table '{table_name}' bridges keys ({', '.join(id_cols)})."
        }

    # 5. Fact Table Detection
    has_measure_col = any(any(m in col for m in _MEASURE_KEYWORDS) for col in col_lower) or len(measures) > 0
    is_fact_by_name = any(kw in name_lower for kw in FACT_KEYWORDS)

    if is_fact_by_name or (has_measure_col and not any(kw in name_lower for kw in DIMENSION_KEYWORDS)):
        return {
            "role": TableRole.FACT.value,
            "is_fact": True,
            "is_analytical": True,
            "is_lookup": False,
            "description": "Primary transactional fact dataset containing business metrics.",
            "reason": f"Table '{table_name}' contains transactional records ({row_count:,} rows)."
        }

    # 6. Dimension Table Detection
    has_entity_id = any(col.endswith("_id") or col == "id" for col in col_lower) and not any(
        any(kw in col for kw in ["order_id", "transaction_id", "event_id", "payment_id", "record_id"]) for col in col_lower
    )
    is_dim_by_name = any(kw in name_lower for kw in DIMENSION_KEYWORDS)

    if is_dim_by_name or (has_entity_id and not has_measure_col):
        return {
            "role": TableRole.DIMENSION.value,
            "is_fact": False,
            "is_analytical": True,
            "is_lookup": False,
            "description": "Master entity dimension providing descriptive attributes.",
            "reason": f"Table '{table_name}' contains master entity attributes ({row_count:,} records)."
        }

    # 7. Default Fact Table fallback
    return {
        "role": TableRole.FACT.value,
        "is_fact": True,
        "is_analytical": True,
        "is_lookup": False,
        "description": "Primary transactional fact dataset containing business metrics.",
        "reason": f"Table '{table_name}' contains transactional records ({row_count:,} rows)."
    }


def detect_specialized_table_type(
    table_name: str,
    columns: List[str],
    measures: List[str],
    row_count: int
) -> Optional[SpecializedTableType]:
    name_lower = table_name.lower()
    col_lower = [c.lower() for c in columns]
    measures_lower = [m.lower() for m in measures]

    for special_type, rules in SPECIALIZED_TABLE_RULES.items():
        keywords = rules.get("keywords", [])
        if not any(k in name_lower for k in keywords):
            continue

        required_columns = [c.lower() for c in rules.get("columns_required", [])]
        if required_columns:
            if any(any(rq in cl for cl in col_lower) for rq in required_columns):
                return special_type
        else:
            if rules.get("measure_required"):
                if measures:
                    return special_type
            else:
                return special_type

    return None