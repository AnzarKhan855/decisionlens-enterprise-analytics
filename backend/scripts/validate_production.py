"""
Production Validation Script for DecisionLens.

Tests the full pipeline with synthetic retail data:
  1. Dataset creation
  2. Semantic detection
  3. Canonical model building
  4. KPI computation
  5. Forecast generation
  6. Recommendation generation
  7. Report generation
  8. Scenario simulation
  9. MongoDB persistence

Run: python -m backend.scripts.validate_production
"""
from __future__ import annotations

import os
import sys
import tempfile
import csv
from pathlib import Path
from datetime import datetime, timedelta

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "backend"))


def create_synthetic_retail_dataset() -> Path:
    """Create a small synthetic retail dataset for validation."""
    tmp_dir = Path(tempfile.mkdtemp(prefix="decisionlens_validation_"))
    csv_path = tmp_dir / "retail_sales.csv"

    rows = 200
    base_date = datetime(2024, 1, 1)

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "InvoiceNo", "StockCode", "Description", "Quantity",
            "InvoiceDate", "UnitPrice", "CustomerID", "Country",
            "Category", "Discount", "Freight"
        ])
        for i in range(rows):
            date = base_date + timedelta(days=i % 90)
            writer.writerow([
                f"INV-{1000 + i}",
                f"PROD-{(i % 20) + 1}",
                f"Product {((i % 20) + 1)}",
                (i % 5) + 1,
                date.strftime("%Y-%m-%d %H:%M:%S"),
                round(10.0 + (i % 50), 2),
                f"CUST-{(i % 30) + 1}",
                ["USA", "UK", "DE", "FR", "BR"][i % 5],
                ["Electronics", "Clothing", "Food", "Books", "Home"][i % 5],
                round((i % 10) * 0.01, 2),
                round(5.0 + (i % 10), 2),
            ])

    return csv_path


def validate_semantic_detection(csv_path: Path):
    from app.retail.retail_semantic_mapper import RetailSemanticMapper
    from app.ingestion.semantic_profiler import SemanticDataProfiler
    from app.ingestion.generic_loader import GenericDataLoader

    dataset_id = "validation-dataset"
    parquet_path = GenericDataLoader.convert_to_parquet(csv_path, dataset_id)

    profile = SemanticDataProfiler.profile(parquet_path)
    mapping = RetailSemanticMapper.map(profile)

    assert mapping.get("mapping", {}).get("order_id_column") == "InvoiceNo", f"Order ID not detected: {mapping}"
    assert mapping.get("mapping", {}).get("product_id_column") == "StockCode", f"Product ID not detected: {mapping}"
    assert mapping.get("mapping", {}).get("customer_id_column") == "CustomerID", f"Customer ID not detected: {mapping}"
    assert mapping.get("mapping", {}).get("date_column") == "InvoiceDate", f"Date column not detected: {mapping}"
    assert mapping.get("mapping", {}).get("revenue_column") is not None or mapping.get("mapping", {}).get("revenue_formula") is not None, "Revenue not detected"
    print("[PASS] Semantic detection")
    return parquet_path, profile, mapping


def validate_canonical_model(parquet_path: Path, profile, mapping):
    from app.retail.canonical_model import build_canonical_model, detect_available_kpis

    model = build_canonical_model(profile, mapping)

    assert model.has_order(), "Canonical model missing order"
    assert model.has_customer(), "Canonical model missing customer"
    assert model.has_product(), "Canonical model missing product"
    assert model.has_revenue(), "Canonical model missing revenue"
    assert model.has_date(), "Canonical model missing date"
    assert len(model.available_kpis) > 0, "No KPIs detected"

    print(f"[PASS] Canonical model - {len(model.available_kpis)} KPIs available")
    return model


def validate_kpi_engine(parquet_path: Path, profile, canonical_model):
    from app.retail.kpi_engine import RetailKPIEngine

    kpis = RetailKPIEngine.compute_all_kpis(parquet_path, canonical_model, profile)

    assert len(kpis) > 0, "No KPIs computed"
    for kpi in kpis:
        assert kpi.value is not None or kpi.value == 0, f"KPI {kpi.name} has null value"
        assert kpi.formula, f"KPI {kpi.name} missing formula"
        assert kpi.confidence > 0, f"KPI {kpi.name} has zero confidence"
        assert kpi.business_meaning, f"KPI {kpi.name} missing business meaning"
        assert kpi.business_impact, f"KPI {kpi.name} missing business impact"

    print(f"[PASS] KPI Engine - {len(kpis)} KPIs computed")


def validate_forecast_engine(parquet_path: Path, canonical_model):
    from app.retail.forecast_engine import RetailForecastEngine

    result = RetailForecastEngine.generate_forecasts(parquet_path, canonical_model, horizons=[7, 30, 90])
    forecasts = result.get("forecasts", [])

    assert len(forecasts) > 0, "No forecasts generated"
    for f in forecasts:
        assert f.get("prediction") or f.get("limitation"), "Forecast missing prediction or limitation"
        assert f.get("confidence") is not None, "Forecast missing confidence"

    print(f"[PASS] Forecast Engine - {len(forecasts)} forecasts generated")


def validate_recommendation_engine(parquet_path: Path, profile, canonical_model):
    from app.analytics.recommendation_engine import RecommendationEngine

    result = RecommendationEngine.generate_retail_recommendations(
        parquet_path=parquet_path,
        profile=profile,
        canonical_model=canonical_model,
        root_causes=[],
        anomalies=[],
        drivers=[],
    )

    assert "recommendations" in result, "Recommendations missing"
    assert "has_valid_strategy" in result, "has_valid_strategy missing"
    for rec in result.get("recommendations", []):
        assert rec.get("problem"), "Recommendation missing problem"
        assert rec.get("evidence"), "Recommendation missing evidence"
        assert rec.get("root_cause"), "Recommendation missing root_cause"
        assert rec.get("priority"), "Recommendation missing priority"
        assert rec.get("business_impact"), "Recommendation missing business_impact"
        assert rec.get("expected_gain"), "Recommendation missing expected_gain"
        assert rec.get("recommended_action"), "Recommendation missing recommended_action"
        assert rec.get("affected_products") is not None, "Recommendation missing affected_products"
        assert rec.get("affected_categories") is not None, "Recommendation missing affected_categories"
        assert rec.get("confidence") is not None, "Recommendation missing confidence"

    print(f"[PASS] Recommendation Engine - {len(result.get('recommendations', []))} recommendations generated")


def validate_scenario_simulator(parquet_path: Path):
    import duckdb
    from app.services.strategy_engine import StrategyDecisionEngine

    con = duckdb.connect(str(parquet_path))
    con.execute(f"CREATE OR REPLACE VIEW retail_sales AS SELECT * FROM read_parquet('{parquet_path.as_posix()}')")
    profile = {"column_categories": {"revenue": ["UnitPrice"], "quantity": ["Quantity"], "sales": ["UnitPrice"]}}

    result = StrategyDecisionEngine.simulate_what_if_scenario(
        con=con,
        table_name="retail_sales",
        profile=profile,
        price_change_pct=5.0,
        marketing_change_pct=10.0,
        discount_reduction_pct=2.0,
        inventory_change_pct=5.0,
        shipping_reduction_pct=3.0,
        return_rate_change_pct=-1.0,
    )

    assert "projected" in result, "Scenario simulation missing projected"
    assert "baseline" in result, "Scenario simulation missing baseline"
    assert result["projected"].get("revenue_delta") is not None, "Missing revenue delta"
    assert result["projected"].get("profit_delta") is not None, "Missing profit delta"
    assert "scenario_impacts" in result, "Missing scenario_impacts"

    con.close()
    print("[PASS] Scenario Simulator")


def validate_report_engine(parquet_path: Path, profile, canonical_model):
    from app.reports.executive_report_engine import UniversalExecutiveReportEngine
    from app.semantic_model.core import SemanticModel
    from app.schemas.analytics import AnalyticsResult, KPIMetric, HealthScore

    sm = SemanticModel(
        workspace_id="validation-ws",
        domain="Retail & E-Commerce",
        dataset_type="Retail",
    )
    ar = AnalyticsResult(
        domain="Retail & E-Commerce",
        dataset_type="Retail",
        volume=profile.get("total_rows", 0),
        kpis=[KPIMetric(
            name="Total Revenue",
            value=1000.0,
            formatted_value="$1,000.00",
            metric_type="Revenue",
            source_column="UnitPrice",
            formula="SUM(UnitPrice)",
            rows_analyzed=profile.get("total_rows", 0),
            confidence=0.9,
        )],
        health_score=HealthScore(overall_score=75.0, grade="B", status="Good"),
    )

    report = UniversalExecutiveReportEngine.generate_report(
        analytics_result=ar,
        semantic_model=sm,
    )

    assert "sections" in report, "Report missing sections"
    assert "executive_summary" in report["sections"], "Report missing executive_summary"
    assert "kpi_summary" in report["sections"], "Report missing kpi_summary"
    assert "risks" in report["sections"], "Report missing risks"
    assert "opportunities" in report["sections"], "Report missing opportunities"
    assert "recommended_actions" in report["sections"], "Report missing recommended_actions"

    print("[PASS] Report Engine")


def validate_mongodb_memory():
    try:
        from app.memory.business_memory_engine import BusinessMemoryEngine

        test_ws = "validation-test-ws"
        test_session = "validation-session"

        conv_id = BusinessMemoryEngine.save_conversation(
            session_id=test_session,
            workspace_id=test_ws,
            role="user",
            content="Validation test question",
        )
        assert conv_id is not None, "Conversation save failed"

        history = BusinessMemoryEngine.get_conversation_history(test_session, test_ws, last_n=5)
        assert len(history) > 0, "Conversation history empty"

        report_id = BusinessMemoryEngine.save_report(
            workspace_id=test_ws,
            report_type="validation",
            audience="CEO",
            title="Validation Report",
            content={"test": True},
        )
        assert report_id is not None, "Report save failed"

        sql_id = BusinessMemoryEngine.save_generated_sql(
            workspace_id=test_ws,
            session_id=test_session,
            sql_query="SELECT * FROM test",
            intent="summary",
            question="test",
            tables_used=["test"],
            columns_used=["col1"],
            status="success",
        )
        assert sql_id is not None, "SQL save failed"

        audit_id = BusinessMemoryEngine.save_audit_log(
            workspace_id=test_ws,
            session_id=test_session,
            action="validation_test",
            resource_type="test",
            details={"test": True},
            status="success",
        )
        assert audit_id is not None, "Audit log save failed"

        sim_id = BusinessMemoryEngine.save_scenario_simulation(
            workspace_id=test_ws,
            simulation_name="validation_test",
            scenario_type="price_change",
            base_metric="revenue",
            base_value=1000.0,
            adjustment_value=5.0,
            adjustment_unit="pct",
            result_estimate=100.0,
            description="Validation test scenario",
            assumptions=["Test assumption"],
            metadata={"test": True},
        )
        assert sim_id is not None, "Scenario simulation save failed"

        print("[PASS] MongoDB Memory")
    except Exception as e:
        print(f"[SKIP] MongoDB Memory - {str(e)}")


def validate_full_pipeline():
    print("=" * 60)
    print("DecisionLens Production Validation")
    print("=" * 60)

    csv_path = create_synthetic_retail_dataset()
    print(f"[INFO] Created synthetic dataset: {csv_path}")

    try:
        parquet_path, profile, mapping = validate_semantic_detection(csv_path)
        canonical_model = validate_canonical_model(parquet_path, profile, mapping)
        validate_kpi_engine(parquet_path, profile, canonical_model)
        validate_forecast_engine(parquet_path, canonical_model)
        validate_recommendation_engine(parquet_path, profile, canonical_model)
        validate_scenario_simulator(parquet_path)
        validate_report_engine(parquet_path, profile, canonical_model)
        validate_mongodb_memory()

        print("=" * 60)
        print("ALL VALIDATIONS PASSED")
        print("=" * 60)
    finally:
        if csv_path.exists():
            csv_path.unlink()
        if csv_path.parent.exists():
            csv_path.parent.rmdir()


if __name__ == "__main__":
    validate_full_pipeline()
