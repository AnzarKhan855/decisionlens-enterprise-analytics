# DecisionLens AI Evidence Report

## Overview

DecisionLens implements a strict **Evidence Builder** module that ensures every AI response is grounded in verified data, traceable SQL execution, and computed statistics. This document describes the Evidence Builder architecture, its guarantees, and how it prevents hallucination.

---

## Pipeline Architecture

```
Dataset
   Ã¢â€ â€œ
Validation
   Ã¢â€ â€œ
Analytics (UniversalAnalyticsEngine)
   Ã¢â€ â€œ
KPIs
   Ã¢â€ â€œ
Forecast (UniversalPredictionEngine)
   Ã¢â€ â€œ
Recommendation Engine (RecommendationEngine)
   Ã¢â€ â€œ
Evidence Builder (EvidenceBuilder)
   Ã¢â€ â€œ
Executive Response (UniversalAIBrain)
```

Every AI response in DecisionLens must pass through the **Evidence Builder** before reaching the user.

---

## Evidence Report Schema

The `EvidenceReport` dataclass (defined in `backend/app/schemas/analytics.py`) contains the following fields:

| Field | Type | Description |
|---|---|---|
| `evidence` | `str` | Text describing what data supports the conclusion |
| `confidence` | `float` | Confidence score (0.0 to 1.0) computed by ExplainableAIEngine |
| `rows_analyzed` | `int` | Number of rows analyzed from the dataset |
| `columns_analyzed` | `List[str]` | Columns used in the analysis |
| `business_reasoning` | `str` | Explanation of why the conclusion was reached |
| `recommendation` | `str` | Evidence-backed recommendation text |
| `expected_impact` | `str` | Expected business impact of the recommendation |
| `priority` | `str` | Priority level: CRITICAL, HIGH, MEDIUM, or LOW |
| `models_used` | `List[str]` | Statistical/AI models used in the analysis |
| `sql_query` | `str` | The SQL query executed to produce the result |
| `tables_used` | `List[str]` | Tables/datasets referenced |
| `validation_status` | `str` | Status of data validation: COMPUTED, VERIFIED, ERROR, UNAVAILABLE |
| `disclaimer` | `str` | Disclaimer if evidence is insufficient |
| `prediction_feasible` | `bool` | Whether prediction was feasible |
| `prediction_limitation` | `Optional[str]` | Why prediction was not feasible |
| `anomalies_detected` | `int` | Number of anomalies detected |
| `drivers_identified` | `int` | Number of key business drivers identified |
| `kpi_count` | `int` | Number of KPIs computed |
| `forecast_available` | `bool` | Whether forecast models are available |
| `recommendation_count` | `int` | Number of recommendations generated |
| `raw` | `Dict[str, Any]` | Raw payload for debugging and traceability |

---

## Evidence Builder Guarantees

### 1. Never Hallucinate
- Every claim in the evidence report is traceable to executed SQL or computed statistics.
- The Evidence Builder receives `analytics_dict`, `predictions`, `recommendations`, `evidence_rows`, `sql_query`, `validation`, and `profile` directly from the analytics engines.
- If evidence does not exist, the `disclaimer` field explicitly states so.

### 2. Never Guess
- The Evidence Builder does not generate predictions, recommendations, or business reasoning from language models.
- All data comes from:
  - Zero-copy DuckDB execution (`sql_query`, `evidence_rows`)
  - `SemanticAnalyticsEngine` (KPIs, trends, distributions, rankings)
  - `StatisticalAnomalyEngine` (anomalies, outliers)
  - `VarianceDecompositionEngine` (root causes, drivers)
  - `UniversalPredictionEngine` (forecasts)
  - `RecommendationEngine` (evidence-based recommendations)
  - `ExplainableAIEngine` (confidence scoring)

### 3. Never Invent
- All numeric values are computed from the dataset.
- If a field cannot be populated from the analytics output, it is marked as "Insufficient evidence" or left empty.
- No external knowledge, assumptions, or language model outputs are used to populate the evidence report.

---

## Evidence Builder Module

**Location:** `backend/app/ai/evidence_builder.py`

**Class:** `EvidenceBuilder`

**Method:** `build(...)`

The `EvidenceBuilder.build` method accepts:
- `analytics_dict`: Full analytics result dictionary
- `predictions`: List of prediction objects
- `recommendations`: List of recommendation objects
- `evidence_rows`: Rows returned by the executed SQL query
- `sql_query`: The SQL query string
- `tables_used`: List of table names
- `columns_used`: List of column names
- `validation`: Validation dictionary
- `profile`: Dataset profile dictionary
- `domain`: Business domain string

It returns an `EvidenceReport` instance.

---

## Integration Points

### UniversalAnalyticsEngine
In `backend/app/analytics/universal_engine.py`, after all analysis is complete, the `EvidenceBuilder.build` method is called to construct the `evidence_report` field on the `AnalyticsResult` object.

### UniversalAIBrain
In `backend/app/ai/universal_copilot_brain.py`, after all engines have run and validation is complete, the `EvidenceBuilder.build` method is called again to construct the `evidence_report` field on the copilot response.

---

## Validation & Confidence

The `ExplainableAIEngine.compute_confidence` method computes the confidence score from empirical data quality factors:
- Data Completeness (missing values)
- Sample Size (row count)
- Historical Coverage (temporal span)
- Variance (coefficient of variation)
- Outlier Ratio
- Feature Quality (correlation strength)
- Evidence Strength (SQL result coverage)
- Prediction Quality
- Recommendation Quality

No hardcoded confidence values are used. The confidence score is computed solely from the dataset profile and analysis results.

---

## Answer Validation

The `AnswerValidationLayer` (`backend/app/ai/validation/answer_validator.py`) validates every AI response before it is returned. It checks:
- Evidence traceability
- Numeric claim accuracy
- Recommendation grounding
- Insight traceability

If validation fails, the response is rejected and the confidence score is adjusted accordingly.

---

## Response Structure

Every AI response in DecisionLens contains:

```json
{
  "answer": "...",
  "executive_summary": "...",
  "evidence": { ... },
  "evidence_list": [ ... ],
  "confidence": 0.0,
  "evidence_report": {
    "evidence": "...",
    "confidence": 0.0,
    "rows_analyzed": 0,
    "columns_analyzed": [],
    "business_reasoning": "...",
    "recommendation": "...",
    "expected_impact": "...",
    "priority": "...",
    "models_used": [],
    "sql_query": "...",
    "tables_used": [],
    "validation_status": "...",
    "disclaimer": "",
    "prediction_feasible": false,
    "prediction_limitation": null,
    "anomalies_detected": 0,
    "drivers_identified": 0,
    "kpi_count": 0,
    "forecast_available": false,
    "recommendation_count": 0,
    "raw": { ... }
  },
  "support": { ... }
}
```

---

## Anti-Hallucination Rules

1. **No evidence = explicit statement**: If the analysis returns no results, the `disclaimer` field states this clearly.
2. **No fabricated numbers**: All numeric values are computed from the dataset via DuckDB SQL.
3. **No external assumptions**: No language model is used to generate numeric claims.
4. **Traceability required**: Every claim must be traceable to a specific SQL query or computed statistic.
5. **Validation gate**: The `AnswerValidationLayer` acts as a gatekeeper before any response is returned.

---

## Files

| File | Description |
|---|---|
| `backend/app/ai/evidence_builder.py` | EvidenceBuilder implementation |
| `backend/app/schemas/analytics.py` | EvidenceReport dataclass |
| `backend/app/analytics/universal_engine.py` | Integration with UniversalAnalyticsEngine |
| `backend/app/ai/universal_copilot_brain.py` | Integration with UniversalAIBrain |
| `backend/app/ai/explainable_ai_engine.py` | Confidence scoring |
| `backend/app/ai/validation/answer_validator.py` | Response validation |

---

*This document is auto-generated and reflects the current state of the DecisionLens Evidence Builder implementation.*
