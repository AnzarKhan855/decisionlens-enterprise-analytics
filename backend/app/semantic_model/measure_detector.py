from typing import Any, Dict, List

from app.semantic_model.core import Measure


MEASURE_AGGREGATION_MAP = {
    "sum": ["revenue", "sales", "amount", "total", "price", "cost", "profit",
            "quantity", "qty", "salary", "income", "expense", "balance", "fee", "tax", "value",
            "margin", "bonus", "commission", "payout", "claim", "premium", "discount",
            "throughput", "volume", "duration", "weight", "distance", "speed", "size",
            "unitprice", "unit_price", "freight", "shipping", "gross_income", "turnover",
            "line_total", "extended_amount", "sales_amount", "invoice_amount", "order_amount",
            "gross_sales", "net_sales", "cogs"],
    "avg": ["discount", "margin", "rate", "percentage", "score", "grade", "marks",
            "efficiency", "utilization", "conversion", "ctr", "cpc", "cpa", "roas",
            "nps", "oee", "yield", "mortality", "readmission", "attrition", "churn",
            "unit_price", "unitprice", "mrp", "catalog_price", "base_price", "item_price"],
    "count": ["count", "num", "number", "total_count"],
    "min": [],
    "max": [],
}

RETAIL_MEASURE_ALIASES = {
    "revenue": ["revenue", "sales", "total_amount", "total_sales", "amount",
                "gross_income", "turnover", "net_sales", "gross_sales",
                "invoice_amount", "order_amount", "transaction_amount",
                "line_total", "extended_amount", "sales_amount"],
    "quantity": ["quantity", "qty", "units", "units_sold", "items_sold",
                 "order_qty", "item_qty", "sold_qty", "volume", "count",
                 "item_count", "order_quantity", "quantity_sold"],
    "price": ["unitprice", "unit_price", "price", "rate", "selling_price",
              "list_price", "cost_price", "mrp", "standard_price",
              "catalog_price", "base_price", "item_price"],
    "freight": ["freight", "freight_value", "shipping", "shipping_cost",
                "delivery_charge", "postage", "carrier_charge", "ship_cost"],
    "discount": ["discount", "discounts", "promo", "promotion", "coupon",
                 "markdown", "discount_rate", "discount_pct", "discount_amount",
                 "reduction"],
    "profit": ["profit", "gross_profit", "net_profit", "profit_margin",
               "margin", "operating_profit"],
}


def detect_measures(
    table_name: str,
    columns: List[Dict[str, Any]],
    profile: Dict[str, Any]
) -> List[Measure]:
    measures = []
    col_profile = profile.get("columns", {})

    # Try to use retail semantic mapper for measure detection if available
    retail_aliases = {}
    try:
        from app.retail.retail_semantic_mapper import RetailSemanticMapper
        retail_aliases = RetailSemanticMapper.ALIAS_MAP
    except ImportError:
        pass

    for c in columns:
        cname = c["name"]
        ctype = c.get("type", "").lower()
        cname_lower = cname.lower()

        is_numeric = any(nt in ctype for nt in [
            "bigint", "integer", "smallint", "tinyint", "double",
            "float", "decimal", "hugeint", "real"
        ])

        # Check if this column matches any retail alias for a measure
        retail_measure_match = None
        for semantic_key, aliases in retail_aliases.items():
            if semantic_key in ("order_id", "product_id", "customer_id", "date",
                                "category", "country", "freight", "discount",
                                "payment", "delivery", "review", "inventory",
                                "store", "region", "city", "status"):
                continue
            for alias in aliases:
                if alias in cname_lower:
                    retail_measure_match = semantic_key
                    break
            if retail_measure_match:
                break

        is_measure_keyword = any(
            kw in cname_lower for kw in [
                "sales", "revenue", "profit", "amount", "cost", "price",
                "discount", "qty", "quantity", "score", "marks", "grade",
                "percentage", "rate", "salary", "income", "expense",
                "balance", "total", "fee", "tax", "val", "value", "margin",
                "bonus", "commission", "payout", "claim", "premium",
                "throughput", "volume", "duration", "weight", "distance",
                "speed", "size", "utilization", "efficiency", "conversion",
                "ctr", "cpc", "cpa", "roas", "nps", "oee", "yield",
                "mortality", "readmission", "attrition", "churn",
                "unitprice", "unit_price", "freight", "shipping",
                "gross_income", "turnover", "line_total", "extended_amount",
                "sales_amount", "invoice_amount", "order_amount",
                "gross_sales", "net_sales", "cogs"
            ]
        )

        is_retail_measure = retail_measure_match in ("revenue", "quantity", "price", "freight", "discount", "profit")

        if is_numeric and (is_measure_keyword or is_retail_measure or ctype in ("double", "float", "decimal", "bigint", "integer")):
            agg = "SUM"
            biz_type = "numeric"

            if retail_measure_match in ("price", "discount", "percentage", "score", "grade", "marks"):
                agg = "AVG"
                biz_type = "ratio"

            for agg_type, kw_list in MEASURE_AGGREGATION_MAP.items():
                if any(kw in cname_lower for kw in kw_list):
                    agg = agg_type.upper()
                    break

            if cname_lower in ("discount", "rate", "percentage", "score", "grade", "marks"):
                agg = "AVG"
                biz_type = "ratio"

            if retail_measure_match == "quantity":
                agg = "SUM"
                biz_type = "volume"

            measures.append(Measure(
                name=cname,
                data_type=ctype,
                table=table_name,
                aggregation=agg,
                business_type=biz_type,
                description=f"Numeric measure column '{cname}' used for aggregation and KPI calculation."
            ))

    return measures


def classify_measure_business_type(measure_name: str) -> str:
    name_lower = measure_name.lower()
    if any(kw in name_lower for kw in ["revenue", "sales", "amount", "price", "total", "cost", "profit"]):
        return "financial"
    if any(kw in name_lower for kw in ["quantity", "qty", "count", "volume"]):
        return "volume"
    if any(kw in name_lower for kw in ["rate", "percentage", "ratio", "score", "grade"]):
        return "ratio"
    if any(kw in name_lower for kw in ["salary", "income", "expense", "payroll"]):
        return "financial"
    return "numeric"