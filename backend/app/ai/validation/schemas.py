from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EvidenceRecord(BaseModel):
    source: str = Field(..., description="Origin of the evidence, e.g. 'duckdb_sql', 'python_analysis', 'rag_document'")
    query: Optional[str] = Field(None, description="SQL or Python query used to obtain the evidence")
    rows_returned: int = Field(0, description="Number of rows returned by the query")
    columns_used: List[str] = Field(default_factory=list)
    tables_used: List[str] = Field(default_factory=list)
    snippet: Optional[str] = Field(None, description="Verbatim data snippet supporting the claim")
    confidence: float = Field(0.0, ge=0.0, le=1.0)


class NumericClaim(BaseModel):
    value: Any
    unit: Optional[str] = None
    context: str = Field(..., description="Sentence or phrase where the number appears")
    evidence_ref: Optional[str] = Field(None, description="Pointer to the evidence record that supports this number")


class RecommendationClaim(BaseModel):
    text: str
    finding_refs: List[str] = Field(default_factory=list, description="IDs or descriptions of findings this recommendation is based on")


class InsightClaim(BaseModel):
    text: str
    evidence_refs: List[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    is_valid: bool
    confidence_score: float = Field(0.0, ge=0.0, le=1.0)
    unsupported_question: bool = Field(False)
    unsupported_reason: Optional[str] = None
    numeric_validation: Dict[str, Any] = Field(default_factory=dict)
    recommendation_validation: Dict[str, Any] = Field(default_factory=dict)
    insight_validation: Dict[str, Any] = Field(default_factory=dict)
    missing_evidence: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AnswerValidationRequest(BaseModel):
    question: str
    answer_text: str
    evidence: List[EvidenceRecord] = Field(default_factory=list)
    numeric_values: List[NumericClaim] = Field(default_factory=list)
    recommendations: List[RecommendationClaim] = Field(default_factory=list)
    insights: List[InsightClaim] = Field(default_factory=list)
    sql_query: Optional[str] = None
    analysis_rows: List[Dict[str, Any]] = Field(default_factory=list)
    dataset_columns: List[str] = Field(default_factory=list)
    domain: str = "Generic Business"
    status: str = "ok"
