from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.retail.engine import RetailIntelligenceEngine
from app.retail.schemas import RetailAnalysisResult, RetailHealthScore


class RetailReportGenerator:
    @staticmethod
    def generate_markdown(result: RetailAnalysisResult) -> str:
        lines = []
        lines.append("# Retail Intelligence Engine Report")
        lines.append("")
        lines.append(f"**Generated At:** {result.generated_at}")
        lines.append(f"**Domain:** {result.domain}")
        lines.append(f"**Dataset Type:** {result.dataset_type}")
        lines.append(f"**Confidence Score:** {result.confidence_score:.2f}")
        lines.append("")

        if result.errors:
            lines.append("## Errors")
            for e in result.errors:
                lines.append(f"- {e}")
            lines.append("")

        lines.append("## Detected Semantic Mapping")
        lines.append("")
        if result.computed_metrics:
            lines.append(f"**Computed Metrics:** {', '.join(result.computed_metrics)}")
            lines.append("")

        lines.append("## Entities Detected")
        lines.append("")
        for ent in result.entities_detected:
            lines.append(f"- **{ent.entity_type}** (confidence: {ent.confidence:.2f})")
            if ent.matched_columns:
                lines.append(f"  - Columns: {', '.join(ent.matched_columns)}")
        lines.append("")

        lines.append("## Column Semantics")
        lines.append("")
        for cs in result.column_semantics:
            lines.append(f"- `{cs.column_name}` → **{cs.semantic_role}** (confidence: {cs.confidence:.2f})")
        lines.append("")

        lines.append("## Health Score")
        lines.append("")
        hs = result.health_score
        lines.append(f"- **Overall Score:** {hs.overall_score:.2f}")
        lines.append(f"- **Grade:** {hs.grade}")
        lines.append(f"- **Status:** {hs.status}")
        lines.append("")
        if hs.breakdown:
            lines.append("### Breakdown")
            for item in hs.breakdown:
                lines.append(f"- {item.get('component', 'N/A')}: {item.get('score', 0.0):.2f}")
            lines.append("")

        lines.append("## Forecast Readiness")
        lines.append("")
        fr = result.forecast_readiness
        if isinstance(fr, dict):
            lines.append(f"- **Ready:** {fr.get('ready', False)}")
            lines.append(f"- **Strategy:** {fr.get('strategy', 'none')}")
            if fr.get("reasons"):
                for reason in fr["reasons"]:
                    lines.append(f"- {reason}")
        lines.append("")

        if result.forecast:
            lines.append("## Forecast")
            lines.append("")
            lines.append("| Period | Value | Method | Confidence |")
            lines.append("|--------|-------|--------|------------|")
            for item in result.forecast:
                lines.append(f"| {item.get('period', 'N/A')} | {item.get('value', 0.0):,.2f} | {item.get('method', 'N/A')} | {item.get('confidence', 0.0):.2f} |")
            lines.append("")

        lines.append("## KPIs")
        lines.append("")
        for kpi in result.kpis:
            lines.append(f"### {kpi.name}")
            lines.append(f"- **Value:** {kpi.formatted_value}")
            lines.append(f"- **Explanation:** {kpi.business_explanation}")
            lines.append(f"- **Evidence:** {kpi.evidence}")
            lines.append(f"- **Confidence:** {kpi.confidence:.2f}")
            lines.append(f"- **Business Impact:** {kpi.business_impact}")
            lines.append(f"- **Calculation:** `{kpi.calculation}`")
            if kpi.source_columns:
                lines.append(f"- **Source Columns:** {', '.join(kpi.source_columns)}")
            lines.append("")

        lines.append("## Top Categories")
        lines.append("")
        if result.top_categories:
            for item in result.top_categories:
                lines.append(f"- {item['category']}: {item['value']:,.2f} ({item['percentage']:.2f}%)")
        else:
            lines.append("No category data available.")
        lines.append("")

        lines.append("## Top Products")
        lines.append("")
        if result.top_products:
            for item in result.top_products:
                lines.append(f"- {item['product']}: {item['value']:,.2f}")
        else:
            lines.append("No product data available.")
        lines.append("")

        lines.append("## Top Customers")
        lines.append("")
        if result.top_customers:
            for item in result.top_customers:
                lines.append(f"- {item['customer']}: {item['value']:,.2f}")
        else:
            lines.append("No customer data available.")
        lines.append("")

        lines.append("## Revenue Trend")
        lines.append("")
        if result.revenue_trend:
            lines.append("| Period | Value |")
            lines.append("|--------|-------|")
            for item in result.revenue_trend:
                lines.append(f"| {item['period']} | {item['value']:,.2f} |")
        else:
            lines.append("No revenue trend data available.")
        lines.append("")

        lines.append("## Freight Analysis")
        lines.append("")
        if result.freight_analysis:
            for item in result.freight_analysis:
                lines.append(f"- Total Freight: {item['total_freight']:,.2f}")
                lines.append(f"- Average Freight: {item['avg_freight']:,.2f}")
                lines.append(f"- Freight to Revenue %: {item['freight_to_revenue_pct']:.2f}%")
        else:
            lines.append("No freight data available.")
        lines.append("")

        lines.append("## Delivery Performance")
        lines.append("")
        if result.delivery_performance:
            for item in result.delivery_performance:
                lines.append(f"- Average: {item['avg_delivery']:,.2f}")
                lines.append(f"- Min: {item['min_delivery']:,.2f}")
                lines.append(f"- Max: {item['max_delivery']:,.2f}")
        else:
            lines.append("No delivery data available.")
        lines.append("")

        lines.append("## Payment Analysis")
        lines.append("")
        if result.payment_analysis:
            lines.append("| Method | Count | Revenue | % of Total |")
            lines.append("|--------|-------|---------|------------|")
            for item in result.payment_analysis:
                lines.append(f"| {item['payment_method']} | {item['tx_count']} | {item['revenue']:,.2f} | {item['pct_of_total']:.2f}% |")
        else:
            lines.append("No payment data available.")
        lines.append("")

        lines.append("## Review Analysis")
        lines.append("")
        if result.review_analysis:
            for item in result.review_analysis:
                lines.append(f"- Average Score: {item['avg_score']:,.2f}")
                lines.append(f"- Min Score: {item['min_score']:,.2f}")
                lines.append(f"- Max Score: {item['max_score']:,.2f}")
                lines.append(f"- Review Count: {item['review_count']}")
        else:
            lines.append("No review data available.")
        lines.append("")

        lines.append("## Store Performance")
        lines.append("")
        if result.store_performance:
            lines.append("| Store | Revenue | Orders |")
            lines.append("|-------|---------|--------|")
            for item in result.store_performance:
                lines.append(f"| {item['store']} | {item['revenue']:,.2f} | {item['orders']} |")
        else:
            lines.append("No store data available.")
        lines.append("")

        lines.append("## Regional Performance")
        lines.append("")
        if result.regional_performance:
            lines.append("| Region | Revenue | Orders |")
            lines.append("|--------|---------|--------|")
            for item in result.regional_performance:
                lines.append(f"| {item['region']} | {item['revenue']:,.2f} | {item['orders']} |")
        else:
            lines.append("No regional data available.")
        lines.append("")

        lines.append("## Inventory Health")
        lines.append("")
        if result.inventory_health:
            lines.append("| Product | Stock |")
            lines.append("|---------|-------|")
            for item in result.inventory_health:
                lines.append(f"| {item['product']} | {item['total_stock']:,.2f} |")
        else:
            lines.append("No inventory data available.")
        lines.append("")

        lines.append("## Additional Metrics")
        lines.append("")
        if result.avg_order_value:
            lines.append(f"**Average Order Value:** {result.avg_order_value.get('formatted', 'N/A')}")
        if result.order_count:
            lines.append(f"**Order Count:** {result.order_count.get('formatted', 'N/A')}")
        if result.customer_count:
            lines.append(f"**Customer Count:** {result.customer_count.get('formatted', 'N/A')}")
        if result.returning_customers:
            lines.append(f"**Returning Customers:** {result.returning_customers.get('formatted', 'N/A')}")
        if result.total_revenue:
            lines.append(f"**Total Revenue:** {result.total_revenue.get('formatted', 'N/A')}")
        lines.append("")

        lines.append("## Evidence")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(result.evidence, indent=2, default=str))
        lines.append("```")
        lines.append("")

        if result.sql_queries:
            lines.append("## SQL Queries")
            lines.append("")
            for q in result.sql_queries:
                lines.append(f"- {q}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def save_report(result: RetailAnalysisResult, output_path: Path) -> None:
        md = RetailReportGenerator.generate_markdown(result)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md)
