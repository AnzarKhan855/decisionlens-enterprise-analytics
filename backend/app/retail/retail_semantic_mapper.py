from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.logging.logger import get_logger
logger = get_logger(__name__)


class RetailSemanticMapper:
    ALIAS_MAP = {
        "order_id": [
            "invoice", "invoice_no", "invoice_id", "invoiceno", "orderid", "order_id",
            "order_no", "order_number", "order_code", "bill_no", "bill_id",
            "receipt", "receipt_no", "receipt_id", "transaction_id",
            "transaction_no", "sales_order", "order_uuid", "txn_id",
            "payment_id", "checkout_id", "confirmation_number",
        ],
        "product_id": [
            "stockcode", "stock_code", "sku", "product_id", "product_code",
            "item_id", "item_code", "item_no", "item_number", "product",
            "product_no", "upc", "ean", "barcode", "merchandise_code",
        ],
        "customer_id": [
            "customer_id", "customerid", "customer_no", "customer_code",
            "client_id", "client_code", "buyer_id", "user_id", "account_id",
            "member_id", "patron_id", "shopper_id",
        ],
        "quantity": [
            "quantity", "qty", "units", "units_sold", "items_sold",
            "order_qty", "item_qty", "sold_qty", "volume", "count",
            "item_count", "order_quantity", "quantity_sold",
        ],
        "price": [
            "unitprice", "unit_price", "price", "rate", "selling_price",
            "list_price", "cost_price", "mrp", "standard_price",
            "catalog_price", "base_price", "item_price",
        ],
        "revenue": [
            "revenue", "sales", "total_amount", "total_sales", "amount",
            "gross_income", "turnover", "net_sales", "gross_sales",
            "invoice_amount", "order_amount", "transaction_amount",
            "line_total", "extended_amount", "sales_amount",
            "payment_value", "payment_amount", "total_payment", "gross_revenue", "net_revenue",
            "sales_value", "total_value", "basket_value", "cart_value",
        ],
        "date": [
            "invoicedate", "invoice_date", "orderdate", "order_date",
            "purchasedate", "purchase_date", "date", "timestamp",
            "transaction_date", "sales_date", "created_at", "updated_at",
            "event_time", "event_date", "order_timestamp",
        ],
        "category": [
            "category", "categories", "category_id", "category_name",
            "segment", "product_category", "item_category", "dept",
            "department", "division", "product_type", "item_type",
        ],
        "country": [
            "country", "countries", "nation", "nationality", "region",
            "state", "province", "territory", "market", "geo",
            "country_code", "country_name",
        ],
        "freight": [
            "freight", "freight_value", "shipping", "shipping_cost",
            "delivery_charge", "postage", "carrier_charge", "transport",
            "logistics_cost", "fulfillment_cost", "ship_cost",
        ],
        "discount": [
            "discount", "discounts", "promo", "promotion", "coupon",
            "markdown", "discount_rate", "discount_pct", "discount_amount",
            "reduction", "offer_price",
        ],
        "payment": [
            "payment", "payments", "payment_type", "pay_mode", "method",
            "payment_method", "settlement", "payment_status", "pay_type",
        ],
        "delivery": [
            "delivery", "deliveries", "shipment", "shipped_date",
            "fulfillment", "dispatch", "courier", "delivered",
            "delivery_date", "estimated_delivery", "actual_delivery",
        ],
        "review": [
            "review", "reviews", "rating", "ratings", "feedback",
            "score", "nps", "customer_score", "satisfaction",
        ],
        "inventory": [
            "inventory", "stock", "stocks", "in_stock", "available_qty",
            "warehouse", "stock_qty", "on_hand", "stock_level",
        ],
        "store": [
            "store", "stores", "shop", "outlet", "branch", "location",
            "retail_location", "store_id", "store_code", "store_name",
        ],
        "region": [
            "region", "regions", "state", "states", "province",
            "territory", "zone", "district", "area", "market",
        ],
        "city": [
            "city", "cities", "town", "municipality", "locality",
        ],
        "status": [
            "status", "order_status", "invoice_status", "payment_status",
            "fulfillment_status", "state",
        ],
    }

    ENTITY_TYPE_MAP = {
        "order_id": "Order",
        "product_id": "Product",
        "customer_id": "Customer",
        "quantity": "Quantity",
        "price": "Price",
        "revenue": "Revenue",
        "date": "Date",
        "category": "Category",
        "country": "Country",
        "freight": "Freight",
        "discount": "Discount",
        "payment": "Payment",
        "delivery": "Delivery",
        "review": "Review",
        "inventory": "Inventory",
        "store": "Store",
        "region": "Region",
        "city": "City",
        "status": "Status",
    }

    @classmethod
    def map(cls, profile: Dict[str, Any]) -> Dict[str, Any]:
        stage = "retail_semantic_mapping"
        columns = list(profile.get("columns", {}).keys())
        col_lower_map = {c.lower(): c for c in columns}
        mapping: Dict[str, Optional[str]] = {k: None for k in list(cls.ENTITY_TYPE_MAP.keys()) + ["revenue_formula", "product_description"]}
        mapping["revenue_formula"] = None

        try:
            sorted_aliases = sorted(cls.ALIAS_MAP.items(), key=lambda x: -len(x[0]))
            used_columns = set()
            for semantic_key, aliases in sorted_aliases:
                if mapping.get(semantic_key):
                    continue
                ordered_aliases = sorted(set(aliases), key=len, reverse=True)
                for alias in ordered_aliases:
                    for cl, original in col_lower_map.items():
                        if original in used_columns:
                            continue
                        if alias in cl:
                            mapping[semantic_key] = original
                            used_columns.add(original)
                            break
                    if mapping.get(semantic_key):
                        break

            if mapping.get("product_id") is None:
                for alias in ["description", "desc", "product_name", "item_name", "product_description"]:
                    for cl, original in col_lower_map.items():
                        if original in used_columns:
                            continue
                        if alias in cl:
                            mapping["product_description"] = original
                            used_columns.add(original)
                            break
                    if mapping.get("product_description"):
                        break

            if not mapping.get("revenue") and mapping.get("price") and mapping.get("quantity"):
                mapping["revenue_formula"] = f"{mapping['price']} * {mapping['quantity']}"
                mapping["revenue"] = mapping["price"]

            if mapping.get("date"):
                date_col = mapping["date"]
                col_prof = profile.get("columns", {}).get(date_col, {})
                if col_prof.get("data_type", "").upper() not in ("DATE", "TIMESTAMP", "TIME"):
                    mapping["date"] = None
                    for cl, original in col_lower_map.items():
                        if original in used_columns:
                            continue
                        dt = profile.get("columns", {}).get(original, {}).get("data_type", "").upper()
                        if any(k in dt for k in ["DATE", "TIMESTAMP", "TIME"]) or any(k in cl for k in ["date", "timestamp", "time"]):
                            mapping["date"] = original
                            used_columns.add(original)
                            break

            health = cls._compute_health(profile, mapping, columns)
            forecast_readiness = cls._compute_forecast_readiness(profile, mapping)
            computed_metrics = cls._compute_metrics_list(mapping)

            engine_mapping = {
                "order_table": None,
                "product_table": None,
                "customer_table": None,
                "category_column": mapping.get("category"),
                "revenue_column": mapping.get("revenue"),
                "revenue_formula": mapping.get("revenue_formula"),
                "price_column": mapping.get("price"),
                "freight_column": mapping.get("freight"),
                "discount_column": mapping.get("discount"),
                "payment_column": mapping.get("payment"),
                "delivery_column": mapping.get("delivery"),
                "inventory_column": mapping.get("inventory"),
                "store_column": mapping.get("store"),
                "region_column": mapping.get("region"),
                "country_column": mapping.get("country"),
                "state_column": mapping.get("region"),
                "city_column": mapping.get("city"),
                "review_column": mapping.get("review"),
                "date_column": mapping.get("date"),
                "customer_id_column": mapping.get("customer_id"),
                "order_id_column": mapping.get("order_id"),
                "product_id_column": mapping.get("product_id"),
                "quantity_column": mapping.get("quantity"),
                "product_description": mapping.get("product_description"),
            }

            return {
                "mapping": engine_mapping,
                "health_score": health,
                "forecast_readiness": forecast_readiness,
                "computed_metrics": computed_metrics,
            }
        except Exception as e:
            logger.error(f"{stage} failed: {str(e)}")
            missing_cols = []
            required = ["revenue", "date", "order_id"]
            for req in required:
                if not mapping.get(req):
                    missing_cols.append(req)
            return {
                "mapping": {k: mapping.get(k) for k in list(cls.ENTITY_TYPE_MAP.keys()) + ["revenue_formula", "product_description"]},
                "health_score": {"overall_score": 0.0, "grade": "F", "status": "Critical", "breakdown": []},
                "forecast_readiness": {"ready": False, "reasons": [f"Mapping failed: {str(e)}"], "strategy": "none", "date_column": None, "min_rows_required": 30, "total_rows": profile.get("total_rows", 0)},
                "computed_metrics": [],
                "missing_required_columns": missing_cols,
                "error": f"Semantic mapping failed: {str(e)}. Missing columns: {', '.join(missing_cols) if missing_cols else 'unknown'}.",
            }

    @staticmethod
    def _compute_metrics_list(mapping: Dict[str, Optional[str]]) -> List[str]:
        metrics = []
        if mapping.get("revenue"):
            metrics.append("revenue")
        if mapping.get("quantity"):
            metrics.append("quantity")
        if mapping.get("price"):
            metrics.append("unit_price")
        if mapping.get("order_id"):
            metrics.append("orders")
        if mapping.get("customer_id"):
            metrics.append("customers")
        if mapping.get("product_id") or mapping.get("product_description"):
            metrics.append("products")
        if mapping.get("date"):
            metrics.append("temporal_trends")
        if mapping.get("forecast_readiness", {}).get("ready"):
            metrics.append("forecast")
        return metrics

    @staticmethod
    def _compute_health(profile: Dict[str, Any], mapping: Dict[str, Optional[str]], columns: List[str]) -> Dict[str, Any]:
        total_rows = profile.get("total_rows", 0)
        cols_profile = profile.get("columns", {})

        missing_values_score = 100.0
        if cols_profile:
            null_pcts = [c.get("null_percentage", 0.0) for c in cols_profile.values() if isinstance(c, dict)]
            avg_null = sum(null_pcts) / len(null_pcts) if null_pcts else 0.0
            missing_values_score = max(0.0, 100.0 - avg_null * 1.5)

        duplicate_score = 100.0
        dup_pct = profile.get("duplicate_percentage", 0.0)
        if dup_pct > 0:
            duplicate_score = max(0.0, 100.0 - dup_pct * 5.0)

        date_score = 100.0 if mapping.get("date") else 0.0
        if mapping.get("date"):
            date_col = mapping["date"]
            date_nulls = cols_profile.get(date_col, {}).get("null_percentage", 100.0)
            date_score = max(0.0, 100.0 - date_nulls)

        revenue_score = 100.0 if mapping.get("revenue") else 0.0
        if mapping.get("revenue_formula"):
            revenue_score = 100.0
        elif mapping.get("revenue"):
            rev_col = mapping["revenue"]
            rev_nulls = cols_profile.get(rev_col, {}).get("null_percentage", 100.0)
            revenue_score = max(0.0, 100.0 - rev_nulls * 1.2)

        forecast_score = 85.0 if mapping.get("date") else 0.0
        ai_readiness = 70.0 if mapping.get("order_id") and mapping.get("quantity") else 40.0
        if mapping.get("customer_id"):
            ai_readiness += 10.0
        if mapping.get("product_id") or mapping.get("product_description"):
            ai_readiness += 10.0
        ai_readiness = min(100.0, ai_readiness)

        overall = round(
            missing_values_score * 0.25 +
            duplicate_score * 0.15 +
            date_score * 0.15 +
            revenue_score * 0.15 +
            forecast_score * 0.15 +
            ai_readiness * 0.15,
            2,
        )
        overall = max(0.0, min(100.0, overall))

        grade = "A" if overall >= 85 else "B" if overall >= 70 else "C" if overall >= 50 else "D"
        status = "Strong" if overall >= 85 else "Stable" if overall >= 70 else "Needs Improvement" if overall >= 50 else "Critical"

        return {
            "overall_score": overall,
            "grade": grade,
            "status": status,
            "missing_values_score": round(missing_values_score, 2),
            "duplicate_score": round(duplicate_score, 2),
            "date_score": round(date_score, 2),
            "revenue_score": round(revenue_score, 2),
            "forecast_score": round(forecast_score, 2),
            "ai_readiness_score": round(ai_readiness, 2),
            "breakdown": [
                {"component": "Missing Values", "score": round(missing_values_score, 2)},
                {"component": "Duplicate Rows", "score": round(duplicate_score, 2)},
                {"component": "Date Completeness", "score": round(date_score, 2)},
                {"component": "Revenue Availability", "score": round(revenue_score, 2)},
                {"component": "Forecast Readiness", "score": round(forecast_score, 2)},
                {"component": "AI Readiness", "score": round(ai_readiness, 2)},
            ],
        }

    @staticmethod
    def _compute_forecast_readiness(profile: Dict[str, Any], mapping: Dict[str, Optional[str]]) -> Dict[str, Any]:
        date_col = mapping.get("date")
        ready = bool(date_col)
        reasons = []
        if not date_col:
            reasons.append("No date column detected")
        else:
            reasons.append(f"Date column detected: {date_col}")

        measures = profile.get("column_categories", {}).get("measures", [])
        numeric_measures = [m for m in measures if mapping.get("revenue") and m == mapping["revenue"]]
        if numeric_measures:
            reasons.append(f"Numeric measure available: {numeric_measures[0]}")
        else:
            reasons.append("No numeric time-series measure detected")

        temporal = profile.get("column_categories", {}).get("temporal", [])
        if temporal:
            reasons.append(f"Temporal columns: {temporal}")

        total_rows = profile.get("total_rows", 0)
        if total_rows < 30:
            ready = False
            reasons.append(f"Insufficient rows for forecasting: {total_rows}")

        strategy = "time_series_forecast" if ready else "none"
        return {
            "ready": ready,
            "reasons": reasons,
            "strategy": strategy,
            "date_column": date_col,
            "min_rows_required": 30,
            "total_rows": total_rows,
        }
