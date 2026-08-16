# DecisionLens - Agent Instructions

## Project Overview

DecisionLens is a decision intelligence platform with a FastAPI backend, React frontend, DuckDB data warehouse, and AI-powered analytics agents.

## Key Directories

- `backend/app/ai/agents/` - AI agent modules (dataset understanding, entity detection, SQL generation, recommendation, visualization, insight generation)
- `backend/app/evaluation/` - Evaluation framework for measuring AI quality
- `backend/app/semantic_model/` - Semantic model entity/metric/relationship detection
- `backend/app/ingestion/` - Data ingestion and profiling
- `backend/app/validation/` - Answer validation and hallucination prevention
- `backend/tests/` - Test suite

## Universal Analytics Engine

Located at `backend/app/analytics/universal_engine.py`:

- **`UniversalAnalyticsEngine`** - The single unified analytics orchestrator
  - Input: `SemanticModel` + `parquet_path`
  - Output: `AnalyticsResult`
  - Reuses all existing statistical modules: `SemanticAnalyticsEngine`, `StatisticalAnomalyEngine`, `VarianceDecompositionEngine`, `AutoInsights`, `RecommendationEngine`, `BusinessHealthEngine`, `UniversalPredictionEngine`, `TimeSeriesForecaster`, `ChartEngine`
  - Answers four questions for every dataset:
    1. What happened? (KPIs, trends, distributions, growth, decline, rankings)
    2. Why did it happen? (root causes, drivers, correlations, anomalies, outliers)
    3. What will happen? (time-series forecasting, regression, clustering predictions)
    4. What should we do? (evidence-based recommendations, risks, opportunities)
  - Auto-specializes results based on `SemanticModel.domain` without hardcoded assumptions

### AnalyticsResult Schema

Located at `backend/app/schemas/analytics.py`:

- `executive_summary`, `kpis`, `summary_statistics`, `volume`, `utilization`, `performance`
- `trends`, `growth`, `decline`, `distributions`, `rankings`
- `root_causes`, `drivers`, `correlations`, `relationships`, `dimension_impact`, `segment_comparisons`
- `outliers`, `anomalies`, `patterns`
- `predictions`, `prediction_strategy`, `prediction_feasible`, `prediction_limitation`
- `recommendations`, `risks`, `opportunities`, `key_drivers`
- `critical_findings`, `positive_findings`, `negative_findings`
- `health_score`, `confidence_score`, `evidence`
- `domain`, `dataset_type`, `semantic_model`, `generated_at`

### Consumers

Every module consumes `AnalyticsResult`:

- **Dashboard** (`DynamicDashboardService`) - builds dashboard dict from AnalyticsResult
- **Reports** (`ReportsAPI`) - builds executive reports from dashboard/AnalyticsResult
- **Copilot** (`EnterpriseCopilotEngine`) - receives pre-computed analytics for grounded responses
- **Prediction Engine** (`UniversalPredictionEngine`) - accepts optional `analytics_result` parameter
- **Recommendation Engine** (`RecommendationEngine`) - integrated via UniversalAnalyticsEngine

### Analytics API

- `GET /api/v1/analytics/universal` - Returns full `AnalyticsResult` from UniversalAnalyticsEngine
- Legacy endpoints (`/kpis`, `/insights`, `/store-performance`, `/top-products`, `/categories`, `/monthly-trend`, `/sales-loss`, `/root-cause/{period}`, `/anomalies`, `/strategic-decisions`) - backward-compatible wrappers that route through UniversalAnalyticsEngine where applicable

## Evaluation Framework

Located at `backend/app/evaluation/`:

- **`benchmark_datasets/generators.py`** - Generates 7 benchmark datasets (Retail, Finance, Healthcare, HR, Marketing, Education, Operations) as CSV files
- **`evaluators/`** - Individual evaluators for each dimension:
  - `dataset_understanding_evaluator.py` - Tests domain identification, schema comprehension, row/column accuracy
  - `entity_detection_evaluator.py` - Tests entity detection precision/recall/F1
  - `metric_detection_evaluator.py` - Tests metric detection precision/recall/F1
  - `sql_generation_evaluator.py` - Tests SQL syntax, GROUP BY, ORDER BY, LIMIT correctness
  - `recommendation_evaluator.py` - Tests intent alignment, evidence grounding, actionability
  - `hallucination_evaluator.py` - Tests numeric traceability, fabrication risk, confidence reasonableness
  - `visualization_evaluator.py` - Tests chart type matching, data completeness, label accuracy
- **`framework.py`** - Main orchestration: `EvaluationFramework.run()` evaluates all domains
- **`runner.py`** - Entry point: `python -m app.evaluation.runner`
- **`reporter.py`** - `generate_weaknesses_report()` and `generate_markdown_report()` for weaknesses/suggestions
- **`models.py`** - `EvaluationScore`, `DatasetEvaluationResult`, `EvaluationReport` dataclasses
- **`schemas.py`** - Pydantic `EvaluationConfig` with domain/dimension settings
- **`test_evaluation.py`** - 25 unit tests covering all evaluators

### Running Evaluation

```
cd backend
python -m app.evaluation.runner
```

This generates CSV benchmark datasets in `data/benchmark/` and a JSON report in `data/evaluation_results/evaluation_report.json`.

### Evaluation Dimensions (6)

1. Dataset Understanding - domain identification, schema comprehension
2. Entity Detection - precision/recall/F1 of business entity detection
3. Metric Detection - precision/recall/F1 of quantitative metric detection
4. SQL Generation - syntax validity, correct clauses for intent
5. Recommendations - intent alignment, evidence grounding, actionability
6. Hallucination Prevention - numeric traceability, fabrication risk

### Output Scores (5)

- Overall AI Accuracy (weighted across all 6 dimensions)
- Business Understanding (dimensions 1-3)
- Recommendation Quality (dimension 5)
- SQL Accuracy (dimension 4)
- Visualization Quality (separate evaluator)

### Weaknesses & Suggestions

The `reporter.py` module contains:
- `WEAKNESSES_DB` - Predefined descriptions/causes/improvements for each dimension
- `generate_weaknesses_report()` - Aggregates weaknesses across all datasets
- `generate_markdown_report()` - Full Markdown report with scores, weaknesses, suggestions
