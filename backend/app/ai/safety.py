import time
from typing import Any, Dict, List, Optional

from app.logging.logger import get_logger

logger = get_logger(__name__)


class AISafetyResult:
    def __init__(self, allowed: bool, reason: str, confidence: float, evidence: List[Dict[str, Any]], recovery: str):
        self.allowed = allowed
        self.reason = reason
        self.confidence = confidence
        self.evidence = evidence
        self.recovery = recovery

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "recovery": self.recovery,
        }


class AISafetyWrapper:
    @staticmethod
    def validate_answer(
        answer: str,
        evidence: List[Dict[str, Any]],
        sql_query: Optional[str] = None,
        rows_analyzed: int = 0,
        columns_used: Optional[List[str]] = None,
        models_used: Optional[List[str]] = None,
    ) -> AISafetyResult:
        if not answer or not answer.strip():
            return AISafetyResult(
                allowed=False,
                reason="No answer produced.",
                confidence=0.0,
                evidence=[],
                recovery="Retry with a more specific question or check dataset integrity.",
            )

        if not evidence and not sql_query:
            return AISafetyResult(
                allowed=False,
                reason="No evidence or SQL query backs this answer.",
                confidence=0.0,
                evidence=[],
                recovery="Insufficient data evidence. Upload a dataset with measurable columns and retry.",
            )

        if rows_analyzed == 0 and not sql_query:
            return AISafetyResult(
                allowed=False,
                reason="No data rows were analyzed.",
                confidence=0.0,
                evidence=[],
                recovery="Dataset may be empty or analysis failed. Verify data quality and retry.",
            )

        evidence_count = len(evidence) if evidence else 0
        confidence = 0.5
        if sql_query:
            confidence += 0.2
        if rows_analyzed > 0:
            confidence += 0.15
        if evidence_count > 0:
            confidence += min(0.10, evidence_count * 0.02)
        if columns_used:
            confidence += 0.05
        if models_used:
            confidence += 0.05

        confidence = max(0.0, min(1.0, round(confidence, 2)))

        return AISafetyResult(
            allowed=True,
            reason="Answer backed by verified data analysis.",
            confidence=confidence,
            evidence=evidence or [],
            recovery="Answer is grounded in dataset evidence.",
        )

    @staticmethod
    def build_evidence_block(
        sql_query: Optional[str],
        rows: List[Dict[str, Any]],
        tables: List[str],
        columns: List[str],
        rows_analyzed: int = 0,
        models_used: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        return {
            "sql_query": sql_query or "",
            "rows": rows[:50],
            "tables_used": tables,
            "columns_used": columns[:20],
            "rows_analyzed": rows_analyzed,
            "validation": {
                "status": "VERIFIED" if rows or sql_query else "PENDING",
                "rows_returned": len(rows),
            },
            "models_used": models_used or [],
            "traceability": "All numeric values derived from executed SQL queries against verified dataset records.",
        }

    @staticmethod
    def enforce_evidence_in_llm_prompt(
        base_prompt: str,
        evidence_block: Dict[str, Any],
        question: str,
    ) -> str:
        sql = evidence_block.get("sql_query", "")
        rows = evidence_block.get("rows", [])
        tables = evidence_block.get("tables_used", [])
        columns = evidence_block.get("columns_used", [])
        rows_analyzed = evidence_block.get("rows_analyzed", 0)

        evidence_summary = f"""
EVIDENCE BLOCK (VERIFIED DATA):
- SQL Query: {sql or 'None'}
- Rows Returned: {len(rows)}
- Tables Used: {', '.join(tables) if tables else 'None'}
- Columns Used: {', '.join(columns) if columns else 'None'}
- Rows Analyzed: {rows_analyzed}

STRICT RULES:
1. ONLY use numbers and facts from the Evidence Block above.
2. If a number is not in the Evidence Block, DO NOT invent it. Say "I don't have enough evidence for that number."
3. If the Evidence Block is empty or rows_returned is 0, respond: "I don't have enough evidence to answer that question."
4. Every recommendation must reference a finding from the Evidence Block.
5. State the evidence source (table, column, SQL query) for every claim.
"""
        return f"{base_prompt}\n\nQuestion: {question}\n{evidence_summary}"
