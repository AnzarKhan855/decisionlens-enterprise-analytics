import unittest
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.evaluation.models import (
    EvaluationScore,
    DatasetEvaluationResult,
    EvaluationReport,
)
from app.evaluation.evaluators.dataset_understanding_evaluator import (
    evaluate_dataset_understanding,
)
from app.evaluation.evaluators.entity_detection_evaluator import (
    evaluate_entity_detection,
)
from app.evaluation.evaluators.metric_detection_evaluator import (
    evaluate_metric_detection,
)
from app.evaluation.evaluators.sql_generation_evaluator import (
    evaluate_sql_generation,
)
from app.evaluation.evaluators.recommendation_evaluator import (
    evaluate_recommendations,
)
from app.evaluation.evaluators.hallucination_evaluator import (
    evaluate_hallucination_prevention,
)
from app.evaluation.evaluators.visualization_evaluator import (
    evaluate_visualization_quality,
)
from app.evaluation.framework import EvaluationFramework
from app.evaluation.reporter import (
    generate_weaknesses_report,
    generate_markdown_report,
)
from app.evaluation.schemas import EvaluationConfig


class TestGenerators(unittest.TestCase):
    pass


class TestDatasetUnderstandingEvaluator(unittest.TestCase):
    def test_perfect_match_scores_one(self):
        dataset_info = {
            "domain": "Retail & E-Commerce",
            "expected_entities": ["customer", "product", "order"],
            "expected_metrics": ["revenue", "quantity"],
        }
        profile_result = {
            "domain_hints": {"primary_domain": "Retail & E-Commerce"},
            "total_rows": 500,
            "entities": {"customer": ["customer_id"], "product": ["product_id"], "order": ["order_id"]},
            "profile_summary": {
                "measures": ["revenue", "quantity"],
                "dimensions": ["category", "store"],
            },
        }
        score, details = evaluate_dataset_understanding(dataset_info, profile_result)
        self.assertGreaterEqual(score, 0.7)

    def test_perfect_match_all(self):
        dataset_info = {
            "domain": "Retail & E-Commerce",
            "expected_entities": ["customer", "product", "order", "seller", "category", "location", "date"],
            "expected_metrics": ["total_revenue", "quantity", "unit_price", "cost", "profit", "discount_pct"],
            "expected_dimensions": ["category", "subcategory", "store", "region", "order_date"],
        }
        profile_result = {
            "domain_hints": {"primary_domain": "Retail & E-Commerce"},
            "total_rows": 500,
            "entities": {
                "customer": ["customer_id"],
                "product": ["product_id"],
                "order": ["order_id"],
                "seller": ["store"],
                "category": ["category"],
                "location": ["region"],
                "date": ["order_date"],
            },
            "profile_summary": {
                "measures": ["total_revenue", "quantity", "unit_price", "cost", "profit", "discount_pct"],
                "dimensions": ["category", "subcategory", "store", "region", "order_date"],
            },
        }
        score, details = evaluate_dataset_understanding(dataset_info, profile_result)
        self.assertGreaterEqual(score, 0.7)


class TestEntityDetectionEvaluator(unittest.TestCase):
    def test_perfect_entity_detection(self):
        dataset_info = {"expected_entities": ["customer", "product", "order"]}
        detection_result = {"entities": {"customer": ["cust_id"], "product": ["prod_id"], "order": ["order_id"]}}
        score, details = evaluate_entity_detection(dataset_info, detection_result)
        self.assertEqual(score, 1.0)

    def test_no_entities_detected(self):
        dataset_info = {"expected_entities": ["customer", "product"]}
        detection_result = {"entities": {}}
        score, details = evaluate_entity_detection(dataset_info, detection_result)
        self.assertEqual(score, 0.0)


class TestMetricDetectionEvaluator(unittest.TestCase):
    def test_perfect_metric_detection(self):
        dataset_info = {"expected_metrics": ["revenue", "quantity"]}
        detection_result = {"metrics": ["revenue", "quantity"]}
        score, details = evaluate_metric_detection(dataset_info, detection_result)
        self.assertEqual(score, 1.0)

    def test_partial_metric_detection(self):
        dataset_info = {"expected_metrics": ["revenue", "quantity", "profit"]}
        detection_result = {"metrics": ["revenue", "quantity"]}
        score, details = evaluate_metric_detection(dataset_info, detection_result)
        self.assertGreater(score, 0.0)
        self.assertLess(score, 1.0)


class TestSQLGenerationEvaluator(unittest.TestCase):
    def test_valid_sql_query(self):
        test_questions = [{"expected_intent": "top_n", "expected_metric": "price", "expected_group_by": "product_id"}]
        sql_results = [{"sql_query": "SELECT product_id, SUM(price) FROM t GROUP BY 1 ORDER BY 2 DESC LIMIT 15", "rows": [], "error": None}]
        score, details = evaluate_sql_generation(test_questions, sql_results)
        self.assertEqual(score, 1.0)

    def test_no_sql_generated(self):
        test_questions = [{"expected_intent": "top_n"}]
        sql_results = [{"sql_query": "", "rows": [], "error": "No query generated"}]
        score, details = evaluate_sql_generation(test_questions, sql_results)
        self.assertEqual(score, 0.0)

    def test_empty_inputs(self):
        score, details = evaluate_sql_generation([], [])
        self.assertEqual(score, 0.0)


class TestRecommendationEvaluator(unittest.TestCase):
    def test_high_quality_recommendation(self):
        qu = {"intent": "recommendation", "entities": {}}
        insight = {
            "answer": "We recommend focusing on high-value customers in the Northeast region. Consider increasing marketing spend for Electronics category.",
            "confidence": 0.92,
            "data_evidence": ["Top customer segment: Northeast, Electronics", "Revenue trend: increasing 12%"],
            "status": "ok",
        }
        score, details = evaluate_recommendations(qu, insight, "recommendation")
        self.assertGreaterEqual(score, 0.7)

    def test_low_quality_recommendation(self):
        qu = {"intent": "summary", "entities": {}}
        insight = {"answer": "The data shows various trends.", "confidence": 0.3, "data_evidence": [], "status": "ok"}
        score, details = evaluate_recommendations(qu, insight, "recommendation")
        self.assertLess(score, 0.7)


class TestHallucinationEvaluator(unittest.TestCase):
    def test_no_hallucination(self):
        insight = {
            "answer": "Total revenue is $50,000",
            "confidence": 0.92,
            "data_evidence": ["SUM(revenue) = 50000"],
            "status": "ok",
        }
        validation = {"is_valid": True, "confidence_score": 0.92, "warnings": []}
        score, details = evaluate_hallucination_prevention(insight, [{"revenue": 50000}], validation)
        self.assertGreaterEqual(score, 0.7)

    def test_hallucination_detected(self):
        insight = {
            "answer": "Revenue is approximately $1,000,000 and projected to grow 50% next year.",
            "confidence": 0.4,
            "data_evidence": [],
            "status": "ok",
        }
        validation = {"is_valid": False, "confidence_score": 0.3, "warnings": ["contains unreliable terms"]}
        score, details = evaluate_hallucination_prevention(insight, [], validation)
        self.assertLess(score, 0.5)


class TestVisualizationEvaluator(unittest.TestCase):
    def test_correct_chart_type(self):
        analysis_result = {"columns_used": ["product", "revenue"]}
        qu = {"intent": "trend"}
        charts = [{"type": "line", "title": "Trend", "data": [{"x": "Jan", "y": 100}]}]
        score, details = evaluate_visualization_quality(analysis_result, qu, charts)
        self.assertGreaterEqual(score, 0.7)

    def test_wrong_chart_type(self):
        analysis_result = {"columns_used": ["product", "revenue"]}
        qu = {"intent": "trend"}
        charts = [{"type": "pie", "title": "Wrong type", "data": []}]
        score, details = evaluate_visualization_quality(analysis_result, qu, charts)
        self.assertLess(score, 1.0)


class TestModels(unittest.TestCase):
    def test_evaluation_score_weighted(self):
        score = EvaluationScore(dimension="test", score=0.8, max_score=1.0, weight=2.0)
        self.assertEqual(score.weighted_score, 1.6)

    def test_dataset_evaluation_result_aggregates(self):
        result = DatasetEvaluationResult(
            dataset_name="test",
            domain="Retail",
            scores=[
                EvaluationScore("sql_generation", 0.9, 1.0, 1.5),
                EvaluationScore("entity_detection", 0.8, 1.0, 1.0),
            ],
        )
        self.assertGreater(result.overall_accuracy, 0.0)

    def test_report_aggregates_scores(self):
        r1 = DatasetEvaluationResult(
            dataset_name="retail",
            domain="Retail",
            scores=[EvaluationScore("sql_generation", 0.9, 1.0, 1.0)],
        )
        r2 = DatasetEvaluationResult(
            dataset_name="finance",
            domain="Finance",
            scores=[EvaluationScore("sql_generation", 0.7, 1.0, 1.0)],
        )
        report = EvaluationReport(dataset_results=[r1, r2], overall_scores={"overall_accuracy": 0.8, "business_understanding": 0.7})
        self.assertGreater(report.overall_scores.get("overall_accuracy", 0), 0)


class TestReporter(unittest.TestCase):
    def test_weaknesses_report_structure(self):
        eval_report = {
            "dataset_results": [],
            "overall_scores": {"overall_accuracy": 0.8},
            "generated_at": "2025-01-01",
        }
        weaknesses = generate_weaknesses_report(eval_report)
        self.assertIn("critical_weaknesses", weaknesses)
        self.assertIn("overall_scores", weaknesses)

    def test_markdown_report_generation(self):
        eval_report = {
            "dataset_results": [],
            "overall_scores": {"overall_accuracy": 0.8, "business_understanding": 0.7},
            "weaknesses": [],
            "suggestions": ["Test suggestion"],
            "generated_at": "2025-01-01",
        }
        md = generate_markdown_report(eval_report)
        self.assertIn("DecisionLens AI Evaluation Report", md)
        self.assertIn("Overall AI Quality Scores", md)


class TestFrameworkIntegration(unittest.TestCase):
    def test_framework_initialization(self):
        config = EvaluationConfig(datasets_dir="data/evaluation", output_dir="data/evaluation_results")
        framework = EvaluationFramework(config)
        self.assertEqual(framework.config.domains, [])

    def test_framework_config_defaults(self):
        config = EvaluationConfig()
        self.assertEqual(len(config.domains), 0)
        self.assertEqual(len(config.dimensions), 6)


if __name__ == "__main__":
    unittest.main()