"""Regression tests for DecisionLens Copilot multi-turn conversation behavior.

Ensures:
- Different analytical questions return different grounded answers
- Follow-up questions are resolved using conversation context
- Conversation history is properly maintained
- No cached duplicate answers for different questions
"""
from __future__ import annotations

import uuid
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from app.ai.decision_mode_router import DecisionModeRouter
from app.ai.universal_copilot_brain import UniversalAIBrain
from app.services.workspace_service import EnterpriseWorkspaceManager
from app.ingestion.generic_loader import GenericDataLoader
from app.ingestion.semantic_profiler import SemanticDataProfiler


UPLOAD_RAW_DIR = Path("backend/storage/raw")
PARQUET_DIR = Path("backend/storage/parquet")


def _get_retail_dataset() -> Path | None:
    candidates = list(UPLOAD_RAW_DIR.glob("*retail*")) + list(UPLOAD_RAW_DIR.glob("*sales*"))
    return candidates[0] if candidates else None


def _setup_workspace(dataset_name: str = "test-copilot-conversation") -> tuple[str, Path]:
    ws_id = f"ws-copilot-{uuid.uuid4().hex[:8]}"
    dataset_path = _get_retail_dataset()
    if dataset_path is None:
        pytest.skip("No retail dataset found in backend/storage/raw")

    upload_path = UPLOAD_RAW_DIR / f"{dataset_name}.csv"
    shutil.copy2(dataset_path, upload_path)
    dataset_id = f"{ws_id}__{dataset_name}"
    parquet_path = GenericDataLoader.convert_to_parquet(upload_path, dataset_id)
    EnterpriseWorkspaceManager.create_or_get_workspace(ws_id, "Copilot Test Workspace")
    profile = SemanticDataProfiler.profile(parquet_path)
    EnterpriseWorkspaceManager.register_table(
        ws_id,
        dataset_name,
        [{"name": c, "type": profile["columns"][c].get("inferred_type", "VARCHAR")} for c in profile["columns"]],
        profile.get("total_rows", 0),
        str(parquet_path),
    )
    return ws_id, parquet_path


class TestDecisionModeRouterFollowUp:
    """Test that follow-up questions are properly classified using history."""

    def test_why_follow_up_after_summary(self):
        history = [
            {"role": "user", "content": "What is the overall health of this business?"},
            {"role": "assistant", "content": "The business health score is 72/100."},
        ]
        result = DecisionModeRouter.route("Why?", history=history)
        assert result["mode"] in ("root_cause_analysis", "diagnose")
        assert result.get("is_follow_up") is True

    def test_what_should_i_do_follow_up(self):
        history = [
            {"role": "user", "content": "Which category performs best?"},
            {"role": "assistant", "content": "Electronics is the top performer."},
        ]
        result = DecisionModeRouter.route("What should I do?", history=history)
        assert result["mode"] == "recommend"
        assert result.get("is_follow_up") is True

    def test_what_if_follow_up(self):
        history = [
            {"role": "user", "content": "What is the forecast for next quarter?"},
            {"role": "assistant", "content": "Revenue is projected to grow 5%."},
        ]
        result = DecisionModeRouter.route("What happens if I increase price by 10%?", history=history)
        assert result["mode"] == "what_if_simulation"
        assert result.get("is_follow_up") is True

    def test_compare_follow_up(self):
        history = [
            {"role": "user", "content": "Show me sales by region"},
            {"role": "assistant", "content": "North: $100k, South: $80k, East: $90k, West: $70k"},
        ]
        result = DecisionModeRouter.route("Compare them", history=history)
        assert result["mode"] == "compare"
        assert result.get("is_follow_up") is True

    def test_risk_follow_up(self):
        history = [
            {"role": "user", "content": "What is declining?"},
            {"role": "assistant", "content": "Customer retention has declined 15%."},
        ]
        result = DecisionModeRouter.route("Is that risky?", history=history)
        assert result["mode"] == "risk_assessment"
        assert result.get("is_follow_up") is True

    def test_summarize_everything_follow_up(self):
        history = [
            {"role": "user", "content": "What are the key trends?"},
            {"role": "assistant", "content": "Revenue is trending upward."},
        ]
        result = DecisionModeRouter.route("Summarize everything for a CEO", history=history)
        assert result["mode"] == "summarize"
        assert result.get("is_follow_up") is True

    def test_no_history_returns_normal_intent(self):
        result = DecisionModeRouter.route("What is the forecast?", history=None)
        assert result["mode"] == "predict"
        assert result.get("is_follow_up") is None


class TestIntentDetectionFollowUp:
    """Test UniversalAIBrain._detect_intent with conversation history."""

    def test_follow_up_why_gets_root_cause(self):
        history = [
            {"role": "user", "content": "What is the overall health of this business?"},
            {"role": "assistant", "content": "Health score: 72/100."},
        ]
        result = UniversalAIBrain._detect_intent("Why?", history=history)
        assert result["intent"] in ("root_cause_analysis", "correlation", "diagnose")
        assert result.get("is_follow_up") is True

    def test_follow_up_what_should_gets_recommendation(self):
        history = [
            {"role": "user", "content": "Which category performs best?"},
            {"role": "assistant", "content": "Electronics leads."},
        ]
        result = UniversalAIBrain._detect_intent("What should I do?", history=history)
        assert result["intent"] == "recommendation"
        assert result.get("is_follow_up") is True

    def test_follow_up_what_if_gets_scenario(self):
        history = [
            {"role": "user", "content": "What is the forecast?"},
            {"role": "assistant", "content": "Growth projected at 5%."},
        ]
        result = UniversalAIBrain._detect_intent("What if I increase price by 10%?", history=history)
        assert result["intent"] == "scenario"
        assert result.get("is_follow_up") is True


class TestCopilotConversationContext:
    """Test that different questions produce different answers from the copilot."""

    def test_different_questions_return_different_answers(self):
        ws_id, parquet_path = _setup_workspace("test-diff-answers")
        try:
            q1 = "What is the overall health of this business?"
            r1 = UniversalAIBrain.query(question=q1, workspace_id=ws_id, dataset_id=ws_id)
            assert "answer" in r1
            a1 = r1["answer"]

            q2 = "Which category performs best?"
            r2 = UniversalAIBrain.query(question=q2, workspace_id=ws_id, dataset_id=ws_id)
            assert "answer" in r2
            a2 = r2["answer"]

            assert a1 != a2, "Different questions must produce different answers"

            q3 = "What is the overall health of this business?"
            r3 = UniversalAIBrain.query(question=q3, workspace_id=ws_id, dataset_id=ws_id)
            assert "answer" in r3
            a3 = r3["answer"]

            assert a1 == a3, "Identical questions should produce the same answer"
        finally:
            EnterpriseWorkspaceManager.delete_workspace(ws_id)

    def test_follow_up_question_uses_context(self):
        ws_id, parquet_path = _setup_workspace("test-followup-context")
        try:
            q1 = "What is the overall health of this business?"
            r1 = UniversalAIBrain.query(question=q1, workspace_id=ws_id, dataset_id=ws_id)
            assert "answer" in r1

            history = [
                {"role": "user", "content": q1},
                {"role": "assistant", "content": r1["answer"], "metadata": {"intent": "summary"}},
            ]

            q2 = "Why?"
            r2 = UniversalAIBrain.query(question=q2, workspace_id=ws_id, dataset_id=ws_id, conversation_history=history)
            assert "answer" in r2
            a2 = r2["answer"]

            q3 = "What should I do?"
            r3 = UniversalAIBrain.query(question=q3, workspace_id=ws_id, dataset_id=ws_id, conversation_history=history + [
                {"role": "user", "content": q2},
                {"role": "assistant", "content": a2, "metadata": {"intent": r2.get("intent", "diagnose")}},
            ])
            assert "answer" in r3
            a3 = r3["answer"]

            assert a2 != a3, "Follow-up questions should produce different answers"
            assert r2.get("intent") in ("root_cause_analysis", "diagnose", "correlation")
            assert r3.get("intent") == "recommendation"
        finally:
            EnterpriseWorkspaceManager.delete_workspace(ws_id)

    def test_no_fabricated_metrics(self):
        ws_id, parquet_path = _setup_workspace("test-no-fabrication")
        try:
            r = UniversalAIBrain.query(question="What is the total revenue?", workspace_id=ws_id, dataset_id=ws_id)
            answer = r.get("answer", "")
            assert "no data" not in answer.lower() or "unavailable" not in answer.lower()
            evidence = r.get("evidence", {})
            rows = evidence.get("rows", []) if isinstance(evidence, dict) else []
            if rows:
                assert any(isinstance(row, dict) and any(isinstance(v, (int, float)) for v in row.values()) for row in rows), (
                    "Evidence rows must contain numeric values"
                )
        finally:
            EnterpriseWorkspaceManager.delete_workspace(ws_id)

    def test_sequence_of_questions_all_return_valid_answers(self):
        ws_id, parquet_path = _setup_workspace("test-sequence")
        try:
            questions = [
                "What is the overall health of this business?",
                "Which category performs best?",
                "Why?",
                "What is declining?",
                "What should I do?",
                "What happens if I increase the main driver by 10%?",
                "Is that risky?",
                "Compare the best and worst segments.",
                "Give me a forecast.",
                "Summarize everything for a CEO.",
            ]
            history = []
            answers = []
            for q in questions:
                r = UniversalAIBrain.query(question=q, workspace_id=ws_id, dataset_id=ws_id, conversation_history=history if history else None)
                answer = r.get("answer", "")
                assert answer, f"Empty answer for: {q}"
                assert "unexpected error" not in answer.lower(), f"Error in answer for: {q}"
                answers.append(answer)
                history.append({"role": "user", "content": q})
                history.append({"role": "assistant", "content": answer, "metadata": {"intent": r.get("intent", "")}})

            unique_answers = set(answers)
            assert len(unique_answers) >= 5, f"Expected at least 5 unique answers, got {len(unique_answers)}"
        finally:
            EnterpriseWorkspaceManager.delete_workspace(ws_id)
