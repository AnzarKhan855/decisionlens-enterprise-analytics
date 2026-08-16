from typing import Any, Dict, List

from app.semantic_model.core import PrimaryKey


RETAIL_PRIMARY_KEY_ALIASES = {
    "order_id": ["invoice", "invoice_no", "invoice_id", "orderid", "order_id",
                 "order_no", "order_number", "order_code", "bill_no", "bill_id",
                 "receipt", "receipt_no", "receipt_id", "transaction_id",
                 "transaction_no", "sales_order", "order_uuid", "txn_id",
                 "payment_id", "checkout_id", "confirmation_number"],
    "product_id": ["stockcode", "stock_code", "sku", "product_id", "product_code",
                   "item_id", "item_code", "item_no", "item_number", "product",
                   "product_no", "upc", "ean", "barcode", "merchandise_code"],
    "customer_id": ["customer_id", "customerid", "customer_no", "customer_code",
                    "client_id", "client_code", "buyer_id", "user_id", "account_id",
                    "member_id", "patron_id", "shopper_id"],
}


def detect_primary_keys(
    table_name: str,
    columns: List[Dict[str, Any]],
    profile: Dict[str, Any]
) -> List[PrimaryKey]:
    pks = []
    col_map = {c["name"]: c for c in columns}
    col_lower_map = {c["name"].lower(): c["name"] for c in columns}
    columns_lower = [c["name"].lower() for c in columns]

    for c in columns:
        cname = c["name"].lower()
        ctype = c.get("type", "").lower()

        is_id = (
            cname == "id" or
            cname.endswith("_id") or
            cname.endswith("_key") or
            "id" in col_map.get(c["name"], {}).get("type", "").lower()
        )
        is_retail_key = False
        retail_key_type = None
        for key_type, aliases in RETAIL_PRIMARY_KEY_ALIASES.items():
            for alias in aliases:
                if alias == cname or cname.endswith("_" + alias) or alias + "_" in cname:
                    is_retail_key = True
                    retail_key_type = key_type
                    break
            if is_retail_key:
                break

        if not is_id and not is_retail_key:
            continue

        col_profile = profile.get("columns", {}).get(c["name"], {})
        distinct_count = col_profile.get("distinct_count", 0)
        null_count = col_profile.get("null_count", 0)
        total_rows = profile.get("total_rows", 1)
        uniqueness = distinct_count / max(total_rows, 1)
        null_rate = null_count / max(total_rows, 1)

        confidence = 0.5
        if cname == "id" or cname.endswith("_id"):
            confidence += 0.2
        if is_retail_key:
            confidence += 0.15
        if uniqueness > 0.95:
            confidence += 0.25
        if null_rate < 0.01:
            confidence += 0.15
        if ctype in ("integer", "bigint", "uuid", "varchar"):
            confidence += 0.1

        confidence = min(0.99, confidence)

        if confidence >= 0.6:
            pks.append(PrimaryKey(
                table=table_name,
                column=c["name"],
                data_type=c.get("type"),
                confidence=round(confidence, 2),
                uniqueness_ratio=round(uniqueness, 4),
                null_ratio=round(null_rate, 4),
                is_primary_key=True,
                is_candidate_key=True,
                detection_basis="naming_pattern+uniqueness+nullability+retail_alias"
            ))

    return pks


def detect_foreign_keys_from_relationships(
    relationships: List[Any],
    tables_meta: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    detected_fks = []
    for rel in relationships:
        detected_fks.append({
            "table": rel.from_table,
            "column": rel.from_column,
            "references_table": rel.to_table,
            "references_column": rel.to_column,
            "cardinality": rel.cardinality.value if hasattr(rel.cardinality, "value") else rel.cardinality,
            "confidence": rel.confidence_score,
            "status": "ACTIVE"
        })
    return detected_fks


def build_pk_lookup(tables_meta: List[Dict[str, Any]]) -> Dict[tuple, PrimaryKey]:
    pk_lookup = {}
    for t in tables_meta:
        for pk in t.get("primary_keys", []):
            pk_lookup[(t["table_name"], pk["column"])] = pk
    return pk_lookup