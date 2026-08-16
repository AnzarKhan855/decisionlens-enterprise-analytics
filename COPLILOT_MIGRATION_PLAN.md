# DecisionLens Universal Enterprise Copilot - Implementation Plan

## STEP 1: Repository Exploration Complete

### AI/Copilot-Related Modules Identified

| Module | File | Role |
|--------|------|------|
| UniversalAIBrain | `backend/app/ai/universal_copilot_brain.py` | **Current** monolithic AI brain (1036 lines) |
| Copilot API | `backend/app/api/v1/copilot_api.py` | Main `/api/v1/ai/copilot/query` endpoint |
| AI Assistant API | `backend/app/api/v1/ai_assistant_api.py` | Legacy `/api/v1/ai/assistant/query` endpoint |
| Conversation Memory | `backend/app/ai/conversation_memory.py` | In-memory session history |
| Answer Validation | `backend/app/ai/validation/answer_validator.py` | Evidence validation layer |
| Validation Schemas | `backend/app/ai/validation/schemas.py` | Pydantic validation models |
| UniversalAnalyticsEngine | `backend/app/analytics/universal_engine.py` | Analytics orchestrator |
| RecommendationEngine | `backend/app/analytics/recommendation_engine.py` | Recommendation generator |
| UniversalPredictionEngine | `backend/app/ml/prediction_engine.py` | Prediction engine |
| UniversalExecutiveReportEngine | `backend/app/reports/executive_report_engine.py` | Report generator |
| ChartEngine | `backend/app/analytics/chart_engine.py` | Visualization engine |
| Dashboard Storyteller | `backend/app/dashboard/storyteller.py` | Dashboard builder |
| SemanticModel | `backend/app/semantic_model/core.py` | Schema/domain model |
| DynamicDashboardService | `backend/app/services/dynamic_dashboard_service.py` | Dashboard service |

---

## STEP 2: Implementation Plan

### Current Copilot Architecture

```
User Question
    |
    v
Copilot API (copilot_api.py)
    |
    v
UniversalAIBrain.query()
    |
    +-- _detect_intent()        [regex-based, 14 intent patterns]
    +-- _resolve_parquet_path()
    +-- SemanticDataProfiler.profile()
    +-- _extract_measures_dimensions()
    +-- _generate_sql()          [DUPLICATE - simplistic SQL generation]
    +-- DuckDBEngine.query()
    +-- _build_grounded_answer() [DUPLICATE - hardcoded answer templates]
    +-- _build_recommendations() [DUPLICATE - duplicates RecommendationEngine]
    +-- _run_universal_analytics() [calls UniversalAnalyticsEngine]
    +-- _run_prediction()        [calls UniversalPredictionEngine]
    +-- _build_executive_report() [calls UniversalExecutiveReportEngine]
    +-- AnswerValidationLayer.validate()
    +-- ConversationMemory.add_turn()
    |
    v
Response Dict (inconsistent format)
```

### Duplicate Logic

1. **SQL Generation**: `UniversalAIBrain._generate_sql()` duplicates `UniversalAnalyticsEngine._compute_*` methods with naive regex-based SQL
2. **Answer Building**: `UniversalAIBrain._build_grounded_answer()` has hardcoded templates per intent - duplicates report engine
3. **Recommendations**: `UniversalAIBrain._build_recommendations()` duplicates `UniversalAnalyticsEngine._compute_recommendations()`
4. **Evidence Validation**: Inline validation in UniversalAIBrain + separate AnswerValidationLayer
5. **Parquet Path Resolution**: Duplicated in `copilot_api.py`, `ai_assistant_api.py`, `UniversalAIBrain`, `dynamic_dashboard_service.py`
6. **Semantic Model Building**: Duplicated pattern in multiple files

### Missing Capabilities

1. **Chart Explanation**: "Explain this chart" not handled
2. **Report Explanation**: "Explain this report" not handled
3. **Dashboard Explanation**: "Explain this dashboard" not handled
4. **Prediction Explanation**: "Explain this prediction" not handled
5. **Recommendation Explanation**: "Explain this recommendation" not handled
6. **Specific Report Types**: Board summary, investor summary, cybersecurity, healthcare, HR, manufacturing reports not routed
7. **Context-Aware Follow-ups**: History is retrieved but not deeply used for resolution
8. **Standardized Response**: No 7-section guaranteed structure

### Weaknesses

1. Monolithic 1036-line class doing everything
2. Regex intent detection is fragile
3. No proper error recovery per section
4. Inconsistent response format between endpoints
5. Hardcoded fallback responses
6. SQL injection risk in `_generate_sql` (uses string formatting)
7. No graceful degradation when analytics fails
8. Duplicate code increases maintenance burden

### Files to Modify

| File | Changes |
|------|---------|
| `backend/app/ai/universal_copilot_brain.py` | **Major refactor** - Remove duplicate logic, add 7-section assembly |
| `backend/app/api/v1/copilot_api.py` | Update response mapping, add new endpoints |
| `backend/app/api/v1/ai_assistant_api.py` | Deprecate, route through copilot |
| `backend/app/analytics/universal_engine.py` | Minor: add chart explanation data |
| `backend/app/reports/executive_report_engine.py` | Minor: add report-type-specific summaries |
| `backend/app/ml/prediction_engine.py` | No changes needed |
| `backend/app/ai/conversation_memory.py` | Enhance context resolution |

### Migration Strategy

1. **Phase 1**: Refactor UniversalAIBrain into orchestrator-only
   - Remove `_generate_sql()`
   - Remove `_build_grounded_answer()`
   - Remove `_build_recommendations()`
   - Keep `_detect_intent()`, `_resolve_parquet_path()`, `_calculate_confidence()`
   - Add new `_assemble_copilot_response()` method

2. **Phase 2**: Implement 7-section response builder
   - Section 1: Executive Answer
   - Section 2: What happened?
   - Section 3: Why?
   - Section 4: What happens next?
   - Section 5: What should we do?
   - Section 6: Evidence
   - Section 7: Executive Summary

3. **Phase 3**: Update API endpoints
   - Standardize response format
   - Add new specialized endpoints
   - Deprecate old endpoint

4. **Phase 4**: Testing & validation
   - Run all backend tests
   - Fix compile errors
   - Verify response format

### Risks

1. Breaking changes to existing API consumers
2. Performance regression from additional analytics pipeline
3. Memory usage from conversation history
4. SQL generation quality without the old `_generate_sql` method

### Testing Strategy

1. Run existing tests: `cd backend && python -m pytest`
2. Verify copilot_api.py returns new format
3. Verify all 7 sections present in response
4. Verify no hallucination (all numbers from SQL)
5. Verify domain adaptation works

### Acceptance Criteria

1. UniversalAIBrain is the ONLY AI entry point
2. Every response has exactly 7 sections
3. No duplicate SQL generation, recommendation, or answer logic
4. All numbers traceable to executed SQL
5. Conversation memory works for follow-ups
6. Supports all query types: explain chart, board summary, investor summary, etc.
7. Domain-agnostic (no retail/healthcare assumptions)
8. All existing tests pass

---

## STEP 3: Implementation
