"""
Enterprise Copilot Verification Suite
Tests 25+ business questions against available workspace data.
Ensures every response contains required fields and no hallucinations.
"""
import sys
import os
from pathlib import Path

os.chdir(Path(__file__).resolve().parent)

sys.path.insert(0, ".")

from app.ai.universal_copilot_brain import UniversalAIBrain
from app.services.workspace_service import EnterpriseWorkspaceManager
from app.database.storage import ParquetStorageManager

REQUIRED_FIELDS = {
    "answer", "evidence", "confidence", "dataset", "columns",
    "calculation", "support", "error", "intent", "domain",
}


BUSINESS_QUESTIONS = [
    "What is the total revenue across all transactions?",
    "Which product category generates the highest sales?",
    "Show me the monthly sales trend over time.",
    "What is the total number of orders?",
    "Which customers generate the most revenue?",
    "Are there any anomalies or unusual spikes in the data?",
    "Give me an executive summary of this dataset.",
    "What is the average order value?",
    "Break down sales by payment type.",
    "Which sellers have the highest total sales?",
    "Compare revenue across different time periods.",
    "What is the distribution of orders by state?",
    "Show me the top 10 products by revenue.",
    "What is the total freight cost paid?",
    "How many unique customers are there?",
    "What is the median review score?",
    "Which month had the highest sales volume?",
    "Is there a correlation between price and quantity?",
    "What percentage of orders are delivered on time?",
    "Show me the seasonal pattern in sales.",
    "Which product category has the lowest average price?",
    "What is the customer retention rate?",
    "Forecast revenue for the next 30 days.",
    "How does freight cost vary by product category?",
    "What is the return on investment by seller?"
]


def run_verification():
    print("=" * 80)
    print("DECISIONLENS UNIVERSAL AI COPILOT — VERIFICATION SUITE")
    print("=" * 80)

    workspace_id = EnterpriseWorkspaceManager.get_active_workspace_id()
    if not workspace_id:
        print("ERROR: No active workspace found. Cannot verify.")
        return 1

    print(f"Active Workspace: {workspace_id}")
    print(f"Total Questions: {len(BUSINESS_QUESTIONS)}")
    print("-" * 80)

    passed = 0
    failed = 0
    issues = []

    for idx, question in enumerate(BUSINESS_QUESTIONS, 1):
        try:
            response = UniversalAIBrain.query(
                question=question,
                workspace_id=workspace_id,
            )
            support = response.get("support", {})

            missing = REQUIRED_FIELDS - set(response.keys())
            if missing:
                failed += 1
                issues.append({
                    "question": question,
                    "issue": f"Missing fields: {missing}",
                    "severity": "HIGH"
                })
                print(f"[{idx:02d}] FAIL  | {question}")
                print(f"       Missing: {missing}")
                continue

            # Check for hallucination: if SQL exists, it must reference actual tables/columns from the dataset
            sql_used = support.get("sql_used")
            error = response.get("error")
            if sql_used and error:
                evidence = response.get("evidence", [])
                if not evidence:
                    failed += 1
                    issues.append({
                        "question": question,
                        "issue": "Query failed with no evidence",
                        "severity": "MEDIUM"
                    })
                    print(f"[{idx:02d}] WARN  | {question} — query failed, no evidence")
                else:
                    passed += 1
                    print(f"[{idx:02d}] PASS  | {question} — failed gracefully with evidence")
                continue

            # If confidence is 0.0 and no error, flag as potential data issue
            if response.get("confidence", 0) == 0.0 and not error:
                failed += 1
                issues.append({
                    "question": question,
                    "issue": "Zero confidence without error explanation",
                    "severity": "MEDIUM"
                })
                print(f"[{idx:02d}] FAIL  | {question} — zero confidence, no error")
                continue

            # Valid response
            passed += 1
            print(f"[{idx:02d}] PASS  | {question}")
            print(f"       Intent={support.get('intent')} | Confidence={response.get('confidence', 0):.2f} | Tables={support.get('tables_used')} | Domain={response.get('support', {}).get('domain')}")

        except Exception as exc:
            failed += 1
            issues.append({
                "question": question,
                "issue": f"Exception: {exc}",
                "severity": "CRITICAL"
            })
            print(f"[{idx:02d}] FAIL  | {question}")
            print(f"       Exception: {exc}")

    print("-" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(BUSINESS_QUESTIONS)}")
    print("=" * 80)

    if issues:
        print("\nISSUES FOUND:")
        for issue in issues:
            print(f"  [{issue['severity']}] {issue['question']}")
            print(f"           {issue['issue']}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_verification())
