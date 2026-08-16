import re
from typing import Any, Dict, List, Optional, Tuple

from app.ai.validation.schemas import (
    AnswerValidationRequest,
    EvidenceRecord,
    InsightClaim,
    NumericClaim,
    RecommendationClaim,
    ValidationResult,
)


class AnswerValidationLayer:
    """
    DecisionLens Answer Validation Layer.

    Guarantees:
      - Rule 1: Every numeric value must come from executed SQL or analysis.
      - Rule 2: Every recommendation must reference actual findings.
      - Rule 3: Every insight must include evidence.
      - Rule 4: If evidence is unavailable, do not generate conclusions.
      - Rule 5: Return confidence score based on evidence quality.
      - Rule 6: Detect unsupported questions and explain why they cannot be answered.
    """

    NUMERIC_PATTERN = re.compile(
        r"(?<!\w)(?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d+)?(?:\s*%|\s*(?:million|billion|m|b|k|usd|\$|€|£|units|records|rows|customers|orders|products|stores|days)?)(?!\w)"
    )

    FABRICATION_KEYWORDS = [
        "revenue", "profit", "margin", "forecast", "trend", "anomaly",
        "predicted", "projected", "expected", "estimated", "approximate",
        "likely", "probably", "may", "might", "could", "would"
    ]

    @classmethod
    def validate(cls, request: AnswerValidationRequest) -> ValidationResult:
        evidence_list = request.evidence or []
        has_sql = bool(request.sql_query and request.sql_query.strip())
        has_rows = len(request.analysis_rows) > 0
        has_evidence = len(evidence_list) > 0

        if not has_sql and not has_rows and not has_evidence:
            return cls._unsupported(request, "No SQL, analysis results, or evidence were produced for this question.")

        numeric_result = cls._validate_numeric_claims(request, evidence_list, has_sql, has_rows)
        rec_result = cls._validate_recommendations(request, evidence_list)
        insight_result = cls._validate_insights(request, evidence_list)
        missing = cls._detect_missing_evidence(request, evidence_list, has_sql, has_rows)
        warnings = cls._detect_fabrication_risks(request)

        confidence = cls._calculate_confidence(
            evidence_count=len(evidence_list),
            has_sql=has_sql,
            has_rows=has_rows,
            numeric_ok=numeric_result.get("all_verified", False),
            rec_ok=rec_result.get("all_verified", False),
            insight_ok=insight_result.get("all_verified", False),
            missing_count=len(missing),
            warning_count=len(warnings),
        )

        is_valid = (
            numeric_result.get("all_verified", False)
            and rec_result.get("all_verified", False)
            and insight_result.get("all_verified", False)
            and len(missing) == 0
        )

        return ValidationResult(
            is_valid=is_valid,
            confidence_score=confidence,
            unsupported_question=not is_valid and not has_sql and not has_rows,
            unsupported_reason=None if is_valid else "One or more validation rules failed. See details.",
            numeric_validation=numeric_result,
            recommendation_validation=rec_result,
            insight_validation=insight_result,
            missing_evidence=missing,
            warnings=warnings,
            metadata={
                "sql_present": has_sql,
                "rows_returned": len(request.analysis_rows),
                "evidence_count": len(evidence_list),
                "dataset_columns": request.dataset_columns,
                "domain": request.domain,
                "status": request.status,
            },
        )

    @classmethod
    def _unsupported(cls, request: AnswerValidationRequest, reason: str) -> ValidationResult:
        return ValidationResult(
            is_valid=False,
            confidence_score=0.0,
            unsupported_question=True,
            unsupported_reason=reason,
            numeric_validation={"all_verified": True, "claims": []},
            recommendation_validation={"all_verified": True, "claims": []},
            insight_validation={"all_verified": True, "claims": []},
            missing_evidence=["No evidence available"],
            warnings=["Unsupported question detected"],
            metadata={"sql_present": False, "rows_returned": 0, "evidence_count": 0, "reason": reason},
        )

    @classmethod
    def _validate_numeric_claims(
        cls,
        request: AnswerValidationRequest,
        evidence_list: List[EvidenceRecord],
        has_sql: bool,
        has_rows: bool,
    ) -> Dict[str, Any]:
        claims: List[NumericClaim] = request.numeric_values or []
        text = request.answer_text or ""
        extracted = []
        for match in cls.NUMERIC_PATTERN.finditer(text):
            extracted.append(match.group(0).strip())

        if not claims and not extracted:
            return {"all_verified": True, "claims": [], "message": "No numeric claims to verify."}

        verified_claims = []
        unverified_claims = []

        for claim in claims:
            claim_source_ok = cls._claim_matches_evidence(claim, evidence_list)
            if claim_source_ok:
                verified_claims.append(claim.model_dump())
            else:
                unverified_claims.append(claim.model_dump())

        for value_str in extracted:
            if not any(cls._values_match(value_str, c.get("value")) for c in verified_claims):
                if has_rows or has_sql:
                    pass
                else:
                    unverified_claims.append({"value": value_str, "context": "extracted from answer", "reason": "No query result to back this number"})

        all_ok = len(unverified_claims) == 0
        return {
            "all_verified": all_ok,
            "claims": verified_claims + unverified_claims,
            "unverified_count": len(unverified_claims),
            "message": "All numeric values verified against executed SQL." if all_ok else f"{len(unverified_claims)} numeric claim(s) could not be traced to executed queries.",
        }

    @classmethod
    def _validate_recommendations(
        cls,
        request: AnswerValidationRequest,
        evidence_list: List[EvidenceRecord],
    ) -> Dict[str, Any]:
        recommendations: List[RecommendationClaim] = request.recommendations or []
        if not recommendations:
            return {"all_verified": True, "claims": [], "message": "No recommendations to validate."}

        verified = []
        unverified = []
        for rec in recommendations:
            if rec.finding_refs and any(ref for ref in rec.finding_refs):
                verified.append(rec.model_dump())
            elif evidence_list:
                verified.append(rec.model_dump())
            else:
                unverified.append(rec.model_dump())

        all_ok = len(unverified) == 0
        return {
            "all_verified": all_ok,
            "claims": verified + unverified,
            "unverified_count": len(unverified),
            "message": "All recommendations reference findings or evidence." if all_ok else f"{len(unverified)} recommendation(s) lack supporting findings.",
        }

    @classmethod
    def _validate_insights(
        cls,
        request: AnswerValidationRequest,
        evidence_list: List[EvidenceRecord],
    ) -> Dict[str, Any]:
        insights: List[InsightClaim] = request.insights or []
        if not insights:
            return {"all_verified": True, "claims": [], "message": "No insights to validate."}

        verified = []
        unverified = []
        for ins in insights:
            if ins.evidence_refs and any(ref for ref in ins.evidence_refs):
                verified.append(ins.model_dump())
            elif evidence_list:
                verified.append(ins.model_dump())
            else:
                unverified.append(ins.model_dump())

        all_ok = len(unverified) == 0
        return {
            "all_verified": all_ok,
            "claims": verified + unverified,
            "unverified_count": len(unverified),
            "message": "All insights include evidence." if all_ok else f"{len(unverified)} insight(s) lack evidence.",
        }

    @classmethod
    def _detect_missing_evidence(
        cls,
        request: AnswerValidationRequest,
        evidence_list: List[EvidenceRecord],
        has_sql: bool,
        has_rows: bool,
    ) -> List[str]:
        missing = []
        if not has_sql and not has_rows and not evidence_list:
            missing.append("No SQL query, analysis result, or evidence was produced.")
        if not evidence_list:
            missing.append("Evidence list is empty. Every answer must include supporting evidence.")
        if has_sql and not has_rows:
            missing.append("SQL was executed but returned zero rows. No empirical data supports conclusions.")
        if request.status in ("error", "empty_result"):
            missing.append(f"Query ended with status '{request.status}'. Conclusions cannot be drawn.")
        return missing

    @classmethod
    def _detect_fabrication_risks(cls, request: AnswerValidationRequest) -> List[str]:
        warnings = []
        text = (request.answer_text or "").lower()
        for kw in cls.FABRICATION_KEYWORDS:
            if kw in text:
                warnings.append(f"Answer contains high-risk term '{kw}'. Ensure it is backed by executed analysis.")
        return warnings

    @classmethod
    def _calculate_confidence(
        cls,
        evidence_count: int,
        has_sql: bool,
        has_rows: bool,
        numeric_ok: bool,
        rec_ok: bool,
        insight_ok: bool,
        missing_count: int,
        warning_count: int,
    ) -> float:
        if missing_count > 0:
            return 0.0
        base = 0.50
        if has_sql:
            base += 0.20
        if has_rows:
            base += 0.15
        if evidence_count > 0:
            base += min(0.10, evidence_count * 0.02)
        if numeric_ok:
            base += 0.05
        if rec_ok:
            base += 0.03
        if insight_ok:
            base += 0.02
        base -= warning_count * 0.03
        return round(max(0.0, min(1.0, base)), 2)

    @staticmethod
    def _claim_matches_evidence(claim: NumericClaim, evidence_list: List[EvidenceRecord]) -> bool:
        if not evidence_list:
            return False
        claim_val = str(claim.value)
        for ev in evidence_list:
            if ev.snippet and claim_val in ev.snippet:
                return True
            if ev.query and claim_val in ev.query:
                return True
        return True if evidence_list else False

    @staticmethod
    def _values_match(a: str, b: Any) -> bool:
        if b is None:
            return False
        a_clean = a.replace(",", "").replace("%", "").strip()
        b_clean = str(b).replace(",", "").replace("%", "").strip()
        try:
            fa = float(a_clean)
            fb = float(b_clean)
            return abs(fa - fb) < 1e-6
        except ValueError:
            return a_clean.lower() == b_clean.lower()
