"""Quick verification that the grounded copilot works with an uploaded dataset."""
from app.ai.universal_copilot_brain import UniversalAIBrain
from app.services.workspace_service import EnterpriseWorkspaceManager


def main():
    ws_id = EnterpriseWorkspaceManager.get_active_workspace_id()

    cases = [
        ("Which product category generated the highest revenue?", "top_n"),
        ("Who are the best customers by payment value?", "top_n"),
        ("What is the monthly sales trend?", "trend"),
    ]

    for question, expected_intent in cases:
        print("=" * 70)
        print(f"Q: {question}")
        res = UniversalAIBrain.query(
            question=question,
            workspace_id=ws_id,
        )
        ans = res.get("answer", "")
        support = res.get("support", {})
        print(f"Intent: {support.get('intent')}")
        print(f"Answer: {ans[:200]}...")
        print(f"Dataset: {res.get('dataset')}")
        print(f"Columns: {res.get('columns')}")
        print(f"Calculation: {res.get('calculation')}")
        print(f"Confidence: {res.get('confidence')}")
        print(f"Tables: {support.get('tables_used')}")
        print(f"SQL: {support.get('sql_used')}")
        assert ans, "answer must be non-empty"
        assert res.get("dataset"), "dataset must be non-empty"
        assert res.get("columns"), "columns must be non-empty"
        assert res.get("calculation"), "calculation must be non-empty"
        assert support.get("tables_used"), "tables_used must be non-empty"
        assert support.get("sql_used"), "sql_used must be non-empty"
        assert res.get("confidence", 0) > 0, "confidence must be > 0"
        print("OK\n")


if __name__ == "__main__":
    main()
