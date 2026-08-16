# DecisionLens Implementation Plan Ã¢â‚¬â€ Phase 1: Repository Audit & Consolidation

---

## 1. Current Architecture

DecisionLens is a FastAPI + React + DuckDB stack with the following major subsystems:

| Subsystem | Location | Purpose |
|---|---|---|
| API Layer | `backend/app/api/v1/` | 30+ route modules exposing REST endpoints |
| Service Layer | `backend/app/services/` | Business logic orchestration |
| Analytics Engine | `backend/app/analytics/` | KPI computation, charting, insights, recommendations |
| Semantic Model | `backend/app/semantic_model/` | Domain/entity/metric/relationship detection |
| AI/Copilot | `backend/app/ai/` | Multi-agent analysis, copilot engine, universal analyst |
| Ingestion | `backend/app/ingestion/` | File upload, conversion, profiling, validation |
| Database | `backend/app/database/` | SQLAlchemy models, DuckDB engine, CRUD |
| ML/Prediction | `backend/app/ml/` | Forecasting, clustering, prediction |
| Reports | `backend/app/reports/` | PDF/Excel report generation (all empty) |
| Frontend | `frontend/app/` | Next.js 16.2 React dashboard |

---

## 2. Problems Identified

### 2.1 Duplicate Components (Critical)

| Duplicate Set | Files | Impact |
|---|---|---|
| KPI Generation | `analytic_sales.py::generate_kpis()`, `dynamic_kpis.py::DynamicKPIEngine`, `semantic_analytics.py::SemanticAnalyticsEngine.get_summary_kpis()`, `recommendation_engine.py::MetricDetector` | 4 different implementations of the same concept Ã¢â‚¬â€ KPI detection from dataset columns |
| Dashboard Loading | `dashboard_service.py::get_overview()`, `dynamic_dashboard_service.py::get_dynamic_dashboard()`, `sales_service.py::get_sales_trend()`, `executive_service.py::executive_dashboard()` | 4 dashboard loaders with overlapping data sources |
| Report Generation | `reports_api.py` (full implementation), `report_service.py` (empty), `pdf_report.py` (empty), `excel_report.py` (empty) | Report API exists but report service/layer is dead |
| Copilot Services | `copilot_engine.py::EnterpriseCopilotEngine`, `universal_analyst.py::UniversalAnalyst`, `analyst_agent.py::AIBusinessAnalystAgent`, `multi_agent_system.py::MultiAgentSystem`, `agents/` (8 agent modules) | 5+ AI analysis pipelines with significant overlap |
| Upload Flows | `upload.py` (full), `workspace_upload.py` (referenced), `loader.py::DataLoader`, `generic_loader.py::GenericDataLoader` | 2 upload APIs + 2 loader classes |
| Semantic Model | `semantic_model/` (15 files), `enterprise_semantic_model.py`, `unified_semantic_model.py`, `semantic_analytics.py` | 3 semantic model systems |
| Chart Builders | `chart_engine.py::ChartEngine`, `DynamicChartRenderer.tsx`, `ForecastChartRenderer.tsx`, `dashboard_generator.py` | 4 chart generation systems |
| Recommendation Engines | `recommendation.py::RecommendationEngine`, `recommendation_engine.py::RecommendationEngine`, `auto_insights.py::AutoInsights` | 3 recommendation engines |
| Dataset Detection | `dataset_detection.py::detect_dataset_type()`, `domain_detector.py::classify_domain()`, `dataset_detector.py` (referenced) | 3 dataset type/classification systems |

### 2.2 Duplicate APIs

| API Endpoint | Implementation Files |
|---|---|
| `/api/v1/analytics/kpis` | `analytics.py` (uses `analytic_sales.py`) |
| `/api/v1/dashboard/dynamic` | `dashboard.py` (delegates to `dynamic_dashboard_service.py`) |
| `/api/v1/analytics` | `analytics.py` (full analytics suite) |
| `/api/v1/reports` | `reports_api.py` (full report generation) |
| `/api/v1/copilot/query` | `copilot_api.py` (uses `copilot_engine.py`) |
| `/api/v1/ai/copilot/query` | Same copilot router, different prefix |
| `/api/v1/upload` | `upload.py` (single + batch + local-path + sample-presets) |
| `/api/v1/dashboard/overview` | `dashboard.py` (delegates to `dashboard_service.py`) |
| `/api/v1/dashboard/sales-trend` | `dashboard.py` (delegates to `sales_service.py`) |
| `/api/v1/dashboard/store-performance` | `dashboard.py` (delegates to `sales_service.py`) |

### 2.3 Duplicate Dashboard Loaders

| Loader | File | Data Source |
|---|---|---|
| `get_overview()` | `dashboard_service.py` | `SalesRepository.get_sales_data()` (M5 parquet) |
| `get_dynamic_dashboard()` | `dynamic_dashboard_service.py` | `_find_best_parquet()` (any workspace parquet) |
| `get_sales_trend()` | `sales_service.py` | `SalesRepository.get_sales_data()` |
| `get_store_performance()` | `sales_service.py` | `SalesRepository.get_sales_data()` |
| `executive_dashboard()` | `executive_service.py` | `SalesRepository.get_sales_data()` |

### 2.4 Duplicate Report Generators

| Generator | File | Status |
|---|---|---|
| `reports_api.py` | `backend/app/api/v1/reports_api.py` | Active Ã¢â‚¬â€ 349 lines, full implementation |
| `report_service.py` | `backend/app/services/report_service.py` | EMPTY Ã¢â‚¬â€ 0 lines |
| `pdf_report.py` | `backend/app/reports/pdf_report.py` | EMPTY Ã¢â‚¬â€ 0 lines |
| `excel_report.py` | `backend/app/reports/excel_report.py` | EMPTY Ã¢â‚¬â€ 0 lines |

### 2.5 Duplicate Copilot Services

| Service | File | Lines |
|---|---|---|
| `EnterpriseCopilotEngine` | `backend/app/ai/copilot_engine.py` | 890 |
| `UniversalAnalyst` | `backend/app/ai/universal_analyst.py` | 143 |
| `AIBusinessAnalystAgent` | `backend/app/ai/analyst_agent.py` | 337 |
| `MultiAgentSystem` | `backend/app/ai/multi_agent_system.py` | 128 |
| `SpecializedAIAgent` | `backend/app/ai/multi_agent_system.py` | 66 |
| 8 Agent Modules | `backend/app/ai/agents/` | ~200+ each |

### 2.6 Duplicate Upload Flows

| Flow | File |
|---|---|
| Single file upload | `backend/app/api/v1/upload.py` (`process_single_file()`) |
| Batch upload | `backend/app/api/v1/upload.py` (`upload_multiple_datasets()`) |
| Local path import | `backend/app/api/v1/upload.py` (`import_local_device_file()`) |
| Workspace upload | `backend/app/api/v1/workspace_upload.py` |
| Generic data loader | `backend/app/ingestion/generic_loader.py` (`GenericDataLoader`) |
| Data loader | `backend/app/ingestion/loader.py` (`DataLoader`) |

### 2.7 Unused Files (Dead Code)

| File | Status |
|---|---|
| `backend/app/services/report_service.py` | 0 lines Ã¢â‚¬â€ empty |
| `backend/app/services/forecasting_service.py` | 0 lines Ã¢â‚¬â€ empty |
| `backend/app/reports/pdf_report.py` | 0 lines Ã¢â‚¬â€ empty |
| `backend/app/reports/excel_report.py` | 0 lines Ã¢â‚¬â€ empty |
| `backend/app/analytics/forecasting_features.py` | 0 lines Ã¢â‚¬â€ empty |
| `backend/app/analytics/forecasting/data_split.py` | 0 lines Ã¢â‚¬â€ empty |
| `backend/app/analytics/forecasting/feature_engineering.py` | 0 lines Ã¢â‚¬â€ empty |
| `backend/app/analytics/trends.py` | Likely duplicate of `dashboard_analytics.py` |
| `backend/app/analytics/trend_metrics.py` | Likely duplicate of `dashboard_analytics.py` |
| `backend/app/analytics/statistics.py` | Not read, likely duplicate |
| `backend/app/analytics/products.py` | Likely duplicate of `product_metrics.py` |
| `backend/app/analytics/root_cause.py` | Used only by `analytics_service.py` |
| `backend/app/analytics/sales_loss.py` | Used only by `analytics_service.py` |
| `backend/app/analytics/store_metrics.py` | Used by `analytics_service.py` and `dashboard_service.py` |
| `backend/app/analytics/product_metrics.py` | Used by `analytics_service.py` |
| `backend/app/analytics/category_metrics.py` | Used by `analytics_service.py` |
| `backend/app/analytics/dashboard_analytics.py` | Used by `dashboard_service.py` and `sales_service.py` |

### 2.8 Stale Cache Logic

| Cache | File | Issue |
|---|---|---|
| `_dashboard_cache` | `dynamic_dashboard_service.py` | TTL 60s, no eviction policy, class-level mutable dict |
| `_CHART_CACHE` | `chart_engine.py` | No TTL, no eviction, class-level mutable dict |
| `_profile_cache_local` | `dynamic_dashboard_service.py` | Thread-safe but no TTL, no eviction |
| `_memory_cache` (TTLCache) | `cache/memory_cache.py` | Referenced but TTL behavior unclear |
| `_workspaces` | `workspace_service.py` | In-memory dict, no TTL, no eviction |
| `_jobs` | `task_queue.py` | In-memory dict, no TTL, no eviction |
| `_schedules` / `_history` | `refresh_scheduler.py` | In-memory dict, no TTL |
| `_versions` | `semantic_version_engine.py` | In-memory dict, no TTL |
| `_cache` (relationship) | `relationship_engine.py` | In-memory tuple, no TTL |
| `_parquet_path_cache` | `copilot_api.py` | TTL 120s, limited size |
| `_sales_data_cache` | `analytics.py` | TTL 30s, maxsize 4 |

### 2.9 Mock Data

| Location | Description |
|---|---|
| `sales_repository.py:32-46` | 100 rows of mock retail data (HOBBIES_1_001, CA_1) when M5 file missing |
| `strategy_engine.py:165-175` | Fallback baseline revenue=$1M, volume=50K when no data |
| `copilot_api.py:31-57` | Empty question fallback with hardcoded "Enter a question" response |
| `analytics.py:172-189` | Hardcoded strategic decision when no active dataset |
| `dynamic_dashboard_service.py:235-246` | Empty workspace fallback with hardcoded zero values |

### 2.10 Placeholder Values

| Location | Placeholder |
|---|---|
| `email_service.py:32` | `re_123456789_placeholder` API key |
| `config.py` | All paths point to M5 retail dataset |
| `workspace_service.py:97` | Default workspace ID `ws-enterprise-retail` |
| `upload.py:63` | Default workspace `ws-enterprise-retail` |
| `copilot_api.py:154` | Skips `m5_` prefixed parquet files |
| `semantic_model/engine.py:375` | Skips `m5_` prefixed parquet files |
| `strategy_engine.py` | Hardcoded elasticity=-1.25, margin=22% |

### 2.11 Hardcoded KPIs

| File | Hardcoded Values |
|---|---|
| `strategy_engine.py` | Revenue=$1M, volume=50K, margin=22%, elasticity=-1.25, specific dollar amounts ($320K, $450K, etc.) |
| `analytic_sales.py` | Confidence scores (95, 90, 85, 80, 50) hardcoded per metric type |
| `dynamic_dashboard_service.py` | Health score=98, confidence "95%", "98%", "97%" |
| `multi_agent_system.py` | Confidence "95%" for all agents |
| `copilot_engine.py` | Confidence 0.95 base, 0.92 for summary/top_n |
| `auto_insights.py` | Confidence 96%, 92%, 90%, 98%, 95% |
| `recommendation_engine.py` | Confidence 92%, 94% |
| `analytics.py` | Hardcoded strategic decision with "+$320,000 Revenue" |
| `chart_engine.py` | Chart titles reference "Revenue" and "Sales" |
| `email_service.py` | Hardcoded sender `admin@decisionlens.ai` |

### 2.12 Retail-Only Assumptions

| File | Retail Assumption |
|---|---|
| `config.py` | Paths hardcoded to `m5_train.parquet`, `m5_test.parquet`, `m5_sell_prices.csv`, `m5_xregs.csv` |
| `sales_repository.py` | M5 dataset schema (unique_id, ds, y, store, category), mock data is HOBBIES_1_001 / CA_1 |
| `analytic_sales.py` | Keywords: `item_id`, `store_id`, `store`, `category`, `sales` Ã¢â‚¬â€ all retail |
| `dashboard_analytics.py` | Functions `get_monthly_sales()`, `get_store_sales()` Ã¢â‚¬â€ retail only |
| `dashboard_service.py` | Uses `SalesRepository` directly |
| `sales_service.py` | Named "sales", uses retail-specific analytics |
| `analytics.py` | Endpoints: `store-performance`, `top-products`, `categories`, `sales-loss`, `root-cause` |
| `recommendation.py` | `_retail_recommendations()` with M5-specific advice |
| `semantic_model/detector.py` | `FACT_KEYWORDS` = order_items, orders, sales, transactions, payments, reviews |
| `semantic_model/entity_detector.py` | Entities: Customer, Product, Order, Employee, Store, Supplier, Shipment |
| `semantic_model/domain_detector.py` | `RETAIL_ECOMMERCE` has most keywords (16), first in dict |
| `workspace_service.py` | Default workspace = `ws-enterprise-retail` |
| `upload.py` | Default workspace = `ws-enterprise-retail` |
| `copilot_api.py` | Skips `m5_` prefixed files |
| `semantic_model/engine.py` | Skips `m5_` prefixed files |
| `strategy_engine.py` | Price elasticity=-1.25, base margin=22% Ã¢â‚¬â€ retail assumptions |
| `chart_engine.py` | Charts assume revenue/sales/category/store dimensions |
| `domain_detector.py` | Retail keywords dominate all other domains |
| `dataset_detection.py` | Categories: Revenue, Orders, Customers, Products Ã¢â‚¬â€ retail-centric |

### 2.13 Duplicate Semantic Model Logic

| System | Files | Overlap |
|---|---|---|
| Core semantic model | `semantic_model/` (15 files) | Full PK/FK/entity/domain/measure detection |
| Enterprise wrapper | `enterprise_semantic_model.py` | Delegates to `semantic_model/engine.py` |
| Unified builder | `unified_semantic_model.py` | Another semantic model builder |
| Semantic analytics | `semantic_analytics.py` | KPI computation using profiler |
| Semantic versioning | `semantic_version_engine.py` | Version control for models |
| Data catalog | `data_catalog_engine.py` | Domain inference (duplicates `domain_detector.py`) |
| Dataset detection | `dataset_detection.py` | Dataset type detection (duplicates `domain_detector.py`) |
| Dimensions/Calendar | `dimensions.py`, `calendar.py` | Feature engineering for M5 retail |

### 2.14 Duplicate Prediction Logic

| System | Files | Status |
|---|---|---|
| ML pipeline | `ml/train.py`, `ml/predict.py`, `ml/evaluate.py`, `ml/models/forecast_model.py`, `ml/training/trainer.py`, `ml/inference/predictor.py` | Full ML pipeline |
| Forecasting service | `services/forecasting_service.py` | EMPTY (0 lines) |
| Forecasting features | `analytics/forecasting_features.py` | EMPTY (0 lines) |
| Forecasting modules | `analytics/forecasting/data_split.py`, `analytics/forecasting/feature_engineering.py` | EMPTY (0 lines) |
| Dynamic dashboard ML | `dynamic_dashboard_service.py` (lines 360-382) | Uses `TimeSeriesForecaster`, `SegmentationEngine`, `UniversalPredictionEngine` |

---

## 3. Root Causes

1. **Incremental Feature Addition**: Features were added iteratively without refactoring existing code, leading to parallel implementations of the same concept.
2. **No Shared Abstraction Layer**: KPI generation, dashboard loading, and report generation each have independent implementations with no shared interface.
3. **Domain-Specific Hardcoding**: The M5 retail dataset was the first and primary test dataset, and retail assumptions leaked into core abstractions (config paths, repository defaults, keyword lists, entity types).
4. **Empty Placeholder Files**: Report generation, forecasting service, and forecasting features were scaffolded but never implemented, leaving empty files that create confusion about what is "real."
5. **No Deduplication Discipline**: Multiple teams or iterations created similar utilities (semantic model, dataset detection, recommendation engine) without checking for existing implementations.
6. **Stale Cache Without Governance**: Multiple in-memory caches with no TTL, no eviction policy, and no invalidation strategy were added as quick fixes.
7. **Mock Data as Fallback**: The sales repository falls back to mock retail data when the M5 file is missing, reinforcing the retail-only assumption.

---

## 4. Files to Modify

| File | Action | Reason |
|---|---|---|
| `backend/app/config.py` | Replace M5-specific paths with generic dataset config | Remove retail-only hardcoding |
| `backend/app/repositories/sales_repository.py` | Generalize repository, remove retail mock data fallback | Remove retail-only assumptions |
| `backend/app/ingestion/loader.py` | Remove M5-specific column renames (unique_idÃ¢â€ â€™item_id, dsÃ¢â€ â€™date, yÃ¢â€ â€™sales) | Make loader truly generic |
| `backend/app/analytics/analytic_sales.py` | Rename to `generic_kpis.py`, generalize keywords, remove retail-specific logic | Universal KPI generation |
| `backend/app/analytics/dashboard_analytics.py` | Rename to `generic_analytics.py`, generalize function names | Universal analytics |
| `backend/app/analytics/chart_engine.py` | Generalize chart titles and dimension detection | Remove retail bias in chart labels |
| `backend/app/analytics/recommendation.py` | Remove `_retail_recommendations()`, generalize all domain methods | Universal recommendations |
| `backend/app/analytics/recommendation_engine.py` | Generalize `MetricDetector` keywords beyond retail | Universal metric detection |
| `backend/app/semantic_model/domain_detector.py` | Balance domain keywords, remove retail dominance | Universal domain detection |
| `backend/app/semantic_model/entity_detector.py` | Add generic entity types beyond retail | Universal entity detection |
| `backend/app/semantic_model/detector.py` | Generalize fact/dimension keywords beyond retail patterns | Universal table classification |
| `backend/app/services/dynamic_dashboard_service.py` | Remove hardcoded health scores, confidence values, and retail-specific executive briefings | Universal dashboard |
| `backend/app/services/strategy_engine.py` | Remove hardcoded baseline values, make elasticity/margin configurable | Universal strategy engine |
| `backend/app/services/workspace_service.py` | Remove `ws-enterprise-retail` default, make workspace ID generic | Universal workspace |
| `backend/app/api/v1/upload.py` | Remove `ws-enterprise-retail` default workspace | Universal upload |
| `backend/app/api/v1/copilot_api.py` | Remove `m5_` file skip logic | Universal copilot |
| `backend/app/semantic_model/engine.py` | Remove `m5_` file skip logic | Universal semantic model |
| `backend/app/api/v1/analytics.py` | Generalize endpoint names and responses | Universal analytics API |
| `backend/app/api/v1/dashboard.py` | Generalize dashboard endpoint names | Universal dashboard API |
| `backend/app/services/email_service.py` | Remove hardcoded sender domain, make configurable | Universal email service |
| `backend/app/ai/copilot_engine.py` | Remove retail-specific JOIN_PATTERNS and domain-specific follow-up questions | Universal copilot |
| `backend/app/ai/analyst_agent.py` | Remove domain-specific branches (Cybersecurity, Education, Healthcare) and make generic | Universal analyst |
| `backend/app/ai/multi_agent_system.py` | Remove retail-biased DOMAIN_AGENTS, make agent construction data-driven | Universal multi-agent |
| `backend/app/analytics/auto_insights.py` | Remove retail-specific insight language | Universal insights |
| `backend/app/analytics/semantic_analytics.py` | Generalize KPI computation | Universal semantic analytics |
| `backend/app/analytics/health_engine.py` | Generalize health score components beyond retail | Universal health scoring |

---

## 5. Files to Merge

| Merge Target | Source Files | Action |
|---|---|---|
| `backend/app/analytics/generic_kpis.py` (new) | `analytic_sales.py`, `dynamic_kpis.py::DynamicKPIEngine`, `semantic_analytics.py::SemanticAnalyticsEngine` | Consolidate KPI generation into single universal engine |
| `backend/app/analytics/generic_analytics.py` (new) | `dashboard_analytics.py`, `trends.py`, `trend_metrics.py`, `statistics.py` | Consolidate time-series and trend analytics |
| `backend/app/analytics/generic_chart_engine.py` (new) | `chart_engine.py`, `dashboard_generator.py` | Consolidate chart generation |
| `backend/app/ai/unified_analyst.py` (new) | `copilot_engine.py`, `universal_analyst.py`, `analyst_agent.py` | Consolidate AI analysis into single pipeline |
| `backend/app/ai/unified_agents.py` (new) | `multi_agent_system.py`, `agents/` (8 modules) | Consolidate agent system |
| `backend/app/analytics/generic_recommendation.py` (new) | `recommendation.py`, `recommendation_engine.py::RecommendationEngine`, `auto_insights.py::AutoInsights` | Consolidate recommendation engine |
| `backend/app/analytics/generic_semantic.py` (new) | `semantic_model/engine.py`, `enterprise_semantic_model.py`, `unified_semantic_model.py` | Consolidate semantic model building |
| `backend/app/ingestion/unified_loader.py` (new) | `loader.py::DataLoader`, `generic_loader.py::GenericDataLoader` | Consolidate data loading |
| `backend/app/services/unified_dashboard.py` (new) | `dashboard_service.py`, `dynamic_dashboard_service.py`, `sales_service.py`, `executive_service.py` | Consolidate dashboard loading |
| `backend/app/services/unified_report.py` (new) | `reports_api.py`, `report_service.py` (empty), `pdf_report.py` (empty), `excel_report.py` (empty) | Consolidate report generation |
| `backend/app/analytics/generic_dataset_detection.py` (new) | `dataset_detection.py`, `domain_detector.py`, `dataset_detector.py` | Consolidate dataset type detection |

---

## 6. Files to Remove

| File | Reason |
|---|---|
| `backend/app/services/report_service.py` | Empty (0 lines), report logic lives in `reports_api.py` |
| `backend/app/services/forecasting_service.py` | Empty (0 lines), ML logic lives in `ml/` |
| `backend/app/reports/pdf_report.py` | Empty (0 lines), no PDF implementation exists |
| `backend/app/reports/excel_report.py` | Empty (0 lines), no Excel implementation exists |
| `backend/app/analytics/forecasting_features.py` | Empty (0 lines) |
| `backend/app/analytics/forecasting/data_split.py` | Empty (0 lines) |
| `backend/app/analytics/forecasting/feature_engineering.py` | Empty (0 lines) |
| `backend/app/analytics/trends.py` | Duplicate of `dashboard_analytics.py::get_monthly_sales_trend()` |
| `backend/app/analytics/trend_metrics.py` | Duplicate of `dashboard_analytics.py` |
| `backend/app/analytics/products.py` | Duplicate of `product_metrics.py` |
| `backend/app/analytics/statistics.py` | Likely duplicate of existing analytics |
| `backend/app/analytics/dashboard_analytics.py` | After merge into `generic_analytics.py` |
| `backend/app/analytics/analytic_sales.py` | After merge into `generic_kpis.py` |
| `backend/app/analytics/recommendation.py` | After merge into `generic_recommendation.py` |
| `backend/app/analytics/recommendation_engine.py` | After merge into `generic_recommendation.py` |
| `backend/app/analytics/auto_insights.py` | After merge into `generic_recommendation.py` |
| `backend/app/analytics/semantic_analytics.py` | After merge into `generic_kpis.py` |
| `backend/app/analytics/dataset_detection.py` | After merge into `generic_dataset_detection.py` |
| `backend/app/analytics/enterprise_semantic_model.py` | After merge into `generic_semantic.py` |
| `backend/app/analytics/unified_semantic_model.py` | After merge into `generic_semantic.py` |
| `backend/app/analytics/semantic_version_engine.py` | After merge into `generic_semantic.py` |
| `backend/app/analytics/data_catalog_engine.py` | After merge into `generic_semantic.py` |
| `backend/app/analytics/data_lineage_engine.py` | After merge into `generic_semantic.py` |
| `backend/app/analytics/data_quality_engine.py` | After merge into unified data quality |
| `backend/app/analytics/system_telemetry_engine.py` | After merge into unified telemetry |
| `backend/app/analytics/collaboration_engine.py` | After merge into unified collaboration |
| `backend/app/analytics/variance_engine.py` | After merge into generic analytics |
| `backend/app/analytics/anomaly_engine.py` | After merge into generic analytics |
| `backend/app/analytics/health_engine.py` | After merge into generic analytics |
| `backend/app/analytics/dimensions.py` | After merge into generic analytics |
| `backend/app/analytics/calendar.py` | After merge into generic analytics |
| `backend/app/analytics/store_metrics.py` | After merge into `generic_analytics.py` |
| `backend/app/analytics/product_metrics.py` | After merge into `generic_analytics.py` |
| `backend/app/analytics/category_metrics.py` | After merge into `generic_analytics.py` |
| `backend/app/analytics/root_cause.py` | After merge into `generic_analytics.py` |
| `backend/app/analytics/sales_loss.py` | After merge into `generic_analytics.py` |
| `backend/app/analytics/analysis_readiness.py` | After merge into generic analytics |
| `backend/app/analytics/forecasting/` (directory) | All files empty or duplicate |

---

## 7. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Breaking existing API contracts during merge | High | Maintain backward-compatible aliases during transition; version API routes |
| Data loss from removing duplicate files | Medium | Git history preserves all code; remove only after merge is verified |
| Regression in retail domain functionality | High | Keep retail as one supported domain; do not remove retail-specific logic, generalize it |
| Cache invalidation bugs during consolidation | Medium | Implement unified cache with TTL + LRU eviction; test thoroughly |
| Mock data removal breaks local dev | Medium | Replace mock data with configurable sample datasets for any domain |
| Hardcoded KPI removal breaks dashboards | High | Make all KPI values computed from actual data; add configuration for defaults |
| Empty file removal confuses developers | Low | Document removal in changelog; use git for history |
| Frontend-backend contract changes | High | Update frontend API client simultaneously with backend changes |
| Semantic model accuracy degradation | High | Validate unified semantic model against all 7 benchmark datasets |
| Performance regression from consolidation | Medium | Benchmark before/after; ensure unified engine is not slower than individual implementations |

---

## 8. Migration Strategy

### Phase 1: Foundation (Weeks 1-2)
1. Create `generic_kpis.py` by consolidating `analytic_sales.py`, `dynamic_kpis.py`, `semantic_analytics.py`
2. Create `generic_analytics.py` by consolidating `dashboard_analytics.py`, `trends.py`, `trend_metrics.py`
3. Create `generic_chart_engine.py` by consolidating `chart_engine.py`, `dashboard_generator.py`
4. Create `generic_dataset_detection.py` by consolidating `dataset_detection.py`, `domain_detector.py`
5. Update `analytics.py` router to use new generic modules
6. Update `dashboard.py` router to use new generic modules
7. Run existing tests to verify no regressions

### Phase 2: AI Consolidation (Weeks 3-4)
1. Create `unified_analyst.py` by consolidating `copilot_engine.py`, `universal_analyst.py`, `analyst_agent.py`
2. Create `unified_agents.py` by consolidating `multi_agent_system.py`, `agents/` modules
3. Create `generic_recommendation.py` by consolidating `recommendation.py`, `recommendation_engine.py`, `auto_insights.py`
4. Update `copilot_api.py` to use unified analyst
5. Update `reports_api.py` to use unified recommendation engine
6. Run existing tests to verify no regressions

### Phase 3: Semantic Model Consolidation (Weeks 5-6)
1. Create `generic_semantic.py` by consolidating `semantic_model/engine.py`, `enterprise_semantic_model.py`, `unified_semantic_model.py`
2. Update `semantic_model_api.py` to use new unified semantic model
3. Update `workspace_service.py` to use new unified semantic model
4. Update `dynamic_dashboard_service.py` to use new unified semantic model
5. Run existing tests to verify no regressions

### Phase 4: Service Layer Consolidation (Weeks 7-8)
1. Create `unified_dashboard.py` by consolidating `dashboard_service.py`, `dynamic_dashboard_service.py`, `sales_service.py`, `executive_service.py`
2. Create `unified_report.py` by consolidating `reports_api.py` logic
3. Create `unified_loader.py` by consolidating `loader.py`, `generic_loader.py`
4. Update all API routers to use new unified services
5. Remove old service files after verification
6. Run existing tests to verify no regressions

### Phase 5: Cleanup (Weeks 9-10)
1. Remove all empty placeholder files (report_service.py, forecasting_service.py, pdf_report.py, excel_report.py, forecasting_features.py, etc.)
2. Remove all duplicate analytics files after merge verification
3. Remove all stale cache implementations; replace with unified cache
4. Remove all mock data fallbacks; replace with configurable sample data
5. Remove all hardcoded KPI values; make them data-driven
6. Remove all retail-only assumptions from core modules
7. Update `config.py` with generic dataset paths
8. Run full test suite
9. Update documentation (README.md, ROADMAP.md, AGENTS.md)

---

## 9. Testing Strategy

### 9.1 Unit Tests
- Test each new consolidated module in isolation
- Verify KPI generation produces same results for retail M5 dataset
- Verify KPI generation works for non-retail datasets (Finance, Healthcare, HR, Marketing, Education, Operations)
- Test domain detection accuracy across all 7 benchmark datasets
- Test entity detection precision/recall/F1 across all domains
- Test semantic model building for each domain

### 9.2 Integration Tests
- Test full upload Ã¢â€ â€™ semantic model Ã¢â€ â€™ dashboard Ã¢â€ â€™ report pipeline for each domain
- Test copilot query answering for each domain
- Test multi-agent analysis for each domain
- Test chart generation for each domain

### 9.3 Regression Tests
- Run existing test suite before and after each phase
- Compare API response shapes before/after consolidation
- Verify no breaking changes in existing endpoints
- Verify performance benchmarks are maintained or improved

### 9.4 Benchmark Tests
- Run evaluation framework (`python -m app.evaluation.runner`) for all 7 benchmark datasets
- Compare scores before/after consolidation
- Ensure no degradation in Business Understanding, SQL Accuracy, or Recommendation Quality

### 9.5 Test Files
- `backend/tests/test_universal_analyst.py` Ã¢â‚¬â€ Already exists, update to test generic pipeline
- `backend/tests/test_phase1_ingestion.py` Ã¢â‚¬â€ Already exists, update for generic loader
- `backend/tests/test_phase2_analytics.py` Ã¢â‚¬â€ Already exists, update for generic analytics
- `backend/tests/test_phase3_insights.py` Ã¢â‚¬â€ Already exists, update for generic insights
- `backend/tests/test_phase4_ml.py` Ã¢â‚¬â€ Already exists, update for generic ML
- `backend/tests/test_phase5_ai.py` Ã¢â‚¬â€ Already exists, update for generic AI
- `backend/tests/test_phase6_security.py` Ã¢â‚¬â€ Already exists, update for generic security
- `backend/tests/test_universal_analyst.py` Ã¢â‚¬â€ Already exists, update for unified analyst

---

## 10. Rollback Strategy

1. **Git Branching**: All consolidation work happens on feature branches. Main branch is never broken.
2. **Feature Flags**: New consolidated modules are gated behind feature flags. Old modules remain active as fallback.
3. **API Versioning**: New endpoints use `/api/v2/` prefix. Old `/api/v1/` endpoints remain functional during transition.
4. **Database Migrations**: No schema changes required for consolidation. If any are needed, use Alembic migrations.
5. **Cache Migration**: Old caches remain readable. New cache is populated alongside old cache. Old cache is deprecated after 2 release cycles.
6. **Rollback Procedure**:
   - Revert feature branch merge
   - Disable feature flags
   - Restart services
   - Verify old endpoints work
   - Investigate and fix issues on feature branch
7. **Monitoring**: Track error rates, latency, and KPI accuracy during rollout. Auto-rollback if error rate exceeds 1%.

---

## 11. Expected Output

After Phase 1 consolidation:

| Metric | Before | After |
|---|---|---|
| Duplicate KPI implementations | 4 | 1 |
| Duplicate dashboard loaders | 4 | 1 |
| Duplicate report generators | 4 (1 active + 3 empty) | 1 |
| Duplicate copilot services | 5+ | 1 |
| Duplicate upload flows | 4 | 1 |
| Duplicate semantic model systems | 3 | 1 |
| Duplicate chart builders | 4 | 1 |
| Duplicate recommendation engines | 3 | 1 |
| Duplicate dataset detection systems | 3 | 1 |
| Empty placeholder files | 8 | 0 |
| Hardcoded retail assumptions | 20+ | 0 (retail is one supported domain) |
| Hardcoded KPI values | 15+ | 0 (all data-driven) |
| Stale cache implementations | 10+ | 1 unified cache |
| Mock data fallbacks | 5+ | 0 (configurable sample data) |
| Total Python files in `app/analytics/` | ~35 | ~10 (consolidated) |
| Total Python files in `app/ai/` | ~20 | ~5 (consolidated) |
| Total Python files in `app/services/` | ~15 | ~8 (consolidated) |
| API endpoints | 30+ | 30+ (same count, cleaner implementation) |

---

## 12. Estimated Effort

| Phase | Duration | Effort (person-weeks) |
|---|---|---|
| Phase 1: Foundation | 2 weeks | 3-4 |
| Phase 2: AI Consolidation | 2 weeks | 3-4 |
| Phase 3: Semantic Model Consolidation | 2 weeks | 3-4 |
| Phase 4: Service Layer Consolidation | 2 weeks | 3-4 |
| Phase 5: Cleanup | 2 weeks | 2-3 |
| **Total** | **10 weeks** | **14-19 person-weeks** |

### Team Composition
- 1 Lead Staff Software Engineer (this role) Ã¢â‚¬â€ architecture, coordination, review
- 2 Backend Engineers Ã¢â‚¬â€ implementation, testing
- 1 AI/ML Engineer Ã¢â‚¬â€ semantic model, copilot, agent consolidation
- 1 QA Engineer Ã¢â‚¬â€ regression testing, benchmark validation

### Dependencies
- None between phases (each phase builds on the previous)
- Frontend team must update API client contracts simultaneously with backend changes
- Evaluation framework must be run after each phase to verify no degradation

---

*This plan covers Phase 1 (Repository Audit & Consolidation). Phase 2 (Universal Dataset Support) will address making the platform truly domain-agnostic, supporting any structured dataset beyond the current 7 benchmark domains.*
