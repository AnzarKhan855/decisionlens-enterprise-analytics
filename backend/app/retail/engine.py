from __future__ import annotations

from typing import Any, Dict, List, Optional
from pathlib import Path

from app.retail.retail_semantic_mapper import RetailSemanticMapper
from app.retail.canonical_model import build_canonical_model, CanonicalRetailModel, get_revenue_formula, detect_available_kpis
from app.ingestion.semantic_profiler import SemanticDataProfiler
from app.logging.logger import get_logger

logger = get_logger(__name__)


class RetailSemanticEngine:
    """
    Retail-specific semantic engine that integrates RetailSemanticMapper
    into the main ingestion and analytics pipeline.

    This engine:
    1. Profiles datasets using SemanticDataProfiler
    2. Applies RetailSemanticMapper alias detection
    3. Builds CanonicalRetailModel
    4. Returns enriched profile with retail semantic information
    """

    @classmethod
    def enrich_profile(cls, parquet_path: Path) -> Dict[str, Any]:
        profile = SemanticDataProfiler.profile(parquet_path)
        retail_mapping = cls.apply_retail_mapping(profile)
        canonical_model = build_canonical_model(profile, retail_mapping)
        enriched = dict(profile)
        enriched["retail_mapping"] = retail_mapping
        enriched["canonical_model"] = canonical_model.to_dict()
        enriched["revenue_formula"] = get_revenue_formula(canonical_model)
        enriched["available_kpis"] = detect_available_kpis(canonical_model)
        enriched["domain"] = "Retail & E-Commerce"
        enriched["dataset_type"] = "Retail"
        return enriched

    @classmethod
    def apply_retail_mapping(cls, profile: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return RetailSemanticMapper.map(profile)
        except Exception as e:
            logger.warning(f"RetailSemanticMapper failed: {str(e)}")
            return cls._fallback_mapping(profile)

    @classmethod
    def _fallback_mapping(cls, profile: Dict[str, Any]) -> Dict[str, Any]:
        columns = list(profile.get("columns", {}).keys())
        col_lower_map = {c.lower(): c for c in columns}
        mapping: Dict[str, Optional[str]] = {k: None for k in list(RetailSemanticMapper.ENTITY_TYPE_MAP.keys()) + ["revenue_formula", "product_description"]}
        mapping["revenue_formula"] = None

        sorted_aliases = sorted(RetailSemanticMapper.ALIAS_MAP.items(), key=lambda x: -len(x[0]))
        for semantic_key, aliases in sorted_aliases:
            ordered_aliases = sorted(set(aliases), key=len, reverse=True)
            for alias in ordered_aliases:
                for cl, original in col_lower_map.items():
                    if alias in cl:
                        mapping[semantic_key] = original
                        break
                if mapping[semantic_key]:
                    break

        if mapping.get("product_id") is None:
            for alias in ["description", "desc", "product_name", "item_name", "product_description"]:
                for cl, original in col_lower_map.items():
                    if alias in cl:
                        mapping["product_description"] = original
                        break
                if mapping.get("product_description"):
                    break

        if not mapping.get("revenue") and mapping.get("price") and mapping.get("quantity"):
            mapping["revenue_formula"] = f"{mapping['price']} * {mapping['quantity']}"
            mapping["revenue"] = mapping["price"]

        engine_mapping = {
            "order_table": None,
            "product_table": None,
            "customer_table": None,
            "category_column": None,
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
            "state_column": None,
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
            "health_score": {},
            "forecast_readiness": {},
            "computed_metrics": [],
        }

    @classmethod
    def get_canonical_model(cls, parquet_path: Path) -> Optional[CanonicalRetailModel]:
        try:
            profile = SemanticDataProfiler.profile(parquet_path)
            retail_mapping = cls.apply_retail_mapping(profile)
            return build_canonical_model(profile, retail_mapping)
        except Exception as e:
            logger.error(f"Failed to build canonical model for {parquet_path}: {str(e)}")
            return None

    @classmethod
    def is_retail_dataset(cls, profile: Dict[str, Any]) -> bool:
        col_names = list(profile.get("columns", {}).keys())
        col_lower = [c.lower() for c in col_names]
        retail_indicators = ["order", "product", "customer", "sales", "revenue", "store",
                             "cart", "checkout", "freight", "invoice", "quantity", "price"]
        matches = sum(1 for ind in retail_indicators if any(ind in col for col in col_lower))
        return matches >= 3
