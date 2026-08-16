from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.retail.retail_semantic_mapper import RetailSemanticMapper


RETAIL_ENTITY_KEYWORDS = {
    "Order": ["order", "orders", "transaction", "transactions", "sale", "sales", "purchase", "invoice", "receipt"],
    "Product": ["product", "products", "item", "items", "sku", "stock_code", "merchandise"],
    "Customer": ["customer", "customers", "client", "clients", "buyer", "buyers", "user", "account"],
    "Category": ["category", "categories", "segment", "segments", "department", "division"],
    "Revenue": ["revenue", "revenues", "sales_amount", "turnover", "gross_income", "total_amount", "amount"],
    "Price": ["price", "prices", "unit_price", "list_price", "selling_price", "cost_price"],
    "Freight": ["freight", "freight_value", "shipping", "delivery_charge", "postage", "carrier_charge", "transport", "shipping_cost"],
    "Discount": ["discount", "discounts", "promo", "promotion", "coupon", "markdown"],
    "Payment": ["payment", "payments", "settlement", "method", "payment_type", "pay_mode"],
    "Delivery": ["delivery", "deliveries", "shipment", "shipped", "fulfillment", "dispatch", "courier", "delivered"],
    "Quantity": ["quantity", "qty", "units", "order_item_id", "count", "volume"],
    "Inventory": ["inventory", "stock", "stocks", "in_stock", "available_qty", "warehouse"],
    "Store": ["store", "stores", "shop", "outlet", "branch", "location", "retail_location"],
    "Region": ["region", "regions", "state", "states", "province", "territory", "zone", "district"],
    "Country": ["country", "countries", "nation", "nationality"],
    "City": ["city", "cities", "town", "municipality", "locality"],
    "Review": ["review", "reviews", "rating", "ratings", "feedback", "score", "nps"],
    "Date": ["date", "time", "timestamp", "order_date", "created_at", "updated_at", "transaction_date", "invoice_date", "purchase_timestamp", "approved_at", "delivered_carrier_date", "delivered_customer_date", "estimated_delivery_date"],
    "CustomerID": ["customer_id", "cust_id", "user_id", "client_id", "buyer_id", "customer_unique_id"],
    "OrderID": ["order_id", "order_no", "transaction_id", "invoice_id", "receipt_no", "sales_order"],
    "ProductID": ["product_id", "item_id", "sku", "stock_code", "product_code"],
}


def detect_retail_entities(table_name: str, columns: List[str], row_count: int, profile: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    entities = []
    name_lower = table_name.lower()
    col_lower = [c.lower() for c in columns]

    for entity_type, keywords in RETAIL_ENTITY_KEYWORDS.items():
        matched = []
        for kw in keywords:
            if kw in name_lower:
                matched.append(f"table_name:{kw}")
            for c in col_lower:
                if kw in c and f"column:{c}" not in matched:
                    matched.append(f"column:{c}")

        if matched:
            confidence = min(0.99, 0.5 + 0.1 * len(matched))
            entities.append({
                "entity_type": entity_type,
                "matched_columns": [m.split(":", 1)[1] for m in matched if m.startswith("column:")],
                "confidence": round(confidence, 2),
                "evidence": f"Matched keywords: {matched}",
                "row_count": row_count,
            })

    return entities


def detect_retail_column_semantics(columns: List[str], profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    semantics = []
    col_profile = profile.get("columns", {})
    col_categories = profile.get("column_categories", {})

    all_keywords = []
    for entity_type, keywords in RETAIL_ENTITY_KEYWORDS.items():
        for kw in keywords:
            all_keywords.append((kw, entity_type))
    all_keywords.sort(key=lambda x: -len(x[0]))

    for col in columns:
        col_lower = col.lower()
        matched_entity = None
        confidence = 0.0
        evidence_parts = []

        for kw, entity_type in all_keywords:
            if kw in col_lower:
                matched_entity = entity_type
                evidence_parts.append(f"keyword:{kw}")
                confidence += 0.15
                break

        cat = None
        for cat_name, cols in col_categories.items():
            if col in cols:
                cat = cat_name
                break

        if cat == "temporal":
            matched_entity = "Date"
            confidence = max(confidence, 0.9)
            evidence_parts.append("temporal_category")
        elif cat == "measures":
            if not matched_entity:
                for kw, entity_type in sorted(all_keywords, key=lambda x: -len(x[0])):
                    if kw in col_lower and entity_type in ("Revenue", "Price", "Freight", "Discount"):
                        matched_entity = entity_type
                        confidence = max(confidence, 0.7)
                        evidence_parts.append(f"measure_keyword:{kw}")
                        break

        if not matched_entity:
            continue

        confidence = min(0.99, confidence)
        sample = []
        if col in col_profile:
            sample = col_profile[col].get("sample_values", [])[:3]

        semantics.append({
            "column_name": col,
            "semantic_role": matched_entity,
            "business_entity": matched_entity,
            "confidence": round(confidence, 2),
            "evidence": ", ".join(evidence_parts) if evidence_parts else "inferred_from_numeric_type",
            "sample_values": sample,
        })

    return semantics


def get_retail_entity_mapping(profile: Dict[str, Any]) -> Dict[str, Optional[str]]:
    mapper_result = RetailSemanticMapper.map(profile)
    mapping = mapper_result["mapping"]
    return mapping
