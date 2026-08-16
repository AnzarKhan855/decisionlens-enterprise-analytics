from typing import Any, Dict, List

from app.semantic_model.core import BusinessEntity


ENTITY_KEYWORDS = {
    "Entity": ["entity", "record", "party", "member", "subject", "stakeholder"],
    "Item": ["item", "article", "thing", "object", "asset", "resource"],
    "Transaction": ["transaction", "deal", "exchange", "interaction", "occurrence"],
    "Employee": ["employee", "staff", "workforce", "hr", "personnel", "worker"],
    "Location": ["location", "site", "branch", "facility", "premises", "outlet"],
    "Supplier": ["supplier", "vendor", "merchant", "partner", "manufacturer"],
    "Shipment": ["shipment", "delivery", "logistics", "tracking", "fulfillment", "carrier"],
    "Ticket": ["ticket", "incident", "issue", "service_request", "support"],
    "Campaign": ["campaign", "marketing", "promotion", "advertisement", "channel"],
    "Device": ["device", "sensor", "iot", "gateway", "endpoint", "equipment"],
    "Claim": ["claim", "policy", "insurance", "payout", "coverage"],
    "Patient": ["patient", "clinical", "medical", "admission", "diagnosis"],
    "Student": ["student", "learner", "pupil", "academic", "enrollment"],
    "Account": ["account", "ledger", "bookkeeping", "general_ledger", "journal"],
    "Project": ["project", "program", "initiative", "portfolio", "milestone"],
    "Teacher": ["teacher", "professor", "faculty", "instructor"],
    "Course": ["course", "subject", "subject_code", "semester", "curriculum"],
    "Exam": ["exam", "grade", "marks", "score", "pass_fail", "result"],
    "Doctor": ["doctor", "physician", "specialist", "nurse"],
    "Threat": ["attack", "attack_type", "threat", "malware", "cve", "signature"],
    "NetworkAsset": ["src_ip", "dst_ip", "source_ip", "destination_ip", "host", "mac_address"],
    "Port": ["port", "src_port", "dst_port", "protocol", "tcp_flags", "service"],
    "SecurityLog": ["event_id", "syslog", "firewall", "siem", "flow_duration", "packets"],
    "Loan": ["loan_id", "mortgage", "principal", "interest_rate", "collateral"],
    "Warehouse": ["warehouse_id", "bin_id", "stock_qty", "inventory_id"],
    "Order": ["order", "invoice", "receipt", "checkout", "cart", "transaction_id", "purchase", "sales_order"],
    "Customer": ["customer", "client", "buyer", "shopper", "account_id", "member_id", "user_id"],
    "Product": ["product", "stock", "stockcode", "sku", "item", "merchandise", "inventory_item"],
    "Category": ["category", "segment", "department", "division", "product_type", "item_type", "dept"],
    "Store": ["store", "shop", "outlet", "branch", "retail_location", "store_id"],
    "Review": ["review", "rating", "feedback", "score", "nps", "satisfaction"],
    "Freight": ["freight", "shipping", "delivery_charge", "postage", "carrier_charge", "ship_cost"],
    "Discount": ["discount", "promo", "promotion", "coupon", "markdown", "reduction"],
    "Payment": ["payment", "pay_mode", "payment_method", "settlement", "pay_type"],
    "Delivery": ["delivery", "shipment", "shipped_date", "fulfillment", "dispatch", "courier", "delivered"],
    "Region": ["region", "territory", "zone", "district", "area", "market", "state", "province"],
    "City": ["city", "town", "municipality", "locality"],
    "Status": ["status", "order_status", "invoice_status", "payment_status", "fulfillment_status"],
}


def detect_business_entities(
    table_name: str,
    columns: List[str],
    row_count: int
) -> List[str]:
    entities = []
    name_lower = table_name.lower()
    col_lower = [c.lower() for c in columns]

    # Use retail semantic mapper if available for retail-specific entities
    try:
        from app.retail.retail_semantic_mapper import RetailSemanticMapper
        mapper = RetailSemanticMapper()
        for semantic_key, entity_name in mapper.ENTITY_TYPE_MAP.items():
            aliases = mapper.ALIAS_MAP.get(semantic_key, [])
            for alias in aliases:
                if any(alias in col for col in col_lower):
                    if entity_name not in entities:
                        entities.append(entity_name)
                    break
            if any(alias in name_lower for alias in aliases):
                if entity_name not in entities:
                    entities.append(entity_name)
    except ImportError:
        pass

    # Fallback to keyword matching
    for entity, keywords in ENTITY_KEYWORDS.items():
        if any(k in name_lower for k in keywords):
            if entity not in entities:
                entities.append(entity)
        for keyword in keywords:
            if any(keyword in col for col in col_lower):
                if entity not in entities:
                    entities.append(entity)

    if not entities and row_count > 0:
        entities.append("Generic Business Record")
    return entities


def detect_entity_confidence(
    table_name: str,
    columns: List[str],
    entity_type: str
) -> float:
    name_lower = table_name.lower()
    col_lower = [c.lower() for c in columns]
    keywords = ENTITY_KEYWORDS.get(entity_type, [])

    name_matches = sum(1 for k in keywords if k in name_lower)
    col_matches = sum(1 for k in keywords for c in col_lower if k in c)

    total_keywords = len(keywords)
    if total_keywords == 0:
        return 0.5

    score = (name_matches * 0.6 + col_matches * 0.4) / total_keywords
    return min(0.99, round(score, 2))