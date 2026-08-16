from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ColumnIntelligence:
    name: str
    data_type: str
    semantic_type: str
    business_role: str
    unit: str = ""
    is_measure: bool = False
    is_dimension: bool = False
    is_temporal: bool = False
    is_identifier: bool = False
    confidence: float = 0.0
    null_percentage: float = 0.0
    distinct_count: int = 0


@dataclass
class DataQualityIntelligence:
    overall_score: float = 100.0
    completeness: float = 100.0
    uniqueness: float = 100.0
    consistency: float = 100.0
    validity: float = 100.0
    accuracy: float = 100.0
    null_percentage: float = 0.0
    duplicate_percentage: float = 0.0
    outlier_percentage: float = 0.0
    issues: List[str] = field(default_factory=list)


@dataclass
class CapabilityMatrix:
    capability: str
    available: bool
    confidence: str
    reason: str


@dataclass
class MLRecommendation:
    model: str
    algorithm: str
    status: str
    reason: str


@dataclass
class DatasetIntelligenceProfile:
    detected_domain: str
    confidence_pct: float
    reasoning: str
    matched_columns: List[str]
    detected_entities: List[str]
    detected_measures: List[str]
    detected_dimensions: List[str]
    detected_temporal: List[str]
    total_records: int
    total_columns: int
    capability_matrix: List[CapabilityMatrix] = field(default_factory=list)
    business_questions: List[str] = field(default_factory=list)
    ml_recommendations: List[MLRecommendation] = field(default_factory=list)


@dataclass
class DatasetIntelligenceResult:
    workspace_id: str
    status: str = "READY"
    domain: str = "Generic Business"
    domain_confidence: float = 50.0
    domain_reason: str = ""
    dataset_type: str = "Unknown"
    generated_at: str = ""
    columns: List[ColumnIntelligence] = field(default_factory=list)
    data_quality: DataQualityIntelligence = field(default_factory=DataQualityIntelligence)
    profile: DatasetIntelligenceProfile = field(default_factory=lambda: DatasetIntelligenceProfile(
        detected_domain="Generic Business",
        confidence_pct=0.0,
        reasoning="",
        matched_columns=[],
        detected_entities=[],
        detected_measures=[],
        detected_dimensions=[],
        detected_temporal=[],
        total_records=0,
        total_columns=0,
    ))
    semantic_model: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "status": self.status,
            "domain": self.domain,
            "domain_confidence": self.domain_confidence,
            "domain_reason": self.domain_reason,
            "dataset_type": self.dataset_type,
            "generated_at": self.generated_at,
            "columns": [c.__dict__ for c in self.columns],
            "data_quality": self.data_quality.__dict__,
            "profile": {
                "detected_domain": self.profile.detected_domain,
                "confidence_pct": self.profile.confidence_pct,
                "reasoning": self.profile.reasoning,
                "matched_columns": self.profile.matched_columns,
                "detected_entities": self.profile.detected_entities,
                "detected_measures": self.profile.detected_measures,
                "detected_dimensions": self.profile.detected_dimensions,
                "detected_temporal": self.profile.detected_temporal,
                "total_records": self.profile.total_records,
                "total_columns": self.profile.total_columns,
                "capability_matrix": [c.__dict__ for c in self.profile.capability_matrix],
                "business_questions": self.profile.business_questions,
                "ml_recommendations": [m.__dict__ for m in self.profile.ml_recommendations],
            },
            "semantic_model": self.semantic_model,
            "error": self.error,
        }
