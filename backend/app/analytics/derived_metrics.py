from typing import Any, Dict, List, Optional


class DerivedMetricCandidate:
    def __init__(
        self,
        metric_name: str,
        formula: str,
        source_columns: List[str],
        calculation_method: str,
        confidence: float,
        business_meaning: str,
        evidence: str,
    ):
        self.metric_name = metric_name
        self.formula = formula
        self.source_columns = source_columns
        self.calculation_method = calculation_method
        self.confidence = confidence
        self.business_meaning = business_meaning
        self.evidence = evidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "formula": self.formula,
            "source_columns": self.source_columns,
            "calculation_method": self.calculation_method,
            "confidence": self.confidence,
            "business_meaning": self.business_meaning,
            "evidence": self.evidence,
        }


def _column_matches_keywords(column_name: str, keywords: List[str]) -> bool:
    col_lower = column_name.lower().replace(" ", "_").replace("-", "_")
    return any(kw in col_lower for kw in keywords)


def _get_column_role(column_name: str, column_classifications: List[Dict[str, Any]]) -> Optional[str]:
    col_lower = column_name.lower()
    for cc in column_classifications:
        cc_name = cc.get("name", "").lower()
        if cc_name == col_lower:
            semantic_type = cc.get("semantic_type", "").lower()
            business_role = cc.get("business_role", "").lower()
            if semantic_type in (
                "identifier", "customer_id", "product_id", "transaction_id",
                "user_id", "employee_id", "order_id", "invoice_id", "session_id",
            ):
                return "identifier"
            if semantic_type == "temporal" or business_role == "temporal":
                return "date"
            if semantic_type in ("measure", "currency", "percentage") or business_role == "measure":
                if any(k in col_lower for k in ["price", "unitprice", "unit_price", "cost_price", "selling_price", "list_price", "rate", "wage", "salary", "premium"]):
                    return "unit_price"
                if any(k in col_lower for k in ["cost", "unit_cost", "cogs", "expense", "fee"]):
                    return "unit_cost"
                if any(k in col_lower for k in ["quantity", "qty", "units", "volume", "count", "number", "total_records", "records", "orders", "customers", "employees", "students", "transactions", "visits", "clicks", "impressions", "sessions", "tickets", "claims", "orders_count"]):
                    return "quantity"
                if any(k in col_lower for k in ["revenue", "sales", "amount", "total", "income", "value", "balance", "payout", "claim_amount", "transaction_amount", "score", "marks", "salary", "profit", "margin", "net"]):
                    return "revenue"
                if any(k in col_lower for k in ["rate", "ratio", "percentage", "efficiency", "density", "probability", "likelihood", "nps", "ctr", "cpc", "cpa", "roas", "margin", "growth_rate", "conversion_rate", "churn_rate", "retention_rate"]):
                    return "rate"
                if any(k in col_lower for k in ["duration", "time", "period", "interval", "hours", "minutes", "seconds", "days"]):
                    return "duration"
                return "measure"
    return None


def _derive_name(column_name: str) -> str:
    return column_name.replace("_", " ").title()


def discover_derived_metrics(
    measures: List[str],
    dimensions: List[str],
    column_classifications: List[Dict[str, Any]],
    profile: Dict[str, Any],
    domain: str = "Generic Business",
) -> List[Dict[str, Any]]:
    candidates: List[DerivedMetricCandidate] = []

    col_profiles = profile.get("columns", {})

    for m_a in measures:
        for m_b in measures:
            if m_a >= m_b:
                continue
            role_a = _get_column_role(m_a, column_classifications)
            role_b = _get_column_role(m_b, column_classifications)

            pa = col_profiles.get(m_a, {})
            pb = col_profiles.get(m_b, {})

            # Pattern A: quantity * unit_price = revenue/amount
            if role_a == "quantity" and role_b in ("unit_price", "unit_cost", "revenue"):
                confidence = 0.92
                null_penalty = 0
                if pa.get("null_percentage", 0) > 20 or pb.get("null_percentage", 0) > 20:
                    null_penalty = 0.15
                elif pa.get("null_percentage", 0) > 10 or pb.get("null_percentage", 0) > 10:
                    null_penalty = 0.10
                confidence = max(0.5, min(0.99, confidence - null_penalty))
                base_name = _derive_name(m_a.replace("_qty", "").replace("_quantity", "").replace("qty_", "").replace("quantity_", "").strip("_") or m_b.replace("_price", "").replace("_rate", "").strip("_") or "Computed")
                if not base_name or base_name.lower() in ("computed",):
                    base_name = _derive_name(m_b if role_b in ("unit_price", "unit_cost") else m_a)
                candidates.append(DerivedMetricCandidate(
                    metric_name=f"{base_name} Total",
                    formula=f"SUM({m_a} * {m_b})",
                    source_columns=[m_a, m_b],
                    calculation_method="row_level_product_aggregated",
                    confidence=round(confidence, 2),
                    business_meaning=f"Total {base_name.lower()} computed as {m_a} multiplied by {m_b}.",
                    evidence=f"Columns '{m_a}' and '{m_b}' are semantically compatible for multiplication.",
                ))

            # Pattern B: revenue - cost = profit/margin
            if role_a == "revenue" and role_b in ("unit_cost", "cost"):
                confidence = 0.93
                candidates.append(DerivedMetricCandidate(
                    metric_name=f"{_derive_name(m_a)} Net",
                    formula=f"SUM({m_a} - {m_b})",
                    source_columns=[m_a, m_b],
                    calculation_method="column_difference",
                    confidence=round(confidence, 2),
                    business_meaning=f"Net {_derive_name(m_a).lower()} computed as {m_a} minus {m_b}.",
                    evidence=f"Columns '{m_a}' and '{m_b}' are semantically compatible for difference calculation.",
                ))

            # Pattern C: revenue / quantity = average rate/price
            if role_a == "revenue" and role_b == "quantity":
                confidence = 0.90
                candidates.append(DerivedMetricCandidate(
                    metric_name=f"Average {_derive_name(m_a.replace('revenue', '').replace('sales', '').replace('amount', '').replace('total', '').strip('_') or 'Value')} Per {_derive_name(m_b)}",
                    formula=f"AVG({m_a} / NULLIF({m_b}, 0))",
                    source_columns=[m_a, m_b],
                    calculation_method="row_level_ratio",
                    confidence=round(confidence, 2),
                    business_meaning=f"Average unit value computed as {m_a} divided by {m_b}.",
                    evidence=f"Columns '{m_a}' and '{m_b}' allow per-unit ratio calculation.",
                ))

            # Pattern D: rate_a / rate_b = relative efficiency/index
            if role_a == "rate" and role_b == "rate":
                confidence = 0.85
                name_a = _derive_name(m_a)
                name_b = _derive_name(m_b)
                candidates.append(DerivedMetricCandidate(
                    metric_name=f"{name_a} Relative to {name_b}",
                    formula=f"AVG({m_a} / NULLIF({m_b}, 0))",
                    source_columns=[m_a, m_b],
                    calculation_method="ratio_of_rates",
                    confidence=round(confidence, 2),
                    business_meaning=f"Relative index comparing {name_a.lower()} against {name_b.lower()}.",
                    evidence=f"Both columns are rate-type measures enabling ratio analysis.",
                ))

            # Pattern E: generic measure_a / measure_b = ratio
            if role_a == "measure" and role_b == "measure":
                confidence = 0.75
                name_a = _derive_name(m_a)
                name_b = _derive_name(m_b)
                if "total" in name_a.lower() or "sum" in name_a.lower():
                    candidates.append(DerivedMetricCandidate(
                        metric_name=f"{name_a} Per {name_b}",
                        formula=f"SUM({m_a}) / NULLIF(COUNT({m_b}), 0)",
                        source_columns=[m_a, m_b],
                        calculation_method="aggregate_ratio",
                        confidence=round(confidence, 2),
                        business_meaning=f"Average {name_a.lower()} per {name_b.lower()}.",
                        evidence=f"Column '{m_a}' can be normalized by count of '{m_b}'.",
                    ))

            # Pattern F: measure / total_rows = per-record average
            if role_a == "measure" and role_b == "quantity":
                if "total" in m_a.lower() or "sum" in m_a.lower() or m_a.endswith("_total"):
                    continue
                confidence = 0.80
                name_a = _derive_name(m_a)
                name_b = _derive_name(m_b)
                candidates.append(DerivedMetricCandidate(
                    metric_name=f"Average {name_a} Per {name_b}",
                    formula=f"AVG({m_a})",
                    source_columns=[m_a, m_b],
                    calculation_method="per_unit_average",
                    confidence=round(confidence, 2),
                    business_meaning=f"Average {name_a.lower()} normalized by {name_b.lower()}.",
                    evidence=f"Measure '{m_a}' can be averaged to derive per-{m_b} metric.",
                ))

    # Deduplicate by source columns
    seen = set()
    unique: List[DerivedMetricCandidate] = []
    for c in candidates:
        key = tuple(sorted(c.source_columns))
        if key not in seen:
            seen.add(key)
            unique.append(c)

    return [c.to_dict() for c in unique[:8]]


def discover_transaction_identifier(
    columns: List[str],
    column_classifications: List[Dict[str, Any]],
    profile: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    col_profiles = profile.get("columns", {})
    total_rows = profile.get("total_rows", 0)

    for cc in column_classifications:
        semantic_type = cc.get("semantic_type", "").lower()
        if semantic_type == "transaction_id":
            col_name = cc.get("name", "")
            cp = col_profiles.get(col_name, {})
            distinct_count = cp.get("distinct_count", 0)
            uniqueness_ratio = distinct_count / max(total_rows, 1) if total_rows > 0 else 0.0
            confidence = 0.90
            if uniqueness_ratio > 0.8:
                confidence = 0.95
            elif uniqueness_ratio > 0.5:
                confidence = 0.90
            return {
                "column": col_name,
                "role": "transaction_id",
                "confidence": round(confidence, 2),
                "evidence": f"Semantic model classified '{col_name}' as transaction identifier with {distinct_count:,} unique values.",
                "distinct_count": distinct_count,
                "uniqueness_ratio": round(uniqueness_ratio, 4),
            }

    for col_name in columns:
        col_lower = col_name.lower()
        cp = col_profiles.get(col_name, {})
        distinct_count = cp.get("distinct_count", 0)
        uniqueness_ratio = distinct_count / max(total_rows, 1) if total_rows > 0 else 0.0

        if uniqueness_ratio > 0.7 and distinct_count > 1:
            for cc in column_classifications:
                if cc.get("name", "").lower() == col_lower:
                    semantic_type = cc.get("semantic_type", "").lower()
                    if semantic_type in ("identifier", "transaction_id"):
                        return {
                            "column": col_name,
                            "role": "transaction_id",
                            "confidence": 0.85,
                            "evidence": f"Column '{col_name}' has high uniqueness ({distinct_count:,} / {total_rows:,}) and is classified as identifier.",
                            "distinct_count": distinct_count,
                            "uniqueness_ratio": round(uniqueness_ratio, 4),
                        }

    return None


def discover_entity_columns(
    columns: List[str],
    column_classifications: List[Dict[str, Any]],
    profile: Dict[str, Any],
) -> List[Dict[str, Any]]:
    entities: List[Dict[str, Any]] = []
    col_profiles = profile.get("columns", {})

    for cc in column_classifications:
        semantic_type = cc.get("semantic_type", "").lower()
        if semantic_type in (
            "customer_id", "user_id", "employee_id", "product_id",
            "transaction_id", "device_id", "patient_id", "client_id",
            "member_id", "order_id", "invoice_id", "account_id",
        ):
            col_name = cc.get("name", "")
            cp = col_profiles.get(col_name, {})
            distinct_count = cp.get("distinct_count", 0)
            entities.append({
                "column": col_name,
                "entity_type": semantic_type.replace("_id", "").title(),
                "distinct_count": distinct_count,
                "confidence": 0.85,
            })

    return entities
