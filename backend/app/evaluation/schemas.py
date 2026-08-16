from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class DatasetProfile(BaseModel):
    name: str
    path: str
    domain: str
    description: str


class ScoreBreakdown(BaseModel):
    dimension: str
    score: float
    max_score: float = 1.0
    weight: float = 1.0
    details: Dict[str, Any] = Field(default_factory=dict)


class EvaluationResult(BaseModel):
    dataset_name: str
    domain: str
    dimension_scores: List[ScoreBreakdown] = Field(default_factory=list)
    overall_accuracy: float = 0.0
    business_understanding: float = 0.0
    recommendation_quality: float = 0.0
    sql_accuracy: float = 0.0
    visualization_quality: float = 0.0
    hallucination_score: float = 0.0
    weaknesses: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvaluationReport(BaseModel):
    summary: Dict[str, Any]
    dataset_results: List[EvaluationResult]
    overall_scores: Dict[str, float]
    weaknesses: List[Dict[str, Any]]
    suggestions: List[str]
    generated_at: str = ""


class DimensionTest(BaseModel):
    name: str
    description: str
    test_fn: str
    weight: float = 1.0


class EvaluationConfig(BaseModel):
    datasets_dir: str = ""
    output_dir: str = "data/evaluation_results"
    domains: List[str] = Field(default_factory=list)
    dimensions: List[str] = Field(default_factory=lambda: [
        "dataset_understanding",
        "entity_detection",
        "metric_detection",
        "sql_generation",
        "recommendations",
        "hallucination_prevention",
    ])
    score_weights: Dict[str, float] = Field(default_factory=lambda: {
        "dataset_understanding": 1.0,
        "entity_detection": 1.0,
        "metric_detection": 1.0,
        "sql_generation": 1.5,
        "recommendations": 1.5,
        "hallucination_prevention": 2.0,
    })