import os
import pytest
import pandas as pd
from pathlib import Path
from dataclasses import asdict

from app.analytics.universal_engine import UniversalAnalyticsEngine
from app.intelligence.schemas import (
    DatasetIntelligenceProfile,
    DatasetIntelligenceResult,
    CapabilityMatrix,
    MLRecommendation,
    ColumnIntelligence,
    DataQualityIntelligence,
)
from app.ml.prediction_engine import UniversalPredictionEngine
from app.semantic_model.core import SemanticModel


@pytest.fixture
def sample_csv_file(tmp_path) -> Path:
    df = pd.DataFrame({
        "student_id": [101, 102, 103, 104, 105],
        "student_name": ["Alice", "Bob", "Charlie", "David", "Eve"],
        "marks": [85.0, 92.5, 78.0, 65.0, 88.0],
        "attendance": [90.0, 95.0, 85.0, 70.0, 92.0],
        "semester": ["Fall 2025", "Fall 2025", "Fall 2025", "Fall 2025", "Fall 2025"],
    })
    filepath = tmp_path / "education_sample.csv"
    df.to_csv(filepath, index=False)
    return filepath


def test_universal_analytics_engine_no_logging_name_error(sample_csv_file):
    """
    Test 1: Verify UniversalAnalyticsEngine executes cleanly on a dataset
    without raising NameError: name 'logging' is not defined in retry or analytics stages.
    """
    sm = SemanticModel(workspace_id="ws-test-edu", domain="Education")
    result = UniversalAnalyticsEngine.analyze(semantic_model=sm, parquet_path=sample_csv_file)

    assert result is not None
    assert result.domain in ("Education", "Generic Business", "Retail")
    assert isinstance(result.kpis, list)
    assert hasattr(result, "to_dict")

    # Verify serialization to dict succeeds
    res_dict = result.to_dict()
    assert isinstance(res_dict, dict)
    assert "kpis" in res_dict
    assert "distributions" in res_dict


def test_dataset_intelligence_profile_to_dict_serialization():
    """
    Test 2: Verify DatasetIntelligenceProfile and all related dataclasses
    have a working to_dict() method and serialize to JSON-compatible dictionaries.
    """
    cap = CapabilityMatrix(
        capability="Time-Series Forecasting",
        available=True,
        confidence="95%",
        reason="Detected temporal columns",
    )
    ml_rec = MLRecommendation(
        model="Student Performance Classifier",
        algorithm="XGBoost Classifier",
        status="Applicable",
        reason="Predicts pass/fail",
    )
    profile = DatasetIntelligenceProfile(
        detected_domain="Education",
        confidence_pct=95.0,
        reasoning="Columns indicate education dataset",
        matched_columns=["student_id", "marks"],
        detected_entities=["Students", "Courses"],
        detected_measures=["marks", "attendance"],
        detected_dimensions=["student_id", "semester"],
        detected_temporal=[],
        total_records=5,
        total_columns=5,
        capability_matrix=[cap],
        business_questions=["Which students are at risk?"],
        ml_recommendations=[ml_rec],
    )

    # Test to_dict on profile
    assert hasattr(profile, "to_dict")
    profile_dict = profile.to_dict()
    assert isinstance(profile_dict, dict)
    assert profile_dict["detected_domain"] == "Education"
    assert profile_dict["confidence_pct"] == 95.0
    assert len(profile_dict["capability_matrix"]) == 1
    assert profile_dict["capability_matrix"][0]["capability"] == "Time-Series Forecasting"

    # Test to_dict on result containing profile
    res = DatasetIntelligenceResult(
        workspace_id="ws-test-123",
        status="READY",
        domain="Education",
        profile=profile,
    )
    assert hasattr(res, "to_dict")
    res_dict = res.to_dict()
    assert isinstance(res_dict, dict)
    assert res_dict["workspace_id"] == "ws-test-123"
    assert res_dict["profile"]["detected_domain"] == "Education"


def test_mongodb_persistence_serialization_compatibility():
    """
    Test 3: Verify MongoDB document conversion helper succeeds for DatasetIntelligenceResult
    and DatasetIntelligenceProfile objects without raising AttributeError.
    """
    profile = DatasetIntelligenceProfile(
        detected_domain="Retail",
        confidence_pct=90.0,
        reasoning="Retail dataset",
        matched_columns=["sales", "category"],
        detected_entities=["Products"],
        detected_measures=["sales"],
        detected_dimensions=["category"],
        detected_temporal=["date"],
        total_records=100,
        total_columns=4,
    )
    result = DatasetIntelligenceResult(
        workspace_id="ws-retail-999",
        status="READY",
        domain="Retail",
        profile=profile,
    )

    # Simulate MongoDB persistence document dictionary generation
    doc = {
        "workspace_id": result.workspace_id,
        "intelligence": result.to_dict(),
        "profile": profile.to_dict(),
    }
    assert isinstance(doc, dict)
    assert doc["intelligence"]["domain"] == "Retail"
    assert doc["profile"]["detected_domain"] == "Retail"


def test_forecast_engine_gracefully_skips_unsuitable_datasets(sample_csv_file):
    """
    Test 4: Verify prediction engine gracefully skips datasets lacking
    sufficient time-series trend observations without raising an exception.
    """
    sm = SemanticModel(workspace_id="ws-test-edu", domain="Education")
    analytics_res = UniversalAnalyticsEngine.analyze(semantic_model=sm, parquet_path=sample_csv_file)
    predictions = UniversalPredictionEngine.generate(
        analytics_result=analytics_res,
        semantic_model=sm,
    )
    assert isinstance(predictions, list)
    # Should fall back or return empty list cleanly
