import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.evaluation.models import (
    EvaluationReport,
    DatasetEvaluationResult,
    EvaluationScore,
)
from app.evaluation.schemas import EvaluationConfig
from app.evaluation.evaluators import (
    evaluate_dataset_understanding,
    evaluate_entity_detection,
    evaluate_metric_detection,
    evaluate_sql_generation,
    evaluate_recommendations,
    evaluate_hallucination_prevention,
    evaluate_visualization_quality,
)


class EvaluationFramework:
    """
    EvaluationFramework orchestrates the full evaluation pipeline for DecisionLens AI quality.

    It:
    1. Evaluates configured datasets across 6 dimensions (requires real datasets)
    2. Runs each dataset through 6 evaluation dimensions
    3. Aggregates scores into 5 core metrics
    4. Identifies weaknesses and generates improvement suggestions
    5. Produces a comprehensive evaluation report
    """

    def __init__(self, config: Optional[EvaluationConfig] = None):
        self.config = config or EvaluationConfig()
        self.datasets_dir = Path(self.config.datasets_dir)
        self.output_dir = Path(self.config.output_dir)
        self.datasets_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> EvaluationReport:
        print("=" * 80)
        print("DECISIONLENS AI EVALUATION FRAMEWORK")
        print("=" * 80)

        report = self._build_empty_report()
        self._save_report(report)
        self._print_final_summary(report)
        return report

    def _build_empty_report(self) -> EvaluationReport:
        return EvaluationReport(
            dataset_results=[],
            overall_scores={
                "overall_accuracy": 0.0,
                "business_understanding": 0.0,
                "recommendation_quality": 0.0,
                "sql_accuracy": 0.0,
                "visualization_quality": 0.0,
            },
            weaknesses=[],
            suggestions=[],
            generated_at=datetime.now().isoformat(),
        )

    def _evaluate_dataset(self, dataset_info: Dict[str, Any]) -> DatasetEvaluationResult:
        domain = dataset_info.get("domain", "Unknown")
        dataset_name = dataset_info.get("name", "unknown")
        test_questions = dataset_info.get("test_questions", [])

        scores: List[EvaluationScore] = []
        weaknesses: List[str] = []
        suggestions: List[str] = []

        du_result = self._run_dataset_understanding(dataset_info)
        du_score, du_details = evaluate_dataset_understanding(dataset_info, du_result)
        scores.append(EvaluationScore("dataset_understanding", du_score, 1.0, 1.0, du_details))
        self._collect_weaknesses("dataset_understanding", du_score, du_details, weaknesses, suggestions)

        ed_result = self._run_entity_detection(dataset_info)
        ed_score, ed_details = evaluate_entity_detection(dataset_info, ed_result)
        scores.append(EvaluationScore("entity_detection", ed_score, 1.0, 1.0, ed_details))
        self._collect_weaknesses("entity_detection", ed_score, ed_details, weaknesses, suggestions)

        md_result = self._run_metric_detection(dataset_info)
        md_score, md_details = evaluate_metric_detection(dataset_info, md_result)
        scores.append(EvaluationScore("metric_detection", md_score, 1.0, 1.0, md_details))
        self._collect_weaknesses("metric_detection", md_score, md_details, weaknesses, suggestions)

        sql_scores_list, sql_details = self._run_sql_tests(dataset_info, test_questions)
        sql_score = sum(s[1] * s[2] for s in sql_scores_list) / max(sum(s[2] for s in sql_scores_list), 1) if sql_scores_list else 0.0
        sql_score = round(sql_score, 4)
        scores.append(EvaluationScore("sql_generation", sql_score, 1.0, 1.5, sql_details))
        self._collect_weaknesses("sql_generation", sql_score, sql_details, weaknesses, suggestions)

        rec_scores_list, rec_details = self._run_recommendation_tests(dataset_info, test_questions)
        rec_score = sum(s[1] * s[2] for s in rec_scores_list) / max(sum(s[2] for s in rec_scores_list), 1) if rec_scores_list else 0.0
        rec_score = round(rec_score, 4)
        scores.append(EvaluationScore("recommendations", rec_score, 1.0, 1.5, rec_details))
        self._collect_weaknesses("recommendations", rec_score, rec_details, weaknesses, suggestions)

        hp_result = self._run_hallucination_tests(dataset_info)
        hp_score, hp_details = evaluate_hallucination_prevention(
            hp_result.get("insight_result", {}),
            hp_result.get("data_rows", []),
            hp_result.get("validation_result", {}),
        )
        scores.append(EvaluationScore("hallucination_prevention", hp_score, 1.0, 2.0, hp_details))
        self._collect_weaknesses("hallucination_prevention", hp_score, hp_details, weaknesses, suggestions)

        viz_result = self._run_visualization_tests(dataset_info, test_questions)
        viz_score, viz_details = evaluate_visualization_quality(
            viz_result.get("analysis_result", {}),
            viz_result.get("question_understanding", {}),
            viz_result.get("charts_generated", []),
        )
        scores.append(EvaluationScore("visualization_quality", viz_score, 1.0, 1.0, viz_details))
        self._collect_weaknesses("visualization_quality", viz_score, viz_details, weaknesses, suggestions)

        return DatasetEvaluationResult(
            dataset_name=dataset_name,
            domain=domain,
            scores=scores,
            weaknesses=weaknesses,
            suggestions=suggestions,
        )

    def _run_dataset_understanding(self, dataset_info: Dict[str, Any]) -> Dict[str, Any]:
        from app.ingestion.semantic_profiler import SemanticDataProfiler
        from app.database.duckdb_engine import DuckDBEngine
        from pathlib import Path

        parquet_path = Path(dataset_info.get("path", ""))
        if not parquet_path.exists():
            csv_path = Path(dataset_info.get("path", "").replace(".csv", ".csv"))
            if csv_path.exists():
                parquet_path = csv_path

        if not parquet_path.exists():
            return {"domain_hints": {"primary_domain": "Unknown"}, "total_rows": 0, "entities": {}, "profile_summary": {"measures": [], "dimensions": []}}

        try:
            profile = SemanticDataProfiler.profile(parquet_path)
            schema = DuckDBEngine.get_schema(parquet_path)
            return {
                "total_rows": profile.get("total_rows", 0),
                "domain_hints": {"primary_domain": dataset_info.get("domain", "Unknown")},
                "entities": profile.get("entities", {}),
                "profile_summary": {
                    "measures": profile.get("column_categories", {}).get("measures", []),
                    "dimensions": profile.get("column_categories", {}).get("dimensions", []),
                },
            }
        except Exception:
            return {"domain_hints": {"primary_domain": dataset_info.get("domain", "Unknown")}, "total_rows": 0, "entities": {}, "profile_summary": {"measures": [], "dimensions": []}}

    def _run_entity_detection(self, dataset_info: Dict[str, Any]) -> Dict[str, Any]:
        from pathlib import Path

        parquet_path = Path(dataset_info.get("path", ""))
        if not parquet_path.exists():
            return {"entities": {}, "metrics": [], "identified_metrics": []}

        try:
            from app.semantic_model.entity_detector import detect_business_entities
            from app.database.duckdb_engine import DuckDBEngine

            schema = DuckDBEngine.get_schema(parquet_path)
            entities = detect_business_entities(schema)
            return {"entities": entities, "metrics": [], "identified_metrics": []}
        except Exception:
            return {"entities": {}, "metrics": [], "identified_metrics": []}

    def _run_metric_detection(self, dataset_info: Dict[str, Any]) -> Dict[str, Any]:
        from app.ingestion.semantic_profiler import SemanticDataProfiler
        from pathlib import Path

        parquet_path = Path(dataset_info.get("path", ""))
        if not parquet_path.exists():
            return {"metrics": [], "identified_metrics": [], "profile_summary": {"measures": []}}

        try:
            profile = SemanticDataProfiler.profile(parquet_path)
            measures = profile.get("column_categories", {}).get("measures", [])
            return {"metrics": measures, "identified_metrics": measures, "profile_summary": {"measures": measures}}
        except Exception:
            return {"metrics": [], "identified_metrics": [], "profile_summary": {"measures": []}}

    def _run_sql_tests(
        self, dataset_info: Dict[str, Any], test_questions: List[Dict[str, Any]]
    ) -> tuple:
        from app.ai.universal_copilot_brain import UniversalAIBrain
        from pathlib import Path

        parquet_path = Path(dataset_info.get("path", ""))
        if not parquet_path.exists():
            return [], {"error": f"Dataset not found: {parquet_path}"}

        all_scores = []
        details = {}

        for i, question_data in enumerate(test_questions):
            question = question_data.get("question", "")
            expected_intent = question_data.get("expected_intent", "summary")
            expected_metric = question_data.get("expected_metric", "")
            expected_group_by = question_data.get("expected_group_by", "")

            try:
                response = UniversalAIBrain.query(question=question, dataset_id=dataset_info.get("id"))
                sql_query = response.get("support", {}).get("sql_used", "")
                rows = response.get("evidence", [])
                columns_used = response.get("columns", [])
                intent = response.get("support", {}).get("intent", "unknown")

                sql_result = {
                    "sql_query": sql_query,
                    "rows": rows,
                    "error": None,
                    "columns_used": columns_used,
                    "intent": intent,
                }

                score, detail = evaluate_sql_generation(
                    [{"expected_intent": expected_intent, "expected_metric": expected_metric, "expected_group_by": expected_group_by}],
                    [sql_result],
                )
                all_scores.append((f"sql_test_{i}", score, 1.0))
                details[f"question_{i}"] = detail.get(f"question_0", detail)

            except Exception as e:
                all_scores.append((f"sql_test_{i}", 0.0, 1.0))
                details[f"question_{i}"] = {"error": str(e)}

        return all_scores, details

    def _run_recommendation_tests(
        self, dataset_info: Dict[str, Any], test_questions: List[Dict[str, Any]]
    ) -> tuple:
        from app.ai.universal_copilot_brain import UniversalAIBrain
        from pathlib import Path

        parquet_path = Path(dataset_info.get("path", ""))
        if not parquet_path.exists():
            return [], {}

        all_scores = []
        details = {}

        for i, question_data in enumerate(test_questions):
            question = question_data.get("question", "")
            expected_intent = question_data.get("expected_intent", "summary")

            try:
                response = UniversalAIBrain.query(question=question, dataset_id=dataset_info.get("id"))
                insight_result = {
                    "answer": response.get("answer", ""),
                    "data_evidence": response.get("evidence", []),
                    "columns_used": response.get("columns", []),
                    "dataset_used": response.get("dataset", ""),
                    "confidence": response.get("confidence", 0.0),
                }
                recommendation = response.get("support", {}).get("recommendation", {})

                score, detail = evaluate_recommendations(
                    {"intent": expected_intent},
                    insight_result,
                    expected_intent
                )
                all_scores.append((f"rec_test_{i}", score, 1.0))
                details[f"question_{i}"] = detail

            except Exception as e:
                all_scores.append((f"rec_test_{i}", 0.0, 1.0))
                details[f"question_{i}"] = {"error": str(e)}

        return all_scores, details

    def _run_hallucination_tests(self, dataset_info: Dict[str, Any]) -> Dict[str, Any]:
        from app.ai.universal_copilot_brain import UniversalAIBrain
        from pathlib import Path

        parquet_path = Path(dataset_info.get("path", ""))
        if not parquet_path.exists():
            return {"insight_result": {}, "data_rows": [], "validation_result": {}}

        try:
            response = UniversalAIBrain.query(
                question="Summarize the dataset",
                dataset_id=dataset_info.get("id"),
            )
            insight_result = {
                "answer": response.get("answer", ""),
                "data_evidence": response.get("evidence", []),
                "columns_used": response.get("columns", []),
                "dataset_used": response.get("dataset", ""),
                "confidence": response.get("confidence", 0.0),
            }
            validation = response.get("support", {}).get("answer_validation", {})

            return {
                "insight_result": insight_result,
                "data_rows": [],
                "validation_result": validation,
            }
        except Exception:
            return {"insight_result": {}, "data_rows": [], "validation_result": {}}

    def _run_visualization_tests(
        self, dataset_info: Dict[str, Any], test_questions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        from app.ai.universal_copilot_brain import UniversalAIBrain
        from pathlib import Path

        parquet_path = Path(dataset_info.get("path", ""))
        if not parquet_path.exists():
            return {"analysis_result": {}, "question_understanding": {}, "charts_generated": []}

        try:
            question = test_questions[0].get("question", "Summarize the dataset") if test_questions else "Summarize the dataset"
            response = UniversalAIBrain.query(question=question, dataset_id=dataset_info.get("id"))
            analysis_result = {
                "sql_query": response.get("support", {}).get("sql_used", ""),
                "rows": response.get("evidence", []),
                "columns_used": response.get("columns", []),
                "tables_used": response.get("support", {}).get("tables_used", []),
            }
            question_understanding = {
                "intent": response.get("support", {}).get("intent", "unknown"),
                "entities": {},
            }
            charts = []

            return {
                "analysis_result": analysis_result,
                "question_understanding": question_understanding,
                "charts_generated": charts,
            }
        except Exception:
            return {"analysis_result": {}, "question_understanding": {}, "charts_generated": []}

    def _collect_weaknesses(
        self, dimension: str, score: float, details: Dict[str, Any],
        weaknesses: List[str], suggestions: List[str],
    ) -> None:
        if score < 0.5:
            weaknesses.append(f"{dimension}: Low score ({score:.2f}) - critical gap in AI capability")
        elif score < 0.8:
            weaknesses.append(f"{dimension}: Moderate score ({score:.2f}) - needs improvement")

        if isinstance(details, dict):
            for key, value in details.items():
                if isinstance(value, dict) and value.get("f1_score", 1.0) < 0.5:
                    weaknesses.append(f"{dimension}.{key}: F1 score below 0.5")
                if isinstance(value, dict) and value.get("precision", 1.0) < 0.5:
                    weaknesses.append(f"{dimension}.{key}: Precision below 0.5")

        if dimension == "sql_generation" and score < 0.7:
            suggestions.append("Improve SQL generation by enhancing schema-aware query planning")
        if dimension == "entity_detection" and score < 0.7:
            suggestions.append("Enhance entity detection with domain-specific entity dictionaries")
        if dimension == "hallucination_prevention" and score < 0.7:
            suggestions.append("Strengthen hallucination prevention with stricter evidence grounding rules")
        if dimension == "visualization_quality" and score < 0.7:
            suggestions.append("Improve visualization quality by adding more chart type heuristics")
        if dimension == "dataset_understanding" and score < 0.7:
            suggestions.append("Improve dataset understanding with richer schema analysis")
        if dimension == "metric_detection" and score < 0.7:
            suggestions.append("Enhance metric detection with semantic measure classification")

    def _print_dataset_summary(self, result: DatasetEvaluationResult) -> None:
        print(f"  Domain: {result.domain}")
        print(f"  Overall Accuracy: {result.overall_accuracy:.4f}")
        print(f"  Business Understanding: {result.business_understanding:.4f}")
        print(f"  Recommendation Quality: {result.recommendation_quality:.4f}")
        print(f"  SQL Accuracy: {result.sql_accuracy:.4f}")
        print(f"  Visualization Quality: {result.visualization_quality:.4f}")
        if result.weaknesses:
            print(f"  Weaknesses: {len(result.weaknesses)}")
        if result.suggestions:
            print(f"  Suggestions: {len(result.suggestions)}")

    def _build_report(self, dataset_results: List[DatasetEvaluationResult]) -> EvaluationReport:
        overall_scores = {}
        for metric in ["overall_accuracy", "business_understanding", "recommendation_quality", "sql_accuracy", "visualization_quality"]:
            values = [getattr(r, metric) for r in dataset_results]
            overall_scores[metric] = round(sum(values) / len(values), 4) if values else 0.0

        all_weaknesses = []
        all_suggestions = []
        for result in dataset_results:
            all_weaknesses.extend(result.weaknesses)
            all_suggestions.extend(result.suggestions)

        weakness_counts: Dict[str, int] = {}
        for w in all_weaknesses:
            key = w.lower().strip()
            weakness_counts[key] = weakness_counts.get(key, 0) + 1

        sorted_weaknesses = sorted(weakness_counts.items(), key=lambda x: -x[1])

        unique_suggestions = list(dict.fromkeys(all_suggestions))

        return EvaluationReport(
            dataset_results=dataset_results,
            overall_scores=overall_scores,
            weaknesses=[{"weakness": w, "occurrence_count": c} for w, c in sorted_weaknesses],
            suggestions=unique_suggestions,
            generated_at=datetime.now().isoformat(),
        )

    def _save_report(self, report: EvaluationReport) -> None:
        report_path = self.output_dir / "evaluation_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2, default=str)
        print(f"\nReport saved to: {report_path}")

    def _print_final_summary(self, report: EvaluationReport) -> None:
        print(f"\n{'=' * 80}")
        print("EVALUATION SUMMARY")
        print(f"{'=' * 80}")
        for metric, value in report.overall_scores.items():
            print(f"  {metric}: {value:.4f}")
        print(f"\n  Datasets evaluated: {len(report.dataset_results)}")
        print(f"  Total weaknesses found: {len(report.weaknesses)}")
        print(f"  Total suggestions: {len(report.suggestions)}")
        print(f"{'=' * 80}")


def run_evaluation(config: Optional[EvaluationConfig] = None) -> EvaluationReport:
    """Entry point to run the full evaluation framework."""
    framework = EvaluationFramework(config)
    return framework.run()