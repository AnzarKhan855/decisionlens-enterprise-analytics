from __future__ import annotations

from typing import Any, Dict, List, Optional
from pathlib import Path
import duckdb

from app.database.duckdb_engine import DuckDBEngine
from app.retail.canonical_model import CanonicalRetailModel, get_revenue_formula
from app.ai.explainable_ai_engine import ExplainableAIEngine
from app.schemas.analytics import KPIMetric


class RetailKPIEngine:
    """
    Comprehensive Retail KPI Engine.

    Automatically computes all retail-specific KPIs from a canonical model.
    Every KPI contains:
      - Value
      - Evidence
      - Formula
      - Confidence
      - Business Meaning
      - Business Impact
    """

    @classmethod
    def compute_all_kpis(
        cls,
        parquet_path: Path,
        canonical_model: CanonicalRetailModel,
        profile: Optional[Dict[str, Any]] = None,
    ) -> List[KPIMetric]:
        kpis: List[KPIMetric] = []
        if not parquet_path.exists():
            return kpis

        path_str = str(parquet_path).replace("\\", "/")
        total_rows = profile.get("total_rows", 0) if profile else 0
        confidence_result = ExplainableAIEngine.compute_confidence(profile=profile or {})
        base_confidence = confidence_result.evidence_score

        def _safe_query(sql: str) -> Optional[Dict[str, Any]]:
            try:
                res = DuckDBEngine.query(sql)
                return res[0] if res else None
            except Exception:
                return None

        # Revenue KPIs
        revenue_col = canonical_model.revenue_column
        revenue_formula = get_revenue_formula(canonical_model)
        if revenue_col:
            safe_rev = cls._escape(revenue_col)
            row = _safe_query(f"SELECT SUM({safe_rev}) as total_rev, AVG({safe_rev}) as avg_rev, MIN({safe_rev}) as min_rev, MAX({safe_rev}) as max_rev FROM read_parquet('{path_str}')")
            if row:
                total_rev = float(row.get("total_rev", 0) or 0)
                kpis.append(KPIMetric(
                    name="Total Revenue",
                    value=total_rev,
                    formatted_value=f"{total_rev:,.2f}",
                    metric_type="Revenue",
                    source_column=revenue_col,
                    formula=f"SUM({revenue_col})",
                    rows_analyzed=total_rows,
                    confidence=round(base_confidence, 2),
                    evidence=f"Sum of {revenue_col} across {total_rows:,} records.",
                    business_meaning="Total monetary value of all transactions.",
                    business_impact="Primary indicator of business performance and growth.",
                ))
                avg_rev = float(row.get("avg_rev", 0) or 0)
                kpis.append(KPIMetric(
                    name="Average Transaction Value",
                    value=avg_rev,
                    formatted_value=f"{avg_rev:,.2f}",
                    metric_type="Revenue",
                    source_column=revenue_col,
                    formula=f"AVG({revenue_col})",
                    rows_analyzed=total_rows,
                    confidence=round(base_confidence, 2),
                    evidence=f"Average of {revenue_col} across {total_rows:,} records.",
                    business_meaning="Mean value per transaction.",
                    business_impact="Helps understand customer spending patterns.",
                ))
        elif revenue_formula and canonical_model.price_column and canonical_model.quantity_column:
            price_col = canonical_model.price_column
            qty_col = canonical_model.quantity_column
            safe_price = cls._escape(price_col)
            safe_qty = cls._escape(qty_col)
            row = _safe_query(f"SELECT SUM({safe_price} * {safe_qty}) as total_rev FROM read_parquet('{path_str}')")
            if row:
                total_rev = float(row.get("total_rev", 0) or 0)
                kpis.append(KPIMetric(
                    name="Total Revenue (Computed)",
                    value=total_rev,
                    formatted_value=f"{total_rev:,.2f}",
                    metric_type="Revenue",
                    source_column=f"{price_col} * {qty_col}",
                    formula=f"SUM({price_col} * {qty_col})",
                    rows_analyzed=total_rows,
                    confidence=round(base_confidence, 2),
                    evidence=f"Computed as SUM({price_col} * {qty_col}) across {total_rows:,} records.",
                    business_meaning="Total revenue derived from price × quantity.",
                    business_impact="Primary indicator of business performance when direct revenue column is unavailable.",
                ))

        # Order Count
        if canonical_model.order_id_column:
            safe_oid = cls._escape(canonical_model.order_id_column)
            row = _safe_query(f"SELECT COUNT(DISTINCT {safe_oid}) as order_count FROM read_parquet('{path_str}')")
            if row:
                order_count = int(row.get("order_count", 0) or 0)
                kpis.append(KPIMetric(
                    name="Total Orders",
                    value=order_count,
                    formatted_value=f"{order_count:,}",
                    metric_type="Order Count",
                    source_column=canonical_model.order_id_column,
                    formula=f"COUNT(DISTINCT {canonical_model.order_id_column})",
                    rows_analyzed=total_rows,
                    confidence=round(base_confidence, 2),
                    evidence=f"Distinct count of {canonical_model.order_id_column}.",
                    business_meaning="Total number of unique orders placed.",
                    business_impact="Core volume metric for sales performance.",
                ))

        # Customer Count
        if canonical_model.customer_id_column:
            safe_cid = cls._escape(canonical_model.customer_id_column)
            row = _safe_query(f"SELECT COUNT(DISTINCT {safe_cid}) as customer_count FROM read_parquet('{path_str}')")
            if row:
                customer_count = int(row.get("customer_count", 0) or 0)
                kpis.append(KPIMetric(
                    name="Total Customers",
                    value=customer_count,
                    formatted_value=f"{customer_count:,}",
                    metric_type="Customer Count",
                    source_column=canonical_model.customer_id_column,
                    formula=f"COUNT(DISTINCT {canonical_model.customer_id_column})",
                    rows_analyzed=total_rows,
                    confidence=round(base_confidence, 2),
                    evidence=f"Distinct count of {canonical_model.customer_id_column}.",
                    business_meaning="Total number of unique customers.",
                    business_impact="Measures customer base size and market reach.",
                ))

        # Product Count
        if canonical_model.product_id_column:
            safe_pid = cls._escape(canonical_model.product_id_column)
            row = _safe_query(f"SELECT COUNT(DISTINCT {safe_pid}) as product_count FROM read_parquet('{path_str}')")
            if row:
                product_count = int(row.get("product_count", 0) or 0)
                kpis.append(KPIMetric(
                    name="Total Products",
                    value=product_count,
                    formatted_value=f"{product_count:,}",
                    metric_type="Product Count",
                    source_column=canonical_model.product_id_column,
                    formula=f"COUNT(DISTINCT {canonical_model.product_id_column})",
                    rows_analyzed=total_rows,
                    confidence=round(base_confidence, 2),
                    evidence=f"Distinct count of {canonical_model.product_id_column}.",
                    business_meaning="Total number of unique products sold.",
                    business_impact="Indicates catalog diversity and product range.",
                ))

        # Category Count
        if canonical_model.category_column:
            safe_cat = cls._escape(canonical_model.category_column)
            row = _safe_query(f"SELECT COUNT(DISTINCT {safe_cat}) as category_count FROM read_parquet('{path_str}')")
            if row:
                category_count = int(row.get("category_count", 0) or 0)
                kpis.append(KPIMetric(
                    name="Total Categories",
                    value=category_count,
                    formatted_value=f"{category_count:,}",
                    metric_type="Category Count",
                    source_column=canonical_model.category_column,
                    formula=f"COUNT(DISTINCT {canonical_model.category_column})",
                    rows_analyzed=total_rows,
                    confidence=round(base_confidence, 2),
                    evidence=f"Distinct count of {canonical_model.category_column}.",
                    business_meaning="Total number of product categories.",
                    business_impact="Shows business diversification across categories.",
                ))

        # Country Count
        if canonical_model.country_column:
            safe_cty = cls._escape(canonical_model.country_column)
            row = _safe_query(f"SELECT COUNT(DISTINCT {safe_cty}) as country_count FROM read_parquet('{path_str}')")
            if row:
                country_count = int(row.get("country_count", 0) or 0)
                kpis.append(KPIMetric(
                    name="Total Countries",
                    value=country_count,
                    formatted_value=f"{country_count:,}",
                    metric_type="Country Count",
                    source_column=canonical_model.country_column,
                    formula=f"COUNT(DISTINCT {canonical_model.country_column})",
                    rows_analyzed=total_rows,
                    confidence=round(base_confidence, 2),
                    evidence=f"Distinct count of {canonical_model.country_column}.",
                    business_meaning="Geographic reach of the business.",
                    business_impact="Indicates market coverage and international presence.",
                ))

        # Average Order Value
        if canonical_model.order_id_column and revenue_col:
            safe_oid = cls._escape(canonical_model.order_id_column)
            safe_rev = cls._escape(revenue_col)
            row = _safe_query(f"SELECT SUM({safe_rev}) / COUNT(DISTINCT {safe_oid}) as aov FROM read_parquet('{path_str}')")
            if row:
                aov = float(row.get("aov", 0) or 0)
                kpis.append(KPIMetric(
                    name="Average Order Value",
                    value=aov,
                    formatted_value=f"{aov:,.2f}",
                    metric_type="Revenue",
                    source_column=f"{revenue_col} / {canonical_model.order_id_column}",
                    formula=f"SUM({revenue_col}) / COUNT(DISTINCT {canonical_model.order_id_column})",
                    rows_analyzed=total_rows,
                    confidence=round(base_confidence, 2),
                    evidence=f"Total revenue divided by distinct order count.",
                    business_meaning="Average monetary value per order.",
                    business_impact="Key metric for pricing strategy and upselling opportunities.",
                ))

        # Average Basket Size
        if canonical_model.order_id_column and canonical_model.quantity_column:
            safe_oid = cls._escape(canonical_model.order_id_column)
            safe_qty = cls._escape(canonical_model.quantity_column)
            row = _safe_query(f"SELECT SUM({safe_qty}) / COUNT(DISTINCT {safe_oid}) as avg_basket FROM read_parquet('{path_str}')")
            if row:
                avg_basket = float(row.get("avg_basket", 0) or 0)
                kpis.append(KPIMetric(
                    name="Average Basket Size",
                    value=avg_basket,
                    formatted_value=f"{avg_basket:,.2f}",
                    metric_type="Quantity",
                    source_column=f"{canonical_model.quantity_column} / {canonical_model.order_id_column}",
                    formula=f"SUM({canonical_model.quantity_column}) / COUNT(DISTINCT {canonical_model.order_id_column})",
                    rows_analyzed=total_rows,
                    confidence=round(base_confidence, 2),
                    evidence=f"Total quantity divided by distinct order count.",
                    business_meaning="Average number of items per order.",
                    business_impact="Indicates cross-selling and bundling effectiveness.",
                ))

        # Average Unit Price
        if canonical_model.price_column:
            safe_price = cls._escape(canonical_model.price_column)
            row = _safe_query(f"SELECT AVG({safe_price}) as avg_price FROM read_parquet('{path_str}')")
            if row:
                avg_price = float(row.get("avg_price", 0) or 0)
                kpis.append(KPIMetric(
                    name="Average Unit Price",
                    value=avg_price,
                    formatted_value=f"{avg_price:,.2f}",
                    metric_type="Price",
                    source_column=canonical_model.price_column,
                    formula=f"AVG({canonical_model.price_column})",
                    rows_analyzed=total_rows,
                    confidence=round(base_confidence, 2),
                    evidence=f"Average of {canonical_model.price_column}.",
                    business_meaning="Mean selling price per unit.",
                    business_impact="Key input for pricing strategy and margin analysis.",
                ))

        # Repeat Customers
        if canonical_model.customer_id_column and canonical_model.order_id_column:
            safe_cid = cls._escape(canonical_model.customer_id_column)
            safe_oid = cls._escape(canonical_model.order_id_column)
            row = _safe_query(f"""
                SELECT COUNT(*) as repeat_customers FROM (
                    SELECT {safe_cid} FROM read_parquet('{path_str}')
                    GROUP BY {safe_cid}
                    HAVING COUNT(DISTINCT {safe_oid}) > 1
                )
            """)
            if row:
                repeat_customers = int(row.get("repeat_customers", 0) or 0)
                kpis.append(KPIMetric(
                    name="Repeat Customers",
                    value=repeat_customers,
                    formatted_value=f"{repeat_customers:,}",
                    metric_type="Customer Count",
                    source_column=canonical_model.customer_id_column,
                    formula=f"COUNT of customers with COUNT(DISTINCT orders) > 1",
                    rows_analyzed=total_rows,
                    confidence=round(base_confidence, 2),
                    evidence=f"Customers with more than one distinct order.",
                    business_meaning="Number of customers who made multiple purchases.",
                    business_impact="Indicator of customer loyalty and retention.",
                ))

        # Profit
        if canonical_model.profit_column:
            safe_profit = cls._escape(canonical_model.profit_column)
            row = _safe_query(f"SELECT SUM({safe_profit}) as total_profit FROM read_parquet('{path_str}')")
            if row:
                total_profit = float(row.get("total_profit", 0) or 0)
                kpis.append(KPIMetric(
                    name="Total Profit",
                    value=total_profit,
                    formatted_value=f"{total_profit:,.2f}",
                    metric_type="Profit",
                    source_column=canonical_model.profit_column,
                    formula=f"SUM({canonical_model.profit_column})",
                    rows_analyzed=total_rows,
                    confidence=round(base_confidence, 2),
                    evidence=f"Sum of {canonical_model.profit_column}.",
                    business_meaning="Total profit generated from sales.",
                    business_impact="Core profitability metric for financial analysis.",
                ))

        # Gross Sales (Revenue without returns/refunds)
        if canonical_model.revenue_column or revenue_formula:
            rev_col_safe = cls._escape(revenue_col) if revenue_col else None
            if rev_col_safe:
                row = _safe_query(f"SELECT SUM({rev_col_safe}) as gross_sales FROM read_parquet('{path_str}') WHERE {rev_col_safe} >= 0")
                if row:
                    gross_sales = float(row.get("gross_sales", 0) or 0)
                    kpis.append(KPIMetric(
                        name="Gross Sales",
                        value=gross_sales,
                        formatted_value=f"{gross_sales:,.2f}",
                        metric_type="Revenue",
                        source_column=revenue_col or revenue_formula,
                        formula=f"SUM({revenue_col or revenue_formula}) WHERE value >= 0",
                        rows_analyzed=total_rows,
                        confidence=round(base_confidence, 2),
                        evidence=f"Total positive-value transactions.",
                        business_meaning="Gross sales before refunds and returns.",
                        business_impact="Baseline for revenue recognition and sales analysis.",
                    ))

        # Monthly Sales
        if canonical_model.date_column and (canonical_model.revenue_column or revenue_formula):
            date_col = canonical_model.date_column
            rev_col = revenue_col
            if rev_col:
                safe_date = cls._escape(date_col)
                safe_rev = cls._escape(rev_col)
                row = _safe_query(f"""
                    SELECT
                        strftime(CAST({safe_date} AS TIMESTAMP), '%Y-%m') as month,
                        SUM({safe_rev}) as monthly_revenue
                    FROM read_parquet('{path_str}')
                    WHERE {safe_date} IS NOT NULL
                    GROUP BY month
                    ORDER BY month DESC
                    LIMIT 1
                """)
                if row:
                    monthly_revenue = float(row.get("monthly_revenue", 0) or 0)
                    kpis.append(KPIMetric(
                        name="Latest Monthly Revenue",
                        value=monthly_revenue,
                        formatted_value=f"{monthly_revenue:,.2f}",
                        metric_type="Revenue",
                        source_column=f"{date_col} + {rev_col}",
                        formula=f"SUM({rev_col}) GROUP BY month",
                        rows_analyzed=total_rows,
                        confidence=round(base_confidence, 2),
                        evidence=f"Revenue for most recent month with data.",
                        business_meaning="Most recent monthly revenue figure.",
                        business_impact="Tracks short-term revenue trajectory.",
                    ))

        # Daily Orders
        if canonical_model.date_column and canonical_model.order_id_column:
            safe_date = cls._escape(canonical_model.date_column)
            safe_oid = cls._escape(canonical_model.order_id_column)
            row = _safe_query(f"""
                SELECT
                    CAST({safe_date} AS DATE) as day,
                    COUNT(DISTINCT {safe_oid}) as daily_orders
                FROM read_parquet('{path_str}')
                WHERE {safe_date} IS NOT NULL
                GROUP BY day
                ORDER BY day DESC
                LIMIT 1
            """)
            if row:
                daily_orders = int(row.get("daily_orders", 0) or 0)
                kpis.append(KPIMetric(
                    name="Latest Daily Orders",
                    value=daily_orders,
                    formatted_value=f"{daily_orders:,}",
                    metric_type="Order Count",
                    source_column=f"{canonical_model.date_column} + {canonical_model.order_id_column}",
                    formula=f"COUNT(DISTINCT {canonical_model.order_id_column}) GROUP BY day",
                    rows_analyzed=total_rows,
                    confidence=round(base_confidence, 2),
                    evidence=f"Order count for most recent day with data.",
                    business_meaning="Daily order volume on the latest transaction date.",
                    business_impact="Measures short-term sales velocity.",
                ))

        # Top Categories
        if canonical_model.category_column and (canonical_model.revenue_column or revenue_formula):
            cat_col = canonical_model.category_column
            rev_col = canonical_model.revenue_column
            if rev_col:
                safe_cat = cls._escape(cat_col)
                safe_rev = cls._escape(rev_col)
                row = _safe_query(f"""
                    SELECT {safe_cat} as category, SUM({safe_rev}) as revenue
                    FROM read_parquet('{path_str}')
                    WHERE {safe_cat} IS NOT NULL
                    GROUP BY category
                    ORDER BY revenue DESC
                    LIMIT 1
                """)
                if row:
                    top_cat = str(row.get("category", ""))
                    top_cat_rev = float(row.get("revenue", 0) or 0)
                    kpis.append(KPIMetric(
                        name="Top Category",
                        value=top_cat_rev,
                        formatted_value=f"{top_cat_rev:,.2f}",
                        metric_type="Revenue",
                        source_column=f"{cat_col} + {rev_col}",
                        formula=f"SUM({rev_col}) GROUP BY {cat_col} ORDER BY revenue DESC LIMIT 1",
                        rows_analyzed=total_rows,
                        confidence=round(base_confidence, 2),
                        evidence=f"Highest revenue category: {top_cat}",
                        business_meaning="Category with highest revenue contribution.",
                        business_impact="Identifies key revenue drivers and category focus areas.",
                    ))

        # Top Products
        if canonical_model.product_id_column and (canonical_model.revenue_column or revenue_formula):
            prod_col = canonical_model.product_id_column
            rev_col = canonical_model.revenue_column
            if rev_col:
                safe_prod = cls._escape(prod_col)
                safe_rev = cls._escape(rev_col)
                row = _safe_query(f"""
                    SELECT {safe_prod} as product, SUM({safe_rev}) as revenue
                    FROM read_parquet('{path_str}')
                    WHERE {safe_prod} IS NOT NULL
                    GROUP BY product
                    ORDER BY revenue DESC
                    LIMIT 1
                """)
                if row:
                    top_prod = str(row.get("product", ""))
                    top_prod_rev = float(row.get("revenue", 0) or 0)
                    kpis.append(KPIMetric(
                        name="Top Product",
                        value=top_prod_rev,
                        formatted_value=f"{top_prod_rev:,.2f}",
                        metric_type="Revenue",
                        source_column=f"{prod_col} + {rev_col}",
                        formula=f"SUM({rev_col}) GROUP BY {prod_col} ORDER BY revenue DESC LIMIT 1",
                        rows_analyzed=total_rows,
                        confidence=round(base_confidence, 2),
                        evidence=f"Highest revenue product: {top_prod}",
                        business_meaning="Product with highest revenue contribution.",
                        business_impact="Identifies star products and inventory priorities.",
                    ))

        # Growth Rate (if date column available)
        if canonical_model.date_column and (canonical_model.revenue_column or revenue_formula):
            date_col = canonical_model.date_column
            rev_col = canonical_model.revenue_column
            if rev_col:
                safe_date = cls._escape(date_col)
                safe_rev = cls._escape(rev_col)
                row = _safe_query(f"""
                    SELECT
                        SUM(CASE WHEN strftime(CAST({safe_date} AS TIMESTAMP), '%Y-%m') = strftime(now(), '%Y-%m') THEN {safe_rev} ELSE 0 END) as current_month,
                        SUM(CASE WHEN strftime(CAST({safe_date} AS TIMESTAMP), '%Y-%m') = strftime(date_sub('month', 1, now()), '%Y-%m') THEN {safe_rev} ELSE 0 END) as prev_month
                    FROM read_parquet('{path_str}')
                """)
                if row:
                    current = float(row.get("current_month", 0) or 0)
                    prev = float(row.get("prev_month", 0) or 0)
                    if prev > 0:
                        growth_pct = ((current - prev) / prev) * 100
                        kpis.append(KPIMetric(
                            name="Month-over-Month Growth",
                            value=growth_pct,
                            formatted_value=f"{growth_pct:+.2f}%",
                            metric_type="Growth",
                            source_column=f"{date_col} + {rev_col}",
                            formula="(Current Month Revenue - Previous Month Revenue) / Previous Month Revenue × 100",
                            rows_analyzed=total_rows,
                            confidence=round(base_confidence, 2),
                            evidence=f"Current: {current:,.2f}, Previous: {prev:,.2f}",
                            business_meaning="Percentage change in revenue from previous month.",
                            business_impact="Measures short-term growth trajectory and business momentum.",
                        ))

        # Fallback: if no specific KPIs were added, add a record count
        if not kpis:
            kpis.append(KPIMetric(
                name="Total Records",
                value=total_rows,
                formatted_value=f"{total_rows:,}",
                metric_type="Record Count",
                source_column="*",
                formula="COUNT(*)",
                rows_analyzed=total_rows,
                confidence=round(base_confidence, 2),
                evidence=f"Total row count in dataset.",
                business_meaning="Total number of records in the dataset.",
                business_impact="Indicates dataset size and coverage.",
            ))

        return kpis

    @staticmethod
    def _escape(col: str) -> str:
        return f'"{col}"' if col else ""
