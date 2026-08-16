from typing import Any, Dict, List

from app.semantic_model.core import BusinessDomain, DatasetType


DOMAIN_KEYWORDS = {
    BusinessDomain.RETAIL_ECOMMERCE: [
        "sales", "revenue", "profit", "customer", "order", "store", "product",
        "sku", "quantity", "discount", "price", "category", "freight", "aov",
        "merchant", "cart", "checkout", "delivery", "invoice", "purchase",
        "invoicedate", "invoice_date", "orderdate", "order_date", "stockcode",
        "stock_code", "unitprice", "unit_price", "transaction_id", "receipt",
        "checkout_id", "confirmation_number", "shopper", "buyer", "client",
        "gross_income", "turnover", "line_total", "extended_amount",
        "sales_amount", "invoice_amount", "order_amount", "gross_sales",
        "net_sales", "freight_value", "shipping_cost", "delivery_charge",
        "discount_rate", "discount_pct", "promo", "promotion", "coupon",
        "markdown", "rating", "feedback", "nps", "satisfaction",
        "warehouse", "stock_qty", "inventory", "product_category",
        "item_category", "department", "division", "product_type",
        "region", "territory", "zone", "market", "country",
        "payment_method", "pay_mode", "settlement",
        "shipped_date", "fulfillment", "dispatch", "courier", "delivered",
        "city", "locality", "town", "municipality",
        "order_status", "invoice_status", "payment_status", "fulfillment_status",
        "store_id", "store_code", "store_name", "outlet", "branch",
        "item_id", "item_code", "item_no", "item_number",
        "upc", "ean", "barcode", "merchandise_code",
    ],
    BusinessDomain.FINANCE_BANKING: [
        "account", "balance", "transaction", "credit", "debit", "deposit",
        "withdrawal", "loan", "interest", "mortgage", "portfolio", "asset",
        "liability", "tax", "iban", "finance", "banking", "payment"
    ],
    BusinessDomain.HEALTHCARE: [
        "patient", "patient_id", "diagnosis", "doctor", "hospital", "medicine",
        "dosage", "blood_pressure", "treatment", "admission", "discharge",
        "readmission", "symptom", "icd10", "mrn", "ward", "physician",
        "mortality", "clinical", "medical"
    ],
    BusinessDomain.HUMAN_RESOURCES: [
        "employee", "employee_id", "salary", "department", "designation",
        "joining", "experience", "attendance", "leave", "manager", "payroll",
        "attrition", "hire", "performance", "bonus", "ctc", "hr", "workforce"
    ],
    BusinessDomain.LOGISTICS_SUPPLY_CHAIN: [
        "stock", "warehouse", "supplier", "inventory", "purchase", "shipment",
        "logistics", "reorder", "lead_time", "carrier", "tracking",
        "fulfillment", "waybill", "fleet", "supply", "delivery"
    ],
    BusinessDomain.MANUFACTURING: [
        "machine", "downtime", "yield", "batch", "assembly", "defect", "oee",
        "maintenance", "sensor_temp", "vibration", "calibration", "tolerance",
        "scrap", "production", "manufacturing"
    ],
    BusinessDomain.TELECOMMUNICATIONS: [
        "call_duration", "caller", "receiver", "bandwidth", "signal", "tower",
        "roaming", "data_usage", "sim", "imei", "latency", "packet_loss",
        "cell_site", "telecom", "network"
    ],
    BusinessDomain.INSURANCE: [
        "policy", "policy_id", "claim", "premium", "deductible", "underwriting",
        "coverage", "claimant", "payout", "actuarial", "loss_ratio", "insured",
        "insurance"
    ],
    BusinessDomain.MARKETING_ADVERTISING: [
        "campaign", "impression", "click", "ctr", "cpc", "conversion", "cpa",
        "ad_group", "channel", "reach", "engagement", "lead", "roas", "marketing"
    ],
    BusinessDomain.SAAS_SUBSCRIPTION: [
        "mrr", "arr", "churn", "subscription", "plan", "trial", "ltv", "cac",
        "renewal", "tier", "license", "seat_count", "saas"
    ],
    BusinessDomain.CRM_SALES: [
        "lead_id", "opportunity", "pipeline", "stage", "deal", "contact",
        "company", "account_owner", "touchpoint", "nps", "sales_rep", "crm"
    ],
    BusinessDomain.GOVERNMENT_PUBLIC_SECTOR: [
        "citizen", "census", "taxpayer", "constituency", "district", "permit",
        "zoning", "pension", "subsidy", "voter", "government", "public"
    ],
    BusinessDomain.REAL_ESTATE: [
        "property", "listing", "square_feet", "sqft", "bedroom", "bathroom",
        "rent", "lease", "mortgage", "appraisal", "zoning", "real_estate"
    ],
    BusinessDomain.HOSPITALITY_TOURISM: [
        "hotel", "booking", "guest", "room_type", "check_in", "check_out",
        "night_stay", "reservation", "occupancy", "revpar", "hospitality"
    ],
    BusinessDomain.AGRICULTURE: [
        "crop", "yield", "harvest", "soil_moisture", "rainfall", "fertilizer",
        "acreage", "irrigation", "pest_level", "farm", "agriculture"
    ],
    BusinessDomain.ENERGY_UTILITIES: [
        "kw_h", "voltage", "grid", "substation", "generator", "mw", "consumption",
        "outage", "meter_reading", "utility", "energy", "electricity"
    ],
    BusinessDomain.EDUCATION: [
        "student_id", "student", "roll_no", "marks", "grade", "gpa", "attendance",
        "semester", "course", "subject", "teacher", "faculty", "fee_paid",
        "tuition", "school", "university", "academic", "enrollment", "exam",
        "assignment"
    ],
    BusinessDomain.CYBERSECURITY: [
        "src_ip", "dst_ip", "source_ip", "destination_ip", "protocol",
        "flow_duration", "flow_bytes", "flow_packets", "timestamp", "attack",
        "attack_type", "label", "malicious", "benign", "severity", "port",
        "src_port", "dst_port", "tcp_flags", "threat", "signature", "malware",
        "cve", "event_id", "siem", "firewall", "suricata", "zeek", "wazuh",
        "cloudtrail", "syslog", "payload", "vulnerability"
    ],
}

DATASET_TYPE_KEYWORDS = {
    DatasetType.RETAIL: [
        "order", "product", "customer", "sales", "revenue", "store", "cart",
        "checkout", "freight", "seller", "invoice", "purchase", "stockcode",
        "stock_code", "sku", "item", "unitprice", "unit_price", "quantity",
        "qty", "transaction_id", "receipt", "checkout_id", "confirmation_number",
        "shopper", "buyer", "client", "gross_income", "turnover",
        "line_total", "extended_amount", "sales_amount", "invoice_amount",
        "order_amount", "gross_sales", "net_sales", "freight_value",
        "shipping_cost", "delivery_charge", "discount_rate", "discount_pct",
        "promo", "promotion", "coupon", "markdown", "rating", "feedback",
        "nps", "satisfaction", "warehouse", "stock_qty", "inventory",
        "product_category", "item_category", "department", "division",
        "product_type", "region", "territory", "zone", "market", "country",
        "payment_method", "pay_mode", "settlement",
        "shipped_date", "fulfillment", "dispatch", "courier", "delivered",
        "city", "locality", "town", "municipality",
        "order_status", "invoice_status", "payment_status", "fulfillment_status",
        "store_id", "store_code", "store_name", "outlet", "branch",
        "item_id", "item_code", "item_no", "item_number",
        "upc", "ean", "barcode", "merchandise_code",
    ],
    DatasetType.CYBERSECURITY: ["ip", "attack", "threat", "malware", "vulnerability", "cve", "signature", "firewall", "siem", "event", "port", "protocol", "zeek", "suricata"],
    DatasetType.HEALTHCARE: ["patient", "diagnosis", "doctor", "hospital", "medicine", "admission", "discharge", "readmission", "icd", "mrn", "ward", "physician"],
    DatasetType.FINANCE: ["account", "balance", "transaction", "credit", "debit", "deposit", "withdrawal", "loan", "interest", "portfolio", "asset", "liability"],
    DatasetType.BANKING: ["account", "balance", "transaction", "credit", "debit", "deposit", "withdrawal", "loan", "interest", "mortgage", "iban", "branch"],
    DatasetType.MANUFACTURING: ["machine", "downtime", "yield", "batch", "assembly", "defect", "oee", "maintenance", "sensor", "production", "scrap", "calibration"],
    DatasetType.HUMAN_RESOURCES: ["employee", "salary", "department", "attendance", "leave", "manager", "payroll", "attrition", "hire", "performance", "bonus", "workforce"],
    DatasetType.MARKETING: ["campaign", "impression", "click", "ctr", "cpc", "conversion", "cpa", "channel", "reach", "engagement", "lead", "roas", "ad_group"],
    DatasetType.TELECOMMUNICATIONS: ["call", "caller", "receiver", "bandwidth", "signal", "tower", "roaming", "data_usage", "sim", "imei", "latency", "packet_loss"],
    DatasetType.INSURANCE: ["policy", "claim", "premium", "deductible", "underwriting", "coverage", "claimant", "payout", "actuarial", "loss_ratio"],
    DatasetType.GOVERNMENT: ["citizen", "census", "taxpayer", "constituency", "district", "permit", "zoning", "pension", "subsidy", "voter", "public"],
    DatasetType.EDUCATION: ["student", "marks", "grade", "gpa", "attendance", "semester", "course", "subject", "teacher", "faculty", "university", "academic", "enrollment"],
    DatasetType.LOGISTICS: ["shipment", "warehouse", "supplier", "inventory", "purchase", "logistics", "reorder", "lead_time", "carrier", "tracking", "fulfillment", "waybill", "fleet"],
    DatasetType.ENERGY: ["kw_h", "voltage", "grid", "substation", "generator", "mw", "consumption", "outage", "meter_reading", "utility", "energy", "electricity"],
}

BUSINESS_DOMAIN_TO_DATASET_TYPE = {
    BusinessDomain.RETAIL_ECOMMERCE: DatasetType.RETAIL,
    BusinessDomain.FINANCE_BANKING: DatasetType.FINANCE,
    BusinessDomain.HEALTHCARE: DatasetType.HEALTHCARE,
    BusinessDomain.HUMAN_RESOURCES: DatasetType.HUMAN_RESOURCES,
    BusinessDomain.LOGISTICS_SUPPLY_CHAIN: DatasetType.LOGISTICS,
    BusinessDomain.MANUFACTURING: DatasetType.MANUFACTURING,
    BusinessDomain.TELECOMMUNICATIONS: DatasetType.TELECOMMUNICATIONS,
    BusinessDomain.INSURANCE: DatasetType.INSURANCE,
    BusinessDomain.MARKETING_ADVERTISING: DatasetType.MARKETING,
    BusinessDomain.SAAS_SUBSCRIPTION: DatasetType.MARKETING,
    BusinessDomain.CRM_SALES: DatasetType.RETAIL,
    BusinessDomain.GOVERNMENT_PUBLIC_SECTOR: DatasetType.GOVERNMENT,
    BusinessDomain.REAL_ESTATE: DatasetType.FINANCE,
    BusinessDomain.HOSPITALITY_TOURISM: DatasetType.RETAIL,
    BusinessDomain.AGRICULTURE: DatasetType.MANUFACTURING,
    BusinessDomain.ENERGY_UTILITIES: DatasetType.ENERGY,
    BusinessDomain.EDUCATION: DatasetType.EDUCATION,
    BusinessDomain.CYBERSECURITY: DatasetType.CYBERSECURITY,
    BusinessDomain.GENERIC_BUSINESS: DatasetType.UNKNOWN,
}


def classify_domain(
    table_name: str,
    columns: List[str],
    measures: List[str]
) -> Dict[str, Any]:
    col_lower = [c.lower() for c in columns]
    measures_lower = [m.lower() for m in measures]
    name_lower = table_name.lower()

    all_text = " ".join(col_lower + measures_lower + [name_lower])

    scores = {}
    matched_cols_map = {}

    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = 0
        matches = []
        for kw in keywords:
            for col in col_lower:
                if kw in col or kw == col:
                    score += 1
                    if col not in matches:
                        matches.append(col)
            if kw in all_text:
                score += 1

        scores[domain.value] = score
        matched_cols_map[domain.value] = matches

    best_domain = max(scores, key=scores.get) if scores else "Generic Business"
    best_score = scores.get(best_domain, 0)

    if best_score == 0:
        return {
            "domain": "Generic Business",
            "confidence": 41.0,
            "reason": "No domain keywords matched the schema.",
            "matched_columns": []
        }

    matched_cols = matched_cols_map.get(best_domain, [])
    total_kws = len(DOMAIN_KEYWORDS.get(next(
        (d for d in DOMAIN_KEYWORDS if d.value == best_domain),
        list(DOMAIN_KEYWORDS.keys())[0]
    ), []))
    confidence = min(99.0, round((best_score / (total_kws + 2)) * 100 + 48.0, 1))

    if confidence < 50.0:
        return {
            "domain": "Generic Business",
            "confidence": confidence,
            "reason": f"Low confidence match ({confidence}%).",
            "matched_columns": matched_cols
        }

    col_str = ", ".join(matched_cols[:6])
    reason_str = f"Columns '{col_str}' strongly indicate a {best_domain.lower()} dataset."

    return {
        "domain": best_domain,
        "confidence": confidence,
        "reason": reason_str,
        "matched_columns": matched_cols
    }


def classify_dataset_type(
    table_name: str,
    columns: List[str],
    measures: List[str]
) -> Dict[str, Any]:
    col_lower = [c.lower() for c in columns]
    measures_lower = [m.lower() for m in measures]
    name_lower = table_name.lower()

    all_text = " ".join(col_lower + measures_lower + [name_lower])

    scores = {}
    matched_keywords_map = {}

    for dtype, keywords in DATASET_TYPE_KEYWORDS.items():
        score = 0
        matched = []
        for kw in keywords:
            if kw in all_text:
                score += 1
                matched.append(kw)
        scores[dtype] = score
        matched_keywords_map[dtype] = matched

    best_type = max(scores, key=scores.get) if scores else DatasetType.UNKNOWN
    best_score = scores.get(best_type, 0)

    if best_score == 0:
        return {
            "dataset_type": DatasetType.UNKNOWN.value,
            "dataset_type_confidence": 0.0,
            "dataset_type_matched_keywords": [],
        }

    matched_kws = matched_keywords_map.get(best_type, [])
    confidence = min(99.0, round((best_score / 5.0) * 100 + 30.0, 1))
    if confidence < 50.0 and best_score > 0:
        confidence = 50.0

    return {
        "dataset_type": best_type.value,
        "dataset_type_confidence": confidence,
        "dataset_type_matched_keywords": matched_kws[:10],
    }
