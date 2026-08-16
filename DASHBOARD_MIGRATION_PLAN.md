# Universal Dashboard Storytelling Engine Ã¢â‚¬â€ Implementation Plan

## 1. Current Architecture

DecisionLens currently has **~50 dashboard-related files** spanning backend and frontend, with significant duplication and retail-specific assumptions hardcoded throughout.

### Backend Dashboard Flow
```
User Request
    Ã¢â€ â€œ
API Endpoint (dashboard.py, executive.py, analytics.py, reports_api.py)
    Ã¢â€ â€œ
Service Layer (dynamic_dashboard_service.py, executive_service.py, analytics_service.py)
    Ã¢â€ â€œ
Analytics Engines (universal_engine.py, recommendation_engine.py, auto_insights.py, chart_engine.py, health_engine.py)
    Ã¢â€ â€œ
ML Engine (prediction_engine.py)
    Ã¢â€ â€œ
Report Engine (executive_report_engine.py)
    Ã¢â€ â€œ
AI Brain (universal_copilot_brain.py)
    Ã¢â€ â€œ
Frontend (Next.js components)
```

### Key Backend Files
| File | Role | Lines |
|------|------|-------|
| `services/dynamic_dashboard_service.py` | Central dashboard orchestration | 480 |
| `services/dashboard_service.py` | Legacy retail dashboard | 34 |
| `services/executive_service.py` | Pass-through wrapper | 8 |
| `services/analytics_service.py` | Legacy analytics endpoints | 224 |
| `analytics/universal_engine.py` | Unified analytics engine | 826 |
| `analytics/dashboard_generator.py` | Domain-specific KPI generator | 108 |
| `analytics/dynamic_kpis.py` | Alternative KPI engine | 76 |
| `analytics/chart_engine.py` | Chart spec generator | 268 |
| `analytics/health_engine.py` | Health score calculator | 56 |
| `analytics/recommendation_engine.py` | Recommendation generator | 117 |
| `analytics/auto_insights.py` | Narrative insight generator | 98 |
| `reports/executive_report_engine.py` | 13-section report builder | 657 |
| `api/v1/dashboard.py` | Dashboard API router | 49 |
| `api/v1/executive.py` | Legacy executive endpoint | 28 |
| `api/v1/analytics.py` | Legacy analytics endpoints | 302 |
| `api/v1/reports_api.py` | Report endpoints | 90 |
| `ai/universal_copilot_brain.py` | Single AI brain | 1036 |
| `ml/prediction_engine.py` | Prediction engine | 665 |

### Key Frontend Files
| File | Role | Lines |
|------|------|-------|
| `components/dashboard/DynamicDashboardShell.tsx` | Main dashboard shell | 417 |
| `components/dashboard/KPISection.tsx` | **Legacy hardcoded retail KPIs** | 317 |
| `components/dashboard/DynamicKPISection.tsx` | Dynamic KPI cards | 139 |
| `components/dashboard/ExecutiveActionCenter.tsx` | Recommendation cards | 122 |
| `components/dashboard/ExecutiveNewsfeed.tsx` | News/alert cards | 98 |
| `components/dashboard/ExecutiveTimeline.tsx` | **100% hardcoded fake data** | 103 |
| `components/dashboard/BenchmarkEngineCard.tsx` | **100% hardcoded fake data** | 101 |
| `components/dashboard/StrategicDecisionsCard.tsx` | Strategic decisions | 111 |
| `components/dashboard/WhatIfSimulator.tsx` | Scenario simulator | 177 |
| `components/dashboard/AIAssistantChat.tsx` | Embedded copilot | 297 |
| `components/dashboard/MultiAgentExecutiveView.tsx` | C-Suite agent view | 83 |
| `components/dashboard/InsightExplanationModal.tsx` | Insight modal | 104 |
| `components/dashboard/GuidedOnboardingModal.tsx` | Onboarding wizard | 218 |
| `components/dashboard/ExecutiveSearchModal.tsx` | Cmd+K search | 134 |
| `components/dashboard/ExecutiveStoryMode.tsx` | Narrative story | 61 |
| `components/charts/DynamicChartRenderer.tsx` | Chart renderer | 304 |
| `components/charts/ForecastChartRenderer.tsx` | Forecast chart | 198 |
| `app/dynamic-dashboard/page.tsx` | Route wrapper | 5 |
| `app/page.tsx` | Home page with briefing | 288 |

---

## 2. Problems

### 2.1 Duplicate Components
| Duplicate | Locations |
|-----------|-----------|
| Parquet path resolution | `dynamic_dashboard_service.py`, `universal_copilot_brain.py`, `copilot_api.py` |
| Currency keyword detection | `dynamic_dashboard_service.py:177`, `dynamic_kpis.py:34`, `universal_engine.py:229`, `kpi_detector.py:70-77`, `recommendation_engine.py` |
| KPI computation | `universal_engine.py:_compute_kpis()`, `dynamic_dashboard_service.py:_fast_kpis()`, `dynamic_kpis.py`, `dashboard_generator.py` |
| Executive briefing structure | Backend `_analytics_result_to_dashboard_dict()`, frontend `DynamicDashboardShell.tsx:169`, `DynamicKPISection.tsx:117-129`, `GuidedOnboardingModal.tsx:17-19` |
| Default workspace ID | `upload.py:63`, `workspace_upload.py:113`, `workspace_service.py:97` Ã¢â‚¬â€ all `"ws-enterprise-retail"` |
| Chart fallback pattern | `chart_engine.py` Ã¢â‚¬â€ identical fallback repeated 5 times |
| Domain branching | `dashboard_generator.py`, `universal_engine.py`, `auto_insights.py`, `recommendation_engine.py` |

### 2.2 Retail-Only Assumptions
| Location | Assumption |
|----------|-----------|
| `dashboard_service.py` | `monthly_sales`, `store_sales` keys |
| `sales_repository.py` | Hardcoded `m5_train.parquet` path |
| `dashboard_generator.py` | Every non-retail domain has "Business Financial Metrics: Not Applicable" |
| `dynamic_kpis.py` | "Financial & Sales Metrics" default name |
| `chart_engine.py` | "Revenue & Growth Trend", "Top Sellers", "Freight Cost", "Payment Distribution" |
| `recommendation_engine.py` | "Product catalog pricing", "Market conditions" |
| `workspace_upload.py` | "Omnichannel Retail Analytics", "Total Revenue", "Net Margin %" |
| `workspace_service.py` | `ws-enterprise-retail` default ID |
| `upload.py` | Default preset = "retail" |
| `universal_engine.py` | Currency keyword list with "freight" |
| `auto_insights.py` | "Diversify marketing spend", "promotional ad campaigns", "14-day buffer inventory" |
| `ExecutiveTimeline.tsx` | **Entirely hardcoded Q1-Q4 2017 retail data** |
| `BenchmarkEngineCard.tsx` | **Entirely hardcoded $13.59M, $120.65 AOV, freight 16.6%** |
| `KPISection.tsx` | "Total Revenue", "Products", "Stores", "Data Coverage" |
| `DynamicKPISection.tsx` | `"olist_order_items_dataset"`, `"112,650"` rows, `"price"` column |
| `GuidedOnboardingModal.tsx` | "Retail Marketplace" default, 99441 rows, "$46,500 Revenue Delta" |
| `WorkspaceUploadWizard.tsx` | "Orders, Customers, Products, Reviews, and Payments", hardcoded Olist numbers |
| `WhatIfSimulator.tsx` | "freight shipping", "$1.42M", elasticity -0.42 |
| `AIAssistantChat.tsx` | "olist_order_items_dataset.parquet", "price, shipping_limit_date" |

### 2.3 Other Issues
- **3 separate parquet path resolvers** with different logic
- **Legacy endpoints** (`/kpis`, `/insights`, `/store-performance`, `/top-products`, `/categories`, `/monthly-trend`, `/sales-loss`, `/root-cause/{period}`, `/anomalies`) still exist alongside unified endpoints
- **`ExecutiveTimeline.tsx`** and **`BenchmarkEngineCard.tsx`** contain 100% fake/hardcoded data with no backend connection
- **`WorkspaceUploadWizard.tsx`** shows hardcoded Olist numbers regardless of uploaded data
- **Multiple fallback objects** for executive briefing in backend and frontend that can drift apart
- **`KPISection.tsx`** fetches from `/analytics/kpis` which may not exist in current backend
- **No single source of truth** for dashboard layout Ã¢â‚¬â€ layout is defined in both backend (`_analytics_result_to_dashboard_dict`) and frontend (`DynamicDashboardShell.tsx`)

---

## 3. Implementation Plan

### 3.1 Files to Modify

#### Backend
1. **`backend/app/services/dynamic_dashboard_service.py`** Ã¢â‚¬â€ Refactor to be a pure orchestrator that delegates to `UniversalAIBrain` and `UniversalAnalyticsEngine`. Remove `_fast_profile()`, `_fast_kpis()`, `_analytics_result_to_dashboard_dict()` Ã¢â‚¬â€ these are duplicated elsewhere. Keep only `_find_best_parquet()` (single canonical resolver).

2. **`backend/app/analytics/universal_engine.py`** Ã¢â‚¬â€ Already the canonical analytics engine. Remove retail assumptions from `_compute_kpis()` currency formatting. Make health score weights configurable via `SemanticModel`.

3. **`backend/app/analytics/chart_engine.py`** Ã¢â‚¬â€ Remove all hardcoded chart titles and retail-specific required columns. Make titles fully dynamic from data.

4. **`backend/app/analytics/recommendation_engine.py`** Ã¢â‚¬â€ Remove retail-specific assumptions ("Product catalog pricing", "Market conditions"). Make recommendations fully generic from `AnalyticsResult`.

5. **`backend/app/analytics/auto_insights.py`** Ã¢â‚¬â€ Remove retail-specific insight text ("Diversify marketing spend", "promotional ad campaigns", "14-day buffer inventory"). Make insights generic.

6. **`backend/app/analytics/dashboard_generator.py`** Ã¢â‚¬â€ Remove per-domain hardcoded KPI dictionaries. Replace with generic KPI generation from `SemanticModel` + `AnalyticsResult`.

7. **`backend/app/analytics/dynamic_kpis.py`** Ã¢â‚¬â€ Remove duplicate KPI computation. Delegate to `UniversalAnalyticsEngine._compute_kpis()`.

8. **`backend/app/analytics/health_engine.py`** Ã¢â‚¬â€ Keep as-is (no retail assumptions), but make weights configurable.

9. **`backend/app/reports/executive_report_engine.py`** Ã¢â‚¬â€ Remove retail-specific domain sections. Keep generic sections only. Remove hardcoded dollar values and percentages.

10. **`backend/app/ml/prediction_engine.py`** Ã¢â‚¬â€ Keep as-is (already domain-agnostic). Remove retail examples from error messages.

11. **`backend/app/services/dashboard_service.py`** Ã¢â‚¬â€ Remove entirely (legacy, hardcoded retail, uses `SalesRepository`).

12. **`backend/app/services/analytics_service.py`** Ã¢â‚¬â€ Remove entirely (legacy wrapper around `SemanticAnalyticsEngine` with hardcoded retail methods like `store_performance`, `top_products`, `category_performance`, `monthly_sales_trend`, `sales_loss_detection`).

13. **`backend/app/services/sales_service.py`** Ã¢â‚¬â€ Remove entirely (legacy, uses `SalesRepository`).

14. **`backend/app/repositories/sales_repository.py`** Ã¢â‚¬â€ Remove entirely (hardcoded M5 path).

15. **`backend/app/api/v1/dashboard.py`** Ã¢â‚¬â€ Remove legacy endpoints (`/overview`, `/sales-trend`, `/store-performance`). Keep only `/dynamic`.

16. **`backend/app/api/v1/executive.py`** Ã¢â‚¬â€ Remove entirely (legacy, retail-specific docstrings).

17. **`backend/app/api/v1/analytics.py`** Ã¢â‚¬â€ Remove legacy endpoints (`/kpis`, `/insights`, `/store-performance`, `/top-products`, `/categories`, `/monthly-trend`, `/sales-loss`, `/root-cause/{period}`, `/anomalies`, `/simulate`). Keep only `/universal` and `/strategic-decisions`.

18. **`backend/app/api/v1/upload.py`** Ã¢â‚¬â€ Remove hardcoded `ws-enterprise-retail` default. Remove hardcoded `"retail"` preset default.

19. **`backend/app/api/v1/workspace_upload.py`** Ã¢â‚¬â€ Remove hardcoded retail business profile. Make business profile dynamic from `SemanticModel`.

20. **`backend/app/services/workspace_service.py`** Ã¢â‚¬â€ Remove hardcoded `ws-enterprise-retail` default. Remove hardcoded retail business profile metadata.

21. **`backend/app/schemas/analytics.py`** Ã¢â‚¬â€ Keep as-is (pure data structures, no assumptions).

22. **`backend/app/ingestion/workspace_discovery.py`** Ã¢â‚¬â€ Keep as-is. Remove hardcoded `m5_`, `sample-` exclusions if they are Olist-specific.

#### Frontend
23. **`frontend/components/dashboard/KPISection.tsx`** Ã¢â‚¬â€ Remove entirely (legacy hardcoded retail KPIs, fetches from non-existent `/analytics/kpis`).

24. **`frontend/components/dashboard/ExecutiveTimeline.tsx`** Ã¢â‚¬â€ Remove entirely (100% hardcoded fake data).

25. **`frontend/components/dashboard/BenchmarkEngineCard.tsx`** Ã¢â‚¬â€ Remove entirely (100% hardcoded fake data).

26. **`frontend/components/dashboard/DynamicDashboardShell.tsx`** Ã¢â‚¬â€ Refactor to consume ONLY `UniversalAIBrain.query()` output. Remove hardcoded fallback briefing object. Remove duplicated `DynamicKPISection` rendering.

27. **`frontend/components/dashboard/DynamicKPISection.tsx`** Ã¢â‚¬â€ Remove hardcoded fallbacks (`"olist_order_items_dataset"`, `"112,650"`, `"price"`). Make all values dynamic from API response.

28. **`frontend/components/dashboard/ExecutiveActionCenter.tsx`** Ã¢â‚¬â€ Remove hardcoded `DollarSign` icon and "Prioritized by Financial Impact ($)" label.

29. **`frontend/components/dashboard/ExecutiveNewsfeed.tsx`** Ã¢â‚¬â€ Remove hardcoded retail fallback text.

30. **`frontend/components/dashboard/WhatIfSimulator.tsx`** Ã¢â‚¬â€ Remove hardcoded freight defaults, elasticity, ROAS, and retail logistics text.

31. **`frontend/components/dashboard/GuidedOnboardingModal.tsx`** Ã¢â‚¬â€ Remove hardcoded "Retail Marketplace" default, 99441 rows, "$46,500 Revenue Delta", Olist-specific descriptions.

32. **`frontend/components/dashboard/ExecutiveSearchModal.tsx`** Ã¢â‚¬â€ Remove hardcoded `$13.59M`, `$120.65`, `$2.25M`, retail table names.

33. **`frontend/components/dashboard/AIAssistantChat.tsx`** Ã¢â‚¬â€ Remove hardcoded Olist dataset/column fallbacks and retail preset prompts.

34. **`frontend/components/dashboard/StrategicDecisionsCard.tsx`** Ã¢â‚¬â€ Remove hardcoded evidence panel values.

35. **`frontend/components/dashboard/MultiAgentExecutiveView.tsx`** Ã¢â‚¬â€ Keep as-is (generic C-Suite view).

36. **`frontend/components/dashboard/InsightExplanationModal.tsx`** Ã¢â‚¬â€ Keep as-is (generic modal).

37. **`frontend/components/dashboard/ExecutiveStoryMode.tsx`** Ã¢â‚¬â€ Keep as-is (generic narrative).

38. **`frontend/components/charts/DynamicChartRenderer.tsx`** Ã¢â‚¬â€ Remove hardcoded Olist dataset in `how_calculated` fallback.

39. **`frontend/components/charts/ForecastChartRenderer.tsx`** Ã¢â‚¬â€ Remove hardcoded `"revenue"` fallback and hardcoded explanation text.

40. **`frontend/app/page.tsx`** Ã¢â‚¬â€ Remove hardcoded health score breakdown percentages.

41. **`frontend/app/dynamic-dashboard/page.tsx`** Ã¢â‚¬â€ Keep as-is (route wrapper).

42. **`frontend/app/copilot/page.tsx`** Ã¢â‚¬â€ Remove retail-specific preset prompts.

43. **`frontend/app/upload/page.tsx`** Ã¢â‚¬â€ Keep as-is (upload UI).

44. **`frontend/components/upload/WorkspaceUploadWizard.tsx`** Ã¢â‚¬â€ Remove hardcoded Olist numbers, retail table names, and "$46,500 Revenue Delta".

### 3.2 Files to Remove
| File | Reason |
|------|--------|
| `backend/app/services/dashboard_service.py` | Legacy retail dashboard |
| `backend/app/services/analytics_service.py` | Legacy retail analytics wrappers |
| `backend/app/services/sales_service.py` | Legacy sales service |
| `backend/app/repositories/sales_repository.py` | Hardcoded M5 path |
| `backend/app/api/v1/dashboard.py` | Legacy endpoints |
| `backend/app/api/v1/executive.py` | Legacy retail endpoint |
| `frontend/components/dashboard/KPISection.tsx` | Hardcoded retail KPIs |
| `frontend/components/dashboard/ExecutiveTimeline.tsx` | 100% fake data |
| `frontend/components/dashboard/BenchmarkEngineCard.tsx` | 100% fake data |

### 3.3 New Files to Create
| File | Purpose |
|------|---------|
| `backend/app/dashboard/schema.py` | Canonical `DashboardResponse` Pydantic schema |
| `backend/app/dashboard/storyteller.py` | `UniversalDashboardStoryteller` Ã¢â‚¬â€ transforms `AnalyticsResult` + `PredictionResult` + `ExecutiveReport` into `DashboardResponse` |
| `backend/app/dashboard/cards.py` | Card builders: `ExecutiveHeroCard`, `KPICard`, `HealthCard`, `TrendCard`, `RootCauseCard`, `PredictionCard`, `RiskCard`, `OpportunityCard`, `RecommendationCard`, `ScenarioCard`, `EvidenceCard` |
| `backend/app/dashboard/layout.py` | Layout engine: sections, ordering, responsive rules |
| `backend/app/dashboard/adapters.py` | Adapters: `AnalyticsResult Ã¢â€ â€™ DashboardSection`, `PredictionResult Ã¢â€ â€™ DashboardSection`, `ExecutiveReport Ã¢â€ â€™ DashboardSection` |
| `frontend/lib/dashboard-schema.ts` | TypeScript types for `DashboardResponse` |

### 3.4 Migration Strategy

#### Phase 1: Backend Canonical Dashboard Engine
1. Create `backend/app/dashboard/storyteller.py` Ã¢â‚¬â€ `UniversalDashboardStoryteller`
2. Create `backend/app/dashboard/cards.py` Ã¢â‚¬â€ all card builders
3. Create `backend/app/dashboard/layout.py` Ã¢â‚¬â€ section ordering
4. Create `backend/app/dashboard/adapters.py` Ã¢â‚¬â€ adapters from existing engines
5. Create `backend/app/dashboard/schema.py` Ã¢â‚¬â€ canonical schema
6. Refactor `dynamic_dashboard_service.py` to delegate to `UniversalDashboardStoryteller`
7. Remove retail assumptions from `chart_engine.py`, `recommendation_engine.py`, `auto_insights.py`, `dashboard_generator.py`, `dynamic_kpis.py`
8. Remove legacy files (`dashboard_service.py`, `analytics_service.py`, `sales_service.py`, `sales_repository.py`)
9. Clean up API endpoints

#### Phase 2: Frontend Universal Dashboard Shell
1. Refactor `DynamicDashboardShell.tsx` to consume `UniversalDashboardStoryteller` output
2. Remove hardcoded fallbacks from all frontend components
3. Remove `KPISection.tsx`, `ExecutiveTimeline.tsx`, `BenchmarkEngineCard.tsx`
4. Update all chart renderers to be data-driven
5. Update upload wizard and onboarding to be domain-agnostic

#### Phase 3: Validation
1. Run backend tests
2. Run frontend build
3. Run compile checks
4. Fix all errors
5. Generate migration report

### 3.5 Risk Analysis

| Risk | Severity | Mitigation |
|------|----------|------------|
| Breaking existing dashboard API contract | HIGH | Keep `/api/v1/dashboard/dynamic` response shape identical during transition |
| Frontend components depend on legacy fields | MEDIUM | Add compatibility layer in `DynamicDashboardShell.tsx` |
| Removing `SalesRepository` breaks other code | MEDIUM | Grep for all usages before removal |
| `UniversalDashboardStoryteller` becomes another monolith | LOW | Keep it as a thin orchestrator; delegate to existing engines |
| Performance regression from additional abstraction | LOW | Existing engines already cached; storyteller adds minimal overhead |

### 3.6 Testing Strategy

1. **Backend unit tests**: Test `UniversalDashboardStoryteller` with synthetic datasets for each domain (Retail, Cybersecurity, Healthcare, Finance, Education)
2. **API contract tests**: Verify `/api/v1/dashboard/dynamic` response shape is unchanged
3. **Frontend build**: `npm run build` must succeed
4. **Integration tests**: Upload a dataset Ã¢â€ â€™ verify dashboard renders without retail assumptions
5. **Regression tests**: Existing `test_universal_analyst.py`, `test_phase5_ai.py`, `test_answer_validation.py` must pass

### 3.7 Acceptance Criteria

- [ ] `UniversalDashboardStoryteller` is the single entry point for all dashboard generation
- [ ] No retail assumptions remain in backend dashboard code
- [ ] No retail assumptions remain in frontend dashboard code
- [ ] `ExecutiveTimeline.tsx` and `BenchmarkEngineCard.tsx` are removed
- [ ] Legacy `dashboard_service.py`, `analytics_service.py`, `sales_service.py`, `sales_repository.py` are removed
- [ ] Legacy API endpoints in `dashboard.py`, `executive.py`, `analytics.py` are removed
- [ ] `/api/v1/dashboard/dynamic` response shape is unchanged
- [ ] Dashboard renders correctly for ANY uploaded dataset without code changes
- [ ] All backend tests pass
- [ ] Frontend build succeeds
- [ ] No hardcoded KPI values, labels, colors, or icons remain
- [ ] No hardcoded retail table names (Orders, Customers, Products, Payments) remain
- [ ] No hardcoded Olist dataset references remain
- [ ] Default workspace ID is no longer `ws-enterprise-retail`
- [ ] Default upload preset is no longer `retail`
