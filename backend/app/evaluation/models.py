from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class EvaluationScore:
    dimension: str
    score: float
    max_score: float = 1.0
    weight: float = 1.0
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def weighted_score(self) -> float:
        return (self.score / self.max_score) * self.weight


@dataclass
class DatasetEvaluationResult:
    dataset_name: str
    domain: str
    scores: List[EvaluationScore] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    @property
    def overall_accuracy(self) -> float:
        if not self.scores:
            return 0.0
        total_weighted = sum(s.weighted_score for s in self.scores)
        total_max_weighted = sum(s.max_score * s.weight for s in self.scores)
        return round(total_weighted / total_max_weighted, 4) if total_max_weighted > 0 else 0.0

    @property
    def business_understanding(self) -> float:
        dims = ["dataset_understanding", "entity_detection", "metric_detection"]
        return self._aggregate(dims)

    @property
    def recommendation_quality(self) -> float:
        return self._aggregate(["recommendations"])

    @property
    def sql_accuracy(self) -> float:
        return self._aggregate(["sql_generation"])

    @property
    def visualization_quality(self) -> float:
        return self._aggregate(["visualization_quality"])

    def _aggregate(self, dimension_names: List[str]) -> float:
        matching = [s for s in self.scores if s.dimension in dimension_names]
        if not matching:
            return 0.0
        total_weighted = sum(s.weighted_score for s in matching)
        total_max_weighted = sum(s.max_score * s.weight for s in matching)
        return round(total_weighted / total_max_weighted, 4) if total_max_weighted > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataset_name": self.dataset_name,
            "domain": self.domain,
            "scores": [
                {
                    "dimension": s.dimension,
                    "score": s.score,
                    "max_score": s.max_score,
                    "weight": s.weight,
                    "details": s.details,
                }
                for s in self.scores
            ],
            "overall_accuracy": self.overall_accuracy,
            "business_understanding": self.business_understanding,
            "recommendation_quality": self.recommendation_quality,
            "sql_accuracy": self.sql_accuracy,
            "visualization_quality": self.visualization_quality,
            "weaknesses": self.weaknesses,
            "suggestions": self.suggestions,
        }


@dataclass
class EvaluationReport:
    dataset_results: List[DatasetEvaluationResult] = field(default_factory=list)
    overall_scores: Dict[str, float] = field(default_factory=dict)
    weaknesses: List[Dict[str, Any]] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    generated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataset_results": [r.to_dict() for r in self.dataset_results],
            "overall_scores": self.overall_scores,
            "weaknesses": self.weaknesses,
            "suggestions": self.suggestions,
        }