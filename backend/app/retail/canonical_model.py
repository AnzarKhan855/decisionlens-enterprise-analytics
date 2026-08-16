from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CanonicalRetailModel:
    orders: List[Dict[str, Any]] = field(default_factory=list)
    customers: List[Dict[str, Any]] = field(default_factory=list)
    products: List[Dict[str, Any]] = field(default_factory=list)
    categories: List[Dict[str, Any]] = field(default_factory=list)
    revenue_column: Optional[str] = None
    revenue_formula: Optional[str] = None
    quantity_column: Optional[str] = None
    price_column: Optional[str] = None
    date_column: Optional[str] = None
    country_column: Optional[str] = None
    region_column: Optional[str] = None
    city_column: Optional[str] = None
    store_column: Optional[str] = None
    category_column: Optional[str] = None
    freight_column: Optional[str] = None
    discount_column: Optional[str] = None
    payment_column: Optional[str] = None
    delivery_column: Optional[str] = None
    review_column: Optional[str] = None
    inventory_column: Optional[str] = None
    status_column: Optional[str] = None
    profit_column: Optional[str] = None
    cost_column: Optional[str] = None
    order_id_column: Optional[str] = None
    customer_id_column: Optional[str] = None
    product_id_column: Optional[str] = None
    product_description_column: Optional[str] = None
    available_kpis: List[str] = field(default_factory=list)
    domain: str = "Retail & E-Commerce"
    dataset_type: str = "Retail"
    health_score: Dict[str, Any] = field(default_factory=dict)
    forecast_readiness: Dict[str, Any] = field(default_factory=dict)
    computed_metrics: List[str] = field(default_factory=list)
    raw_mapping: Dict[str, Optional[str]] = field(default_factory=dict)
    source_columns: List[str] = field(default_factory=list)
    missing_required_columns: List[str] = field(default_factory=list)

    def has_revenue(self) -> bool:
        return bool(self.revenue_column) or bool(self.revenue_formula)

    def has_quantity(self) -> bool:
        return bool(self.quantity_column)

    def has_price(self) -> bool:
        return bool(self.price_column)

    def has_date(self) -> bool:
        return bool(self.date_column)

    def has_customer(self) -> bool:
        return bool(self.customer_id_column)

    def has_product(self) -> bool:
        return bool(self.product_id_column) or bool(self.product_description_column)

    def has_order(self) -> bool:
        return bool(self.order_id_column)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "revenue_column": self.revenue_column,
            "revenue_formula": self.revenue_formula,
            "quantity_column": self.quantity_column,
            "price_column": self.price_column,
            "date_column": self.date_column,
            "country_column": self.country_column,
            "region_column": self.region_column,
            "city_column": self.city_column,
            "store_column": self.store_column,
            "category_column": self.category_column,
            "freight_column": self.freight_column,
            "discount_column": self.discount_column,
            "payment_column": self.payment_column,
            "delivery_column": self.delivery_column,
            "review_column": self.review_column,
            "inventory_column": self.inventory_column,
            "status_column": self.status_column,
            "profit_column": self.profit_column,
            "cost_column": self.cost_column,
            "order_id_column": self.order_id_column,
            "customer_id_column": self.customer_id_column,
            "product_id_column": self.product_id_column,
            "product_description_column": self.product_description_column,
            "available_kpis": self.available_kpis,
            "domain": self.domain,
            "dataset_type": self.dataset_type,
            "health_score": self.health_score,
            "forecast_readiness": self.forecast_readiness,
            "computed_metrics": self.computed_metrics,
            "source_columns": self.source_columns,
            "missing_required_columns": self.missing_required_columns,
            "has_revenue": self.has_revenue(),
            "has_quantity": self.has_quantity(),
            "has_price": self.has_price(),
            "has_date": self.has_date(),
            "has_customer": self.has_customer(),
            "has_product": self.has_product(),
            "has_order": self.has_order(),
        }


def build_canonical_model(profile: Dict[str, Any], mapping: Dict[str, Any]) -> CanonicalRetailModel:
    engine_mapping = mapping.get("mapping", {}) if isinstance(mapping, dict) else {}
    health_score = mapping.get("health_score", {}) if isinstance(mapping, dict) else {}
    forecast_readiness = mapping.get("forecast_readiness", {}) if isinstance(mapping, dict) else {}
    computed_metrics = mapping.get("computed_metrics", []) if isinstance(mapping, dict) else []
    raw_mapping = {k: v for k, v in engine_mapping.items()} if isinstance(engine_mapping, dict) else {}

    columns = list(profile.get("columns", {}).keys()) if profile else []

    order_id_col = engine_mapping.get("order_id_column")
    customer_id_col = engine_mapping.get("customer_id_column")
    product_id_col = engine_mapping.get("product_id_column")
    product_desc_col = engine_mapping.get("product_description")
    revenue_col = engine_mapping.get("revenue_column")
    revenue_formula = engine_mapping.get("revenue_formula")
    quantity_col = engine_mapping.get("quantity_column")
    price_col = engine_mapping.get("price_column")
    date_col = engine_mapping.get("date_column")
    country_col = engine_mapping.get("country_column")
    region_col = engine_mapping.get("region_column")
    city_col = engine_mapping.get("city_column")
    store_col = engine_mapping.get("store_column")
    category_col = engine_mapping.get("category_column")
    freight_col = engine_mapping.get("freight_column")
    discount_col = engine_mapping.get("discount_column")
    payment_col = engine_mapping.get("payment_column")
    delivery_col = engine_mapping.get("delivery_column")
    review_col = engine_mapping.get("review_column")
    inventory_col = engine_mapping.get("inventory_column")
    status_col = engine_mapping.get("status_column")

    profit_col = _find_by_alias(columns, ["profit", "gross_profit", "net_profit", "profit_margin", "margin"])
    cost_col = _find_by_alias(columns, ["cost", "total_cost", "unit_cost", "cogs", "cost_price"])

    model = CanonicalRetailModel(
        revenue_column=revenue_col,
        revenue_formula=revenue_formula,
        quantity_column=quantity_col,
        price_column=price_col,
        date_column=date_col,
        country_column=country_col,
        region_column=region_col,
        city_column=city_col,
        store_column=store_col,
        category_column=category_col,
        freight_column=freight_col,
        discount_column=discount_col,
        payment_column=payment_col,
        delivery_column=delivery_col,
        review_column=review_col,
        inventory_column=inventory_col,
        status_column=status_col,
        profit_column=profit_col,
        cost_column=cost_col,
        order_id_column=order_id_col,
        customer_id_column=customer_id_col,
        product_id_column=product_id_col,
        product_description_column=product_desc_col,
        health_score=health_score,
        forecast_readiness=forecast_readiness,
        computed_metrics=computed_metrics,
        raw_mapping=raw_mapping,
        source_columns=columns,
    )

    model.available_kpis = detect_available_kpis(model)
    model.missing_required_columns = _detect_missing_required(model)
    return model


def detect_available_kpis(model: CanonicalRetailModel) -> List[str]:
    kpis = []
    if model.has_revenue():
        kpis.append("total_revenue")
    if model.has_quantity():
        kpis.append("total_quantity")
    if model.has_price():
        kpis.append("average_price")
    if model.has_order():
        kpis.append("order_count")
    if model.has_customer():
        kpis.append("customer_count")
    if model.has_product():
        kpis.append("product_count")
    if model.has_date():
        kpis.append("daily_revenue")
        kpis.append("monthly_revenue")
        kpis.append("daily_orders")
        kpis.append("growth_rate")
    if model.has_revenue() and model.has_quantity():
        kpis.append("revenue_per_unit")
    if model.has_revenue() and model.has_order():
        kpis.append("average_order_value")
    if model.freight_column:
        kpis.append("freight_ratio")
    if model.discount_column:
        kpis.append("discount_ratio")
    if model.profit_column:
        kpis.append("total_profit")
        kpis.append("profit_margin")
    if model.cost_column and model.has_revenue():
        kpis.append("gross_margin")
    if model.review_column:
        kpis.append("average_rating")
    if model.category_column:
        kpis.append("revenue_by_category")
    if model.country_column:
        kpis.append("revenue_by_country")
    if model.store_column:
        kpis.append("revenue_by_store")
    if model.has_date() and model.has_revenue():
        kpis.append("time_series_forecast")
    return kpis


def get_revenue_formula(model: CanonicalRetailModel) -> Optional[str]:
    if model.revenue_column:
        return model.revenue_column
    if model.revenue_formula:
        return model.revenue_formula
    if model.price_column and model.quantity_column:
        return f"{model.price_column} * {model.quantity_column}"
    return None


def _find_by_alias(columns: List[str], aliases: List[str]) -> Optional[str]:
    col_lower_map = {c.lower(): c for c in columns}
    for alias in aliases:
        for cl, original in col_lower_map.items():
            if alias in cl:
                return original
    return None


def _detect_missing_required(model: CanonicalRetailModel) -> List[str]:
    missing = []
    if not model.has_revenue():
        missing.append("revenue")
    if not model.has_date():
        missing.append("date")
    if not model.has_order():
        missing.append("order_id")
    return missing
