"""
Strategy API & Enterprise Strategy Engine Tests

Validates that the strategy API endpoint works correctly and
that different datasets produce distinct, data-grounded strategies.
"""
import uuid
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from app.services.enterprise_strategy_engine import EnterpriseStrategyEngine
from app.schemas.strategy import StrategyReport, ExecutiveSummary, RiskItem, OpportunityItem, ExecutiveRecommendation


def _make_profile(df: pd.DataFrame) -> dict:
    """Build a minimal profile dict from a dataframe."""
    profile = {
        "total_rows": len(df),
        "columns": {},
        "column_categories": {
            "measures": [],
            "dimensions": [],
            "temporal": [],
            "identifiers": [],
        },
    }
    for col in df.columns:
        col_data = df[col]
        null_count = int(col_data.isna().sum())
        if pd.api.types.is_numeric_dtype(col_data):
            profile["column_categories"]["measures"].append(col)
        else:
            profile["column_categories"]["dimensions"].append(col)

        profile["columns"][col] = {
            "data_type": "DOUBLE" if pd.api.types.is_numeric_dtype(col_data) else "VARCHAR",
            "null_percentage": round(null_count / max(len(df), 1) * 100, 2),
            "non_null_count": len(df) - null_count,
            "distinct_count": int(col_data.nunique()),
        }
    return profile


def _write_csv_and_get_path(df: pd.DataFrame) -> tuple[Path, str]:
    """Write DataFrame to a temp CSV and return (csv_path, dataset_id)."""
    tmpdir = Path(tempfile.mkdtemp())
    csv_path = tmpdir / f"{uuid.uuid4().hex}.csv"
    df.to_csv(csv_path, index=False)
    dataset_id = csv_path.stem
    return csv_path, dataset_id


class TestStrategyReportSchema:
    """Test StrategyReport dataclass and serialization."""

    def test_strategy_report_defaults(self):
        report = StrategyReport(workspace_id="ws-001")
        assert report.workspace_id == "ws-001"
        assert report.domain == "Generic Business"
        assert report.dataset_type == "Unknown"
        assert report.confidence_score == 0.0
        assert isinstance(report.executive_summary, ExecutiveSummary)
        assert report.risks == []
        assert report.opportunities == []
        assert report.recommendations == []

    def test_strategy_report_to_dict(self):
        report = StrategyReport(
            workspace_id="ws-001",
            domain="Retail",
            dataset_type="Sales Transactions",
            confidence_score=0.85,
            executive_summary=ExecutiveSummary(
                headline="Retail Strategy Analysis",
                key_findings=["Revenue up 10%"],
                evidence=["Data shows growth"],
                business_impact="Positive",
                confidence=0.85,
            ),
            risks=[
                RiskItem(
                    id="RSK-001",
                    title="Test Risk",
                    category="Operational",
                    probability="MEDIUM",
                    severity="HIGH",
                    business_impact="Impact",
                    recommended_mitigation="Mitigate",
                    confidence=80.0,
                )
            ],
            opportunities=[
                OpportunityItem(
                    id="OPP-001",
                    title="Test Opportunity",
                    category="Growth",
                    priority="HIGH",
                    potential_value="$1M",
                    timeline="90 Days",
                    action="Expand",
                    confidence=85.0,
                )
            ],
            recommendations=[
                ExecutiveRecommendation(
                    id="REC-001",
                    title="Test Recommendation",
                    category="Strategy",
                    priority="HIGH",
                    reason="Data supports",
                    action="Execute",
                    confidence=90.0,
                    risk_level="LOW",
                )
            ],
        )
        data = report.to_dict()
        assert data["workspace_id"] == "ws-001"
        assert data["domain"] == "Retail"
        assert data["confidence_score"] == 0.85
        assert len(data["risks"]) == 1
        assert data["risks"][0]["title"] == "Test Risk"
        assert len(data["opportunities"]) == 1
        assert data["opportunities"][0]["title"] == "Test Opportunity"
        assert len(data["recommendations"]) == 1
        assert data["recommendations"][0]["title"] == "Test Recommendation"
        assert data["executive_summary"]["headline"] == "Retail Strategy Analysis"


class TestStrategyEngineDifferentiation:
    """Test that strategy engine produces different outputs for different datasets."""

    def test_retail_vs_finance_produces_different_domains(self):
        """Retail and finance datasets should produce different domain classifications."""
        retail_df = pd.DataFrame({
            "product": ["A", "B", "C", "D", "E"] * 20,
            "quantity": [1 + (i % 10) for i in range(100)],
            "unit_price": [10.0 + (i % 50) * 0.5 for i in range(100)],
            "customer_id": [f"CUST{i%20}" for i in range(100)],
            "region": ["North", "South", "East", "West"] * 25,
        })

        finance_df = pd.DataFrame({
            "account": [f"ACC{i%10}" for i in range(100)],
            "balance": [1000.0 + (i % 5000) for i in range(100)],
            "interest_rate": [2.0 + (i % 8) * 0.5 for i in range(100)],
            "transaction_date": pd.date_range("2024-01-01", periods=100, freq="D"),
            "transaction_type": ["credit", "debit"] * 50,
        })

        retail_profile = _make_profile(retail_df)
        finance_profile = _make_profile(finance_df)

        # Build mock analytics results that the strategy engine consumes
        retail_analytics = {
            "domain": "Retail",
            "dataset_type": "Sales Transactions",
            "confidence_score": 0.8,
            "kpis": [],
            "root_causes": [],
            "anomalies": [],
            "health_score": {"overall_score": 75},
            "drivers": [],
            "opportunities": [],
            "recommendations": [],
            "risks": [],
            "critical_findings": ["Retail dataset analyzed"],
            "positive_findings": ["Sales volume stable"],
            "negative_findings": [],
            "correlations": [],
        }

        finance_analytics = {
            "domain": "Finance",
            "dataset_type": "Banking Transactions",
            "confidence_score": 0.85,
            "kpis": [],
            "root_causes": [],
            "anomalies": [],
            "health_score": {"overall_score": 80},
            "drivers": [],
            "opportunities": [],
            "recommendations": [],
            "risks": [],
            "critical_findings": ["Finance dataset analyzed"],
            "positive_findings": ["Portfolio balanced"],
            "negative_findings": [],
            "correlations": [],
        }

        retail_report = EnterpriseStrategyEngine._build_strategy_report(
            workspace_id="ws-retail",
            analytics=retail_analytics,
            profile=retail_profile,
            con=None,
            table_name=None,
            generated_at="2024-01-01T00:00:00",
        )

        finance_report = EnterpriseStrategyEngine._build_strategy_report(
            workspace_id="ws-finance",
            analytics=finance_analytics,
            profile=finance_profile,
            con=None,
            table_name=None,
            generated_at="2024-01-01T00:00:00",
        )

        assert retail_report.domain == "Retail"
        assert finance_report.domain == "Finance"
        assert retail_report.dataset_type == "Sales Transactions"
        assert finance_report.dataset_type == "Banking Transactions"
        # Domain and dataset type must differ
        assert retail_report.domain != finance_report.domain

    def test_education_vs_healthcare_produces_different_domains(self):
        education_df = pd.DataFrame({
            "student_id": [f"STU{i%50}" for i in range(100)],
            "course": [f"Course{i%10}" for i in range(100)],
            "grade": [50 + (i % 50) for i in range(100)],
            "attendance": [60 + (i % 40) for i in range(100)],
            "semester": ["Fall", "Spring"] * 50,
        })

        healthcare_df = pd.DataFrame({
            "patient_id": [f"PAT{i%30}" for i in range(100)],
            "diagnosis": ["Flu", "Diabetes", "Hypertension"] * 33 + ["Flu"],
            "age": [20 + (i % 70) for i in range(100)],
            "treatment_cost": [100.0 + (i % 2000) for i in range(100)],
            "admission_date": pd.date_range("2024-01-01", periods=100, freq="D"),
        })

        education_profile = _make_profile(education_df)
        healthcare_profile = _make_profile(healthcare_df)

        education_analytics = {
            "domain": "Education",
            "dataset_type": "Student Records",
            "confidence_score": 0.75,
            "kpis": [],
            "root_causes": [],
            "anomalies": [],
            "health_score": {"overall_score": 70},
            "drivers": [],
            "opportunities": [],
            "recommendations": [],
            "risks": [],
            "critical_findings": ["Education dataset analyzed"],
            "positive_findings": ["Attendance improving"],
            "negative_findings": [],
            "correlations": [],
        }

        healthcare_analytics = {
            "domain": "Healthcare",
            "dataset_type": "Patient Records",
            "confidence_score": 0.78,
            "kpis": [],
            "root_causes": [],
            "anomalies": [],
            "health_score": {"overall_score": 72},
            "drivers": [],
            "opportunities": [],
            "recommendations": [],
            "risks": [],
            "critical_findings": ["Healthcare dataset analyzed"],
            "positive_findings": ["Costs stable"],
            "negative_findings": [],
            "correlations": [],
        }

        education_report = EnterpriseStrategyEngine._build_strategy_report(
            workspace_id="ws-education",
            analytics=education_analytics,
            profile=education_profile,
            con=None,
            table_name=None,
            generated_at="2024-01-01T00:00:00",
        )

        healthcare_report = EnterpriseStrategyEngine._build_strategy_report(
            workspace_id="ws-healthcare",
            analytics=healthcare_analytics,
            profile=healthcare_profile,
            con=None,
            table_name=None,
            generated_at="2024-01-01T00:00:00",
        )

        assert education_report.domain == "Education"
        assert healthcare_report.domain == "Healthcare"
        assert education_report.domain != healthcare_report.domain

    def test_strategy_output_changes_with_data(self):
        """Same engine should produce different executive summaries for different data."""
        sales_df = pd.DataFrame({
            "product": ["A", "B", "C"] * 33,
            "revenue": [100.0 + i * 10 for i in range(99)],
            "units_sold": [1 + (i % 20) for i in range(99)],
        })

        hr_df = pd.DataFrame({
            "employee": [f"EMP{i%25}" for i in range(100)],
            "salary": [30000 + (i % 50000) for i in range(100)],
            "department": ["Eng", "Sales", "HR", "Marketing"] * 25,
            "years_experience": [1 + (i % 15) for i in range(100)],
        })

        sales_profile = _make_profile(sales_df)
        hr_profile = _make_profile(hr_df)

        sales_analytics = {
            "domain": "Retail",
            "dataset_type": "Sales",
            "confidence_score": 0.8,
            "kpis": [],
            "root_causes": [],
            "anomalies": [],
            "health_score": {"overall_score": 75},
            "drivers": [],
            "opportunities": [],
            "recommendations": [],
            "risks": [],
            "critical_findings": ["Sales growth detected"],
            "positive_findings": ["Revenue increasing"],
            "negative_findings": [],
            "correlations": [],
        }

        hr_analytics = {
            "domain": "HR",
            "dataset_type": "Employee Records",
            "confidence_score": 0.82,
            "kpis": [],
            "root_causes": [],
            "anomalies": [],
            "health_score": {"overall_score": 78},
            "drivers": [],
            "opportunities": [],
            "recommendations": [],
            "risks": [],
            "critical_findings": ["Turnover rate stable"],
            "positive_findings": ["Salary competitive"],
            "negative_findings": [],
            "correlations": [],
        }

        sales_report = EnterpriseStrategyEngine._build_strategy_report(
            workspace_id="ws-sales",
            analytics=sales_analytics,
            profile=sales_profile,
            con=None,
            table_name=None,
            generated_at="2024-01-01T00:00:00",
        )

        hr_report = EnterpriseStrategyEngine._build_strategy_report(
            workspace_id="ws-hr",
            analytics=hr_analytics,
            profile=hr_profile,
            con=None,
            table_name=None,
            generated_at="2024-01-01T00:00:00",
        )

        # Executive summaries must reflect the domain
        assert "Retail" in sales_report.executive_summary.headline
        assert "HR" in hr_report.executive_summary.headline
        assert sales_report.executive_summary.headline != hr_report.executive_summary.headline


class TestStrategyRanking:
    """Test recommendation ranking by priority."""

    def test_recommendations_ranked_by_priority(self):
        recs = [
            ExecutiveRecommendation(
                id="REC-003", title="Low Priority", category="Strategy",
                priority="LOW", reason="", action="", confidence=90.0, risk_level="LOW",
            ),
            ExecutiveRecommendation(
                id="REC-001", title="Critical Priority", category="Strategy",
                priority="CRITICAL", reason="", action="", confidence=80.0, risk_level="LOW",
            ),
            ExecutiveRecommendation(
                id="REC-002", title="High Priority", category="Strategy",
                priority="HIGH", reason="", action="", confidence=85.0, risk_level="MEDIUM",
            ),
        ]

        ranked = EnterpriseStrategyEngine._rank_recommendations(recs)
        assert ranked[0].priority == "CRITICAL"
        assert ranked[1].priority == "HIGH"
        assert ranked[2].priority == "LOW"
