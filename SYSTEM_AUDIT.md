# SYSTEM_AUDIT.md

## DecisionLens Enterprise Decision Intelligence Platform Ã¢â‚¬â€ Complete System Audit

**Date:** 2026-08-02
**Auditor:** Kilo
**Scope:** Full-stack (Frontend Next.js + Backend FastAPI + DuckDB + AI/ML engines)

---

## EXECUTIVE SUMMARY

The platform has a sophisticated modular architecture with a unified analytics engine, semantic model, and AI copilot. However, several **critical** and **high-severity** issues prevent it from functioning correctly in production. The most severe issues are:

1. **Frontend/Backend schema mismatch** Ã¢â‚¬â€ Dashboard shell renders non-existent `intelligence` field, causing silent failures.
2. **Authentication security vulnerability** Ã¢â‚¬â€ Any unknown email/password auto-creates accounts on login.
3. **Workspace deletion crash** Ã¢â‚¬â€ AttributeError on `ACTIVE_WORKSPACE_FILE`.
4. **Cache invalidation gaps** Ã¢â‚¬â€ Dashboard and semantic caches not fully cleared on mutations.
5. **Information leakage** Ã¢â‚¬â€ Stack traces and exception messages returned to clients.

---

## 1. FRONTEND UI

### Issue F-01: Dashboard Shell References Non-Existent `intelligence` Field
- **Root Cause:** `DynamicDashboardShell.tsx` accesses `dashboard.intelligence.*` extensively (lines 273, 347, 367, 432, etc.), but `DashboardResponse` schema (`backend/app/dashboard/schema.py`) has no `intelligence` field. The backend `UniversalDashboardStoryteller.generate` does not populate it.
- **Files Involved:** `frontend/components/dashboard/DynamicDashboardShell.tsx`, `backend/app/dashboard/schema.py`, `backend/app/dashboard/storyteller.py`
- **Functions Involved:** `DynamicDashboardShell` render, `UniversalDashboardStoryteller.generate`
- **Dependency Chain:** Dashboard API Ã¢â€ â€™ Storyteller Ã¢â€ â€™ DashboardResponse Ã¢â€ â€™ Frontend shell Ã¢â€ â€™ silent empty sections
- **Severity:** CRITICAL
- **Estimated Effort:** 4 hours
- **Suggested Fix:** Add `intelligence: Dict[str, Any] = {}` to `DashboardResponse` schema and populate it in `UniversalDashboardStoryteller.generate` from `analytics_dict` (domain, entities, measures, dimensions, capability_matrix, detection_panel, business_questions).

### Issue F-02: Hardcoded Backend URLs in Frontend
- **Root Cause:** `DynamicDashboardShell.tsx` uses hardcoded `http://127.0.0.1:8000` for polling workspace status (lines 76, 81, 95). Breaks in production or when backend host changes.
- **Files Involved:** `frontend/components/dashboard/DynamicDashboardShell.tsx`
- **Functions Involved:** `loadDashboard` useEffect
- **Severity:** HIGH
- **Estimated Effort:** 1 hour
- **Suggested Fix:** Replace hardcoded URLs with `API_BASE_URL` from `lib/api.ts` or a frontend environment variable.

### Issue F-03: Frontend POST Requests Cached Improperly
- **Root Cause:** `lib/api.ts` `postCached` caches all POST responses. Upload endpoints (`/upload/`, `/upload/batch`) return cached responses on repeat calls, potentially serving stale success payloads without actual upload.
- **Files Involved:** `frontend/lib/api.ts`, `frontend/lib/upload.ts`
- **Functions Involved:** `postCached`, `uploadDataset`, `uploadMultipleDatasets`
- **Dependency Chain:** Upload Ã¢â€ â€™ POST cache Ã¢â€ â€™ stale response Ã¢â€ â€™ duplicate dataset or phantom success
- **Severity:** HIGH
- **Estimated Effort:** 1 hour
- **Suggested Fix:** Exclude mutation endpoints from caching. Add `noCache: true` flag or bypass cache for `/upload/*`, `/auth/*`, `/workspace/*`.

### Issue F-04: Frontend `getDynamicDashboard` Passes Workspace ID Ambiguously
- **Root Cause:** `lib/dynamic-dashboard.ts` passes `explicitWsId` as a query param `workspace_id`, but the backend `get_dynamic_dashboard` signature is `(dataset_id=None, workspace_id=None)`. The frontend function parameter name `explicitWsId` is misleading; it is actually treated as `workspace_id` via query params. Workspace switching may fail if the frontend localStorage ID is stale.
- **Files Involved:** `frontend/lib/dynamic-dashboard.ts`, `backend/app/services/dynamic_dashboard_service.py`
- **Functions Involved:** `getDynamicDashboard`, `get_dynamic_dashboard`
- **Severity:** MEDIUM
- **Estimated Effort:** 30 minutes
- **Suggested Fix:** Rename frontend parameter to `workspaceId` and ensure it maps to `workspace_id` query param explicitly.

### Issue F-05: Reports Page Hardcodes Generation Date
- **Root Cause:** `frontend/app/reports/page.tsx` line 242 uses `new Date().toISOString().split("T")[0]` for report generation date instead of the backend `generated_at` timestamp.
- **Files Involved:** `frontend/app/reports/page.tsx`
- **Severity:** LOW
- **Estimated Effort:** 10 minutes
- **Suggested Fix:** Use `report?.generated_at` from API response.

---

## 2. BACKEND API

### Issue B-01: Duplicate Copilot Route Registration
- **Root Cause:** `copilot_router` is included twice:
  1. Directly in `main.py` with prefix `/api/v1/ai/copilot`
  2. Via `routes.py` `api_router` with prefix `/api/v1/copilot`
  This creates duplicate endpoints `/api/v1/ai/copilot/query` and `/api/v1/copilot/query`.
- **Files Involved:** `backend/app/main.py`, `backend/app/api/v1/routes.py`
- **Severity:** MEDIUM
- **Estimated Effort:** 10 minutes
- **Suggested Fix:** Remove one inclusion. Keep either `/api/v1/ai/copilot` or `/api/v1/copilot`, not both.

### Issue B-02: Global Exception Handler Leaks Information
- **Root Cause:** `main.py` middleware returns `{"error": str(exc)}` for unhandled exceptions. `workspace_upload.py` returns `traceback.format_exc()[-3:]` in JSON responses. This exposes internal stack traces and error messages to clients.
- **Files Involved:** `backend/app/main.py`, `backend/app/api/v1/workspace_upload.py`
- **Severity:** HIGH
- **Estimated Effort:** 30 minutes
- **Suggested Fix:** Return generic error messages in production. Log full tracebacks server-side only.

### Issue B-03: Auth Allows Automatic User Creation on Login
- **Root Cause:** `auth.py` `_get_or_create_user` accepts `password_fallback` and creates a new SQLite user record for any email/password combination during login. Any unknown email with any password automatically registers and logs in.
- **Files Involved:** `backend/app/api/v1/auth.py`
- **Functions Involved:** `_get_or_create_user`, `login_user`
- **Dependency Chain:** Login Ã¢â€ â€™ auto-create user Ã¢â€ â€™ SQLite insert Ã¢â€ â€™ JWT issued for unauthorized account
- **Severity:** CRITICAL
- **Estimated Effort:** 2 hours
- **Suggested Fix:** Remove `password_fallback` auto-creation from login. Require explicit registration for new users.

### Issue B-04: OTP Required Only for SUPER_ADMIN
- **Root Cause:** `auth.py` enforces OTP verification exclusively for `SUPER_ADMIN`. `ORGANIZATION_ADMIN` and `EMPLOYEE` receive immediate JWTs. This creates inconsistent security posture.
- **Files Involved:** `backend/app/api/v1/auth.py`
- **Functions Involved:** `register_user`, `login_user`
- **Severity:** MEDIUM
- **Estimated Effort:** 2 hours
- **Suggested Fix:** Either enforce OTP for all roles or document the deliberate exception for internal users.

### Issue B-05: RedisCacheManager Calls Non-Existent Method
- **Root Cause:** `redis_cache.py` lines 102 and 116 call `cls._backend()` but only `_get_backend()` exists. This raises `AttributeError` when Redis backend is active.
- **Files Involved:** `backend/app/cache/redis_cache.py`
- **Functions Involved:** `delete`, `clear`
- **Severity:** HIGH
- **Estimated Effort:** 5 minutes
- **Suggested Fix:** Replace `cls._backend()` with `cls._get_backend()`.

---

## 3. WORKSPACE MANAGEMENT

### Issue W-01: Workspace Deletion Crashes on `ACTIVE_WORKSPACE_FILE`
- **Root Cause:** `workspace_service.py` line 486 calls `cls.ACTIVE_WORKSPACE_FILE.unlink(missing_ok=True)`, but `ACTIVE_WORKSPACE_FILE` is a module-level variable, not a class attribute. This raises `AttributeError` during deletion.
- **Files Involved:** `backend/app/services/workspace_service.py`
- **Functions Involved:** `delete_workspace`
- **Dependency Chain:** Delete request Ã¢â€ â€™ workspace removed from memory Ã¢â€ â€™ AttributeError Ã¢â€ â€™ 500 response Ã¢â€ â€™ workspace partially deleted
- **Severity:** CRITICAL
- **Estimated Effort:** 5 minutes
- **Suggested Fix:** Change to `ACTIVE_WORKSPACE_FILE.unlink(missing_ok=True)` (remove `cls.`).

### Issue W-02: Workspace Reconciliation Generates Random IDs
- **Root Cause:** `_reconcile_from_sqlite_and_storage` generates a new random workspace ID (`ws-{uuid.uuid4().hex[:8]}`) every time `workspaces.json` is empty. If the file is deleted or corrupted, a new phantom workspace is created on every restart, breaking references to old workspaces.
- **Files Involved:** `backend/app/services/workspace_service.py`
- **Functions Involved:** `_reconcile_from_sqlite_and_storage`
- **Severity:** HIGH
- **Estimated Effort:** 1 hour
- **Suggested Fix:** Derive workspace ID deterministically from dataset metadata or preserve the first dataset's ID.

### Issue W-03: Upload Reuses Active Workspace Without Isolation
- **Root Cause:** `upload.py` `process_single_file` reuses `EnterpriseWorkspaceManager.get_active_workspace_id()` if an active workspace exists. Multiple uploads are merged into the same workspace, mixing unrelated datasets.
- **Files Involved:** `backend/app/api/v1/upload.py`
- **Functions Involved:** `process_single_file`
- **Dependency Chain:** Upload 1 Ã¢â€ â€™ ws-abc created Ã¢â€ â€™ Upload 2 Ã¢â€ â€™ merged into ws-abc Ã¢â€ â€™ semantic model corrupted Ã¢â€ â€™ analytics empty
- **Severity:** HIGH
- **Estimated Effort:** 2 hours
- **Suggested Fix:** Always create a new workspace per upload, or prompt user to select existing workspace vs. new workspace.

### Issue W-04: Dashboard Service Mutates Global Active Workspace
- **Root Cause:** `get_dynamic_dashboard` calls `EnterpriseWorkspaceManager.set_active_workspace(target_ws_id)` on every request. In concurrent/multi-user scenarios, this causes race conditions where one user's dashboard request switches the active workspace for all users.
- **Files Involved:** `backend/app/services/dynamic_dashboard_service.py`
- **Functions Involved:** `get_dynamic_dashboard`
- **Severity:** HIGH
- **Estimated Effort:** 2 hours
- **Suggested Fix:** Remove `set_active_workspace` from `get_dynamic_dashboard`. Active workspace should only change on explicit user action (upload, activation endpoint).

### Issue W-05: Business Profile Returns Hardcoded Placeholders
- **Root Cause:** `get_business_profile` returns static strings like `"Active Items"`, `"Global Distribution"`, `"Enterprise Channels"` instead of deriving them from actual data.
- **Files Involved:** `backend/app/services/workspace_service.py`
- **Functions Involved:** `get_business_profile`
- **Severity:** MEDIUM
- **Estimated Effort:** 3 hours
- **Suggested Fix:** Compute `products_sold`, `countries`, `customers`, `sales_channels` from actual dimension distinct counts.

---

## 4. DATASET UPLOAD

### Issue U-01: ZIP Upload Returns Stack Traces to Client
- **Root Cause:** `workspace_upload.py` includes `traceback.format_exc()[-3:]` in error JSON responses. This exposes internal file paths and code structure.
- **Files Involved:** `backend/app/api/v1/workspace_upload.py`
- **Severity:** HIGH
- **Estimated Effort:** 30 minutes
- **Suggested Fix:** Remove traceback from response. Log server-side only.

### Issue U-02: Upload SHA256 Deduplication is In-Memory Only
- **Root Cause:** `upload.py` checks existing workspaces for SHA256 hash matches using `EnterpriseWorkspaceManager.get_all_workspaces()`. This loads from disk but the check is not atomic, and the hash is stored in `workspaces.json` which may not persist across restarts if not saved.
- **Files Involved:** `backend/app/api/v1/upload.py`, `backend/app/services/workspace_service.py`
- **Severity:** LOW
- **Estimated Effort:** 2 hours
- **Suggested Fix:** Persist SHA256 hashes to SQLite datasets table and query atomically.

---

## 5. SEMANTIC MODEL

### Issue S-01: Parquet File Matching is Too Loose
- **Root Cause:** `SemanticModelEngine._discover_parquet_files` and `_get_workspace_parquet_mtime` use `clean_target in clean_pname or clean_pname.startswith(clean_target)`. For workspace ID "abc", this matches "abc_xyz", "xyz_abc", and "abc", potentially including unrelated files.
- **Files Involved:** `backend/app/semantic_model/engine.py`
- **Functions Involved:** `_discover_parquet_files`, `_get_workspace_parquet_mtime`
- **Dependency Chain:** Wrong parquet files included Ã¢â€ â€™ semantic model polluted Ã¢â€ â€™ analytics incorrect Ã¢â€ â€™ dashboard misleading
- **Severity:** HIGH
- **Estimated Effort:** 1 hour
- **Suggested Fix:** Use strict prefix matching `clean_pname.startswith(clean_target + "__")` or exact workspace ID prefix.

### Issue S-02: Semantic Model Cache Invalidated Globally on Upload
- **Root Cause:** `upload.py` calls `invalidate_semantic_model_cache()` without a workspace ID, which clears the entire cache. In a multi-workspace environment, this evicts unrelated workspace models.
- **Files Involved:** `backend/app/api/v1/upload.py`, `backend/app/semantic_model/cache.py`
- **Severity:** MEDIUM
- **Estimated Effort:** 30 minutes
- **Suggested Fix:** Pass `workspace_id` to `invalidate_semantic_model_cache(workspace_id)` to invalidate only the affected workspace.

### Issue S-03: Column Classification Uses Hardcoded Keyword Lists
- **Root Cause:** `engine.py` `_classify_columns_detailed` uses extensive hardcoded keyword lists (e.g., `"price", "cost", "salary", "revenue"`) to infer semantic types. This creates false positives for domain-specific column names and violates the "industry-agnostic" principle.
- **Files Involved:** `backend/app/semantic_model/engine.py`
- **Severity:** MEDIUM
- **Estimated Effort:** 4 hours
- **Suggested Fix:** Move keyword lists to configurable profiles per domain, or rely on data type and statistical profiling instead of name matching.

---

## 6. ANALYTICS ENGINE

### Issue A-01: UniversalAnalyticsEngine Calls Health Engine Twice
- **Root Cause:** `universal_engine.py` lines 114-119 call `BusinessHealthEngine.calculate_health_score(profile, kpis)` twice (once per field access). This is wasteful.
- **Files Involved:** `backend/app/analytics/universal_engine.py`
- **Severity:** LOW
- **Estimated Effort:** 5 minutes
- **Suggested Fix:** Store result in a local variable.

### Issue A-02: AnalyticsResult Construction May Fail on Nested Objects
- **Root Cause:** `universal_engine.py` constructs `AnalyticsResult` with nested dataclass instances (e.g., `HealthScore`, `KPIMetric`). If any nested constructor raises, the entire result fails and falls back to empty. The error is silently swallowed.
- **Files Involved:** `backend/app/analytics/universal_engine.py`, `backend/app/schemas/analytics.py`
- **Severity:** MEDIUM
- **Estimated Effort:** 2 hours
- **Suggested Fix:** Add validation in `AnalyticsResult.__post_init__` or use Pydantic models with proper error handling.

### Issue A-03: Correlation Query Uses Raw String Interpolation
- **Root Cause:** `universal_engine.py` `_compute_correlations` builds SQL with f-strings: `f"SELECT CORR(\"{m1}\", \"{m2}\") ... FROM read_parquet('{path_str}')"`. Although column names are validated elsewhere, the parquet path is not parameterized.
- **Files Involved:** `backend/app/analytics/universal_engine.py`
- **Severity:** MEDIUM
- **Estimated Effort:** 1 hour
- **Suggested Fix:** Use DuckDB parameterized queries `?` for path and column names where possible, or ensure strict path validation.

---

## 7. DASHBOARD

### Issue D-01: Dashboard Cache Key Collision Risk
- **Root Cause:** `dynamic_dashboard_service.py` cache key is `f"{active_ws}_{parquet_path}"`. If `active_ws` is empty string or None, different parquet paths could collide. Also, cache is not invalidated when workspace is deleted.
- **Files Involved:** `backend/app/services/dynamic_dashboard_service.py`
- **Severity:** MEDIUM
- **Estimated Effort:** 1 hour
- **Suggested Fix:** Include `dataset_id` in cache key and invalidate on workspace deletion.

### Issue D-02: Dashboard Falls Back to Empty SemanticModel
- **Root Cause:** `dynamic_dashboard_service.py` line 231 creates `SemanticModel(workspace_id=active_ws, domain=domain, dataset_type="Unknown")` when `build_semantic_model` fails. This loses all table/measure metadata, resulting in empty KPIs.
- **Files Involved:** `backend/app/services/dynamic_dashboard_service.py`
- **Severity:** MEDIUM
- **Estimated Effort:** 1 hour
- **Suggested Fix:** Propagate the original exception or return a structured error instead of silently degrading.

---

## 8. COPILOT

### Issue C-01: Copilot Runs Full Analytics Pipeline Per Question
- **Root Cause:** `UniversalAIBrain.query` calls `_run_universal_analytics` and `_run_prediction` for every question, even simple summary queries. This makes copilot responses extremely slow (often >10s).
- **Files Involved:** `backend/app/ai/universal_copilot_brain.py`
- **Functions Involved:** `query`, `_run_universal_analytics`, `_run_prediction`
- **Severity:** HIGH
- **Estimated Effort:** 4 hours
- **Suggested Fix:** Cache analytics result per workspace with TTL. Only re-run if parquet mtime changes or cache is invalidated.

### Issue C-02: Copilot Evidence Query Returns Empty for Unhandled Intents
- **Root Cause:** `_execute_evidence_query` has no fallback branch for unrecognized intents. It returns empty SQL, empty tables, empty columns, and empty rows. The answer template still produces a 7-section response based on empty data.
- **Files Involved:** `backend/app/ai/universal_copilot_brain.py`
- **Functions Involved:** `_execute_evidence_query`
- **Severity:** MEDIUM
- **Estimated Effort:** 2 hours
- **Suggested Fix:** Add a default `summary` branch that runs `SELECT COUNT(*), SUM(measure), AVG(measure)` for the first available measure.

### Issue C-03: Copilot Conversation Memory is Not Persisted
- **Root Cause:** `ConversationMemory` is imported but its storage backend is unknown. If it's in-memory, conversation history is lost on server restart.
- **Files Involved:** `backend/app/ai/conversation_memory.py` (not fully audited)
- **Severity:** LOW
- **Estimated Effort:** 2 hours
- **Suggested Fix:** Persist conversation turns to SQLite or Redis.

---

## 9. REPORTS

### Issue R-01: Reports Fallback Masks Analytics Failures
- **Root Cause:** `reports_api.py` catches all exceptions and returns a fallback report with placeholder sections and `"status": "warning"`. The frontend displays this as a normal report, hiding the fact that analytics failed.
- **Files Involved:** `backend/app/api/v1/reports_api.py`, `frontend/app/reports/page.tsx`
- **Severity:** HIGH
- **Estimated Effort:** 1 hour
- **Suggested Fix:** Return HTTP 500 or a structured error object. Frontend should display an error state, not a placeholder report.

### Issue R-02: Report Sections Generated from Empty AnalyticsResult
- **Root Cause:** When `_get_report_data` receives an empty `analytics_result`, it constructs a minimal `SemanticModel` from dashboard dict. This produces a report with generic placeholders instead of real data.
- **Files Involved:** `backend/app/api/v1/reports_api.py`
- **Severity:** MEDIUM
- **Estimated Effort:** 1 hour
- **Suggested Fix:** Validate `analytics_result` has non-empty KPIs before generating report. Return error if dataset is missing.

### Issue R-03: Executive Report Has Hardcoded Domain Assumptions
- **Root Cause:** `executive_report_engine.py` `_build_domain_specific` contains hardcoded branches for `cybersecurity`, `healthcare`, `finance`, `retail`, `hr`, `manufacturing`. While these are labeled as "adaptive", they embed domain-specific vocabulary and assumptions that may not match the actual dataset.
- **Files Involved:** `backend/app/reports/executive_report_engine.py`
- **Severity:** MEDIUM
- **Estimated Effort:** 3 hours
- **Suggested Fix:** Replace hardcoded domain sections with template-driven generation based on actual detected entities and measures.

---

## 10. FORECASTING

### Issue F-01: Forecasting Triggers Expensive Full Analytics
- **Root Cause:** `forecasting_api.py` calls `UniversalAnalyticsEngine.analyze` before generating predictions. For a time-series forecast, this runs the entire analytics pipeline (KPIs, trends, root causes, anomalies, correlations, etc.) unnecessarily.
- **Files Involved:** `backend/app/api/v1/forecasting_api.py`
- **Functions Involved:** `get_time_series_forecast`, `get_customer_segmentation`
- **Severity:** HIGH
- **Estimated Effort:** 3 hours
- **Suggested Fix:** Create a lightweight `AnalyticsResultLite` with only `trends`, `measures`, `temporal`, `volume`, and `confidence_score` for prediction engine consumption.

### Issue F-02: Forecast Returns `prediction_interval` as Tuple
- **Root Cause:** `Prediction` dataclass has `prediction_interval: Optional[Tuple[float, float]]`. When serialized to JSON via `to_dict()`, tuples become lists. The frontend expects arrays but the schema doesn't document this.
- **Files Involved:** `backend/app/schemas/analytics.py`, `backend/app/api/v1/forecasting_api.py`
- **Severity:** LOW
- **Estimated Effort:** 30 minutes
- **Suggested Fix:** Document tuple-to-list serialization or convert to list explicitly in `to_dict()`.

---

## 11. AUTHENTICATION

### Issue AU-01: In-Memory OTP and Reset Token Stores
- **Root Cause:** `OTP_STORE` and `RESET_TOKEN_STORE` are Python dicts in memory. They are lost on server restart, invalidating pending OTPs and reset links.
- **Files Involved:** `backend/app/api/v1/auth.py`
- **Severity:** MEDIUM
- **Estimated Effort:** 2 hours
- **Suggested Fix:** Store OTPs and reset tokens in SQLite with expiry timestamps.

### Issue AU-02: Super Admin Password Hardcoded in MOCK_USERS_DB
- **Root Cause:** `auth.py` initializes `MOCK_USERS_DB` with hardcoded super admin credentials derived from `settings.SUPER_ADMIN_PASSWORD`. If the environment variable is missing, it falls back to a default that may be committed to version control.
- **Files Involved:** `backend/app/api/v1/auth.py`, `backend/app/core/config.py`
- **Severity:** MEDIUM
- **Estimated Effort:** 30 minutes
- **Suggested Fix:** Remove `MOCK_USERS_DB` in production. Require all users to exist in SQLite.

### Issue AU-03: JWT Secret Key Has Insecure Fallback
- **Root Cause:** `security.py` falls back to `"production-super-secret-jwt-key-decisionlens-2026"` if `SECRET_KEY` env var is missing. This is a well-known default that allows token forgery.
- **Files Involved:** `backend/app/core/security.py`
- **Severity:** CRITICAL
- **Estimated Effort:** 15 minutes
- **Suggested Fix:** Fail startup if `SECRET_KEY` is not set in production. Never use a fallback.

---

## 12. DATABASE

### Issue DB-01: DuckDB Connection is Global and Shared
- **Root Cause:** `DuckDBEngine` uses a single global connection (`_conn`) shared across all requests. DuckDB connections are not fully thread-safe for concurrent writes. Heavy analytics queries can block other requests.
- **Files Involved:** `backend/app/database/duckdb_engine.py`
- **Severity:** HIGH
- **Estimated Effort:** 4 hours
- **Suggested Fix:** Use a connection pool or create a new connection per query. DuckDB supports multiple read-only connections to the same database file.

### Issue DB-02: SQLite Session Not Scoped to Request
- **Root Cause:** Many endpoints create `SessionLocal()` in a `try/finally` block, but if an exception occurs during `db.close()`, the session leaks. Also, long-running analytics hold a session open.
- **Files Involved:** `backend/app/api/v1/upload.py`, `backend/app/api/v1/workspace_upload.py`, `backend/app/api/v1/forecasting_api.py`
- **Severity:** MEDIUM
- **Estimated Effort:** 2 hours
- **Suggested Fix:** Use FastAPI `Depends(get_db)` with proper session scoping.

---

## 13. PERFORMANCE

### Issue P-01: Dashboard Load Runs Full Analytics Synchronously
- **Root Cause:** `get_dynamic_dashboard` calls `UniversalAnalyticsEngine.analyze` synchronously. For large datasets, this blocks the request for 5-30 seconds.
- **Files Involved:** `backend/app/services/dynamic_dashboard_service.py`
- **Severity:** HIGH
- **Estimated Effort:** 6 hours
- **Suggested Fix:** Run analytics in background task and serve cached result. Frontend should poll or use WebSocket for completion.

### Issue P-02: Parquet Profiling is Repeated Unnecessarily
- **Root Cause:** `SemanticDataProfiler.profile` is called multiple times for the same parquet file within a single request (e.g., in `_find_best_parquet`, `_profile_table_score`, `_table_has_temporal`, `_table_has_measures`).
- **Files Involved:** `backend/app/services/dynamic_dashboard_service.py`
- **Severity:** MEDIUM
- **Estimated Effort:** 2 hours
- **Suggested Fix:** Cache profiling results in `SemanticDataProfiler` with file mtime key.

### Issue P-03: Frontend Polls Backend Every 2 Seconds
- **Root Cause:** `DynamicDashboardShell.tsx` polls `/workspaces` and `/workspace/{id}/status` every 2 seconds with hardcoded URLs.
- **Files Involved:** `frontend/components/dashboard/DynamicDashboardShell.tsx`
- **Severity:** MEDIUM
- **Estimated Effort:** 1 hour
- **Suggested Fix:** Use WebSocket or Server-Sent Events for background processing status. Increase poll interval to 10s.

---

## 14. CACHING

### Issue CA-01: Dashboard Cache Not Invalidated on Workspace Deletion
- **Root Cause:** `_dashboard_cache` (TTLCache) is never explicitly cleared when a workspace is deleted. Deleted workspace dashboards remain in cache until TTL expires (60s).
- **Files Involved:** `backend/app/services/dynamic_dashboard_service.py`, `backend/app/api/v1/workspace_upload.py`
- **Severity:** MEDIUM
- **Estimated Effort:** 30 minutes
- **Suggested Fix:** Clear `_dashboard_cache` entries for the deleted workspace ID in `delete_workspace`.

### Issue CA-02: Semantic Model Cache Key Doesn't Include Lineage Flag Consistently
- **Root Cause:** `SemanticModelCache._compute_cache_key` uses `workspace_id + include_lineage`. But `invalidate_semantic_model_cache` is sometimes called with `workspace_id=None` (global invalidation) and sometimes with a specific ID. The global invalidation clears all entries, which is correct but expensive.
- **Files Involved:** `backend/app/semantic_model/cache.py`
- **Severity:** LOW
- **Estimated Effort:** 1 hour
- **Suggested Fix:** Ensure all callers pass `workspace_id` for targeted invalidation. Use global invalidation only for testing.

---

## 15. AI REASONING

### Issue AI-01: Copilot Answers Are Template-Based, Not LLM-Based
- **Root Cause:** `UniversalAIBrain._build_executive_answer` uses hardcoded string templates for each intent. The "AI" does not reason; it interpolates values into pre-written paragraphs. This is not documented to users.
- **Files Involved:** `backend/app/ai/universal_copilot_brain.py`
- **Severity:** MEDIUM
- **Estimated Effort:** N/A (architectural decision)
- **Suggested Fix:** Document that answers are template-assembled from empirical data. If LLM reasoning is desired, integrate an LLM call with the evidence as context.

### Issue AI-02: Answer Validation is Superficial
- **Root Cause:** `AnswerValidationLayer.validate` checks that numeric claims match evidence rows, but the matching is string-equality based. It does not verify that the SQL query actually produced the evidence rows.
- **Files Involved:** `backend/app/ai/validation/answer_validator.py`
- **Severity:** MEDIUM
- **Estimated Effort:** 3 hours
- **Suggested Fix:** Include SQL execution hash or row checksum in validation request to ensure evidence integrity.

---

## 16. TESTING

### Issue T-01: No Integration Tests for Upload Ã¢â€ â€™ Dashboard Ã¢â€ â€™ Copilot Flow
- **Root Cause:** The test suite has unit tests for individual evaluators and phase tests, but no end-to-end test that uploads a dataset and verifies the dashboard renders non-empty KPIs.
- **Files Involved:** `backend/tests/`
- **Severity:** HIGH
- **Estimated Effort:** 6 hours
- **Suggested Fix:** Add integration test that uploads a CSV, waits for semantic model build, queries dashboard, and asserts KPIs are present.

### Issue T-02: Frontend Has No Tests
- **Root Cause:** No test files exist under `frontend/`. All UI components are untested.
- **Files Involved:** `frontend/`
- **Severity:** MEDIUM
- **Estimated Effort:** 8 hours
- **Suggested Fix:** Add React Testing Library tests for `DynamicDashboardShell`, `DynamicKPISection`, and `AIAssistantChat`.

---

## CASCADING FAILURE MAP

### Chain 1: Upload Ã¢â€ â€™ Workspace Ã¢â€ â€™ Semantic Model Ã¢â€ â€™ Dashboard Ã¢â€ â€™ Copilot Ã¢â€ â€™ Report
```
Upload bug (W-03: workspace reuse)
  Ã¢â€ â€œ
Semantic model built on mixed data (S-01: loose file matching)
  Ã¢â€ â€œ
UniversalAnalyticsEngine analyzes wrong/mixed tables (A-02)
  Ã¢â€ â€œ
Dashboard receives empty or incorrect AnalyticsResult (D-01)
  Ã¢â€ â€œ
Frontend renders empty KPIs or wrong data (F-01: missing intelligence field)
  Ã¢â€ â€œ
Copilot queries wrong parquet and produces fabricated answers (C-01)
  Ã¢â€ â€œ
Report generates from empty analytics with fallback placeholders (R-01)
```

### Chain 2: Auth Ã¢â€ â€™ Workspace Access Ã¢â€ â€™ Data Leakage
```
Auth auto-creates users (B-03)
  Ã¢â€ â€œ
Any user can login and access active workspace
  Ã¢â€ â€œ
No tenant isolation in workspace service (W-04: global active workspace mutation)
  Ã¢â€ â€œ
User A's request switches active workspace for User B
  Ã¢â€ â€œ
User B sees User A's data
```

### Chain 3: Cache Ã¢â€ â€™ Stale Data Ã¢â€ â€™ Wrong Decisions
```
Dashboard cache not invalidated on delete (CA-01)
  Ã¢â€ â€œ
Deleted workspace dashboard remains in cache
  Ã¢â€ â€œ
User switches to deleted workspace and sees stale KPIs
  Ã¢â€ â€œ
Copilot and report also serve stale cached analytics
  Ã¢â€ â€œ
Executive makes decisions on outdated data
```

### Chain 4: Forecast Ã¢â€ â€™ Performance Ã¢â€ â€™ Timeout
```
Forecast triggers full analytics (F-01)
  Ã¢â€ â€œ
Analytics takes 10-30s on large datasets (P-01)
  Ã¢â€ â€œ
HTTP request times out or user abandons
  Ã¢â€ â€œ
Frontend shows error despite data being available
  Ã¢â€ â€œ
User perceives platform as unreliable
```

---

## DUPLICATE FIX OPPORTUNITIES (HIGH IMPACT)

1. **Fix `dashboard.intelligence` field (F-01)** Ã¢â‚¬â€ Also fixes R-01 report sections, C-01 copilot context, and D-01 dashboard rendering. **Impact: 4 issues.**
2. **Fix auth auto-creation (B-03)** Ã¢â‚¬â€ Also fixes AU-02 hardcoded users and W-04 workspace isolation. **Impact: 3 issues.**
3. **Fix cache invalidation (CA-01, S-02)** Ã¢â‚¬â€ Also fixes D-01 dashboard staleness and F-01 copilot stale data. **Impact: 4 issues.**
4. **Fix frontend hardcoded URLs (F-02)** Ã¢â‚¬â€ Also fixes P-03 polling and F-03 upload cache. **Impact: 3 issues.**

---

## PRIORITIZED ROADMAP

### Priority 1 Ã¢â‚¬â€ Critical Blockers (Fix Immediately)
| ID | Issue | Module | Severity | Effort |
|---|---|---|---|---|
| B-03 | Auth auto-creates users on login | Authentication | CRITICAL | 2h |
| W-01 | Workspace deletion crashes on ACTIVE_WORKSPACE_FILE | Workspace | CRITICAL | 5m |
| AU-03 | JWT secret key has insecure fallback | Authentication | CRITICAL | 15m |
| F-01 | Dashboard shell references missing `intelligence` field | Frontend UI | CRITICAL | 4h |
| B-05 | RedisCacheManager calls non-existent `_backend()` | Caching | HIGH | 5m |

### Priority 2 Ã¢â‚¬â€ Incorrect Analytics or AI Reasoning
| ID | Issue | Module | Severity | Effort |
|---|---|---|---|---|
| S-01 | Semantic model parquet matching too loose | Semantic Model | HIGH | 1h |
| W-03 | Upload reuses active workspace | Workspace | HIGH | 2h |
| W-04 | Dashboard mutates global active workspace | Workspace | HIGH | 2h |
| C-01 | Copilot runs full analytics per question | Copilot | HIGH | 4h |
| F-01 | Forecast triggers expensive full analytics | Forecasting | HIGH | 3h |
| P-01 | Dashboard load blocks on synchronous analytics | Performance | HIGH | 6h |

### Priority 3 Ã¢â‚¬â€ Dashboard and Reports
| ID | Issue | Module | Severity | Effort |
|---|---|---|---|---|
| R-01 | Reports fallback masks analytics failures | Reports | HIGH | 1h |
| R-02 | Report sections generated from empty AnalyticsResult | Reports | MEDIUM | 1h |
| R-03 | Executive report has hardcoded domain assumptions | Reports | MEDIUM | 3h |
| D-01 | Dashboard cache key collision risk | Dashboard | MEDIUM | 1h |
| D-02 | Dashboard falls back to empty SemanticModel | Dashboard | MEDIUM | 1h |

### Priority 4 Ã¢â‚¬â€ Performance
| ID | Issue | Module | Severity | Effort |
|---|---|---|---|---|
| P-02 | Parquet profiling repeated unnecessarily | Performance | MEDIUM | 2h |
| P-03 | Frontend polls backend every 2 seconds | Performance | MEDIUM | 1h |
| DB-01 | DuckDB global connection shared across requests | Database | HIGH | 4h |
| DB-02 | SQLite session not scoped to request | Database | MEDIUM | 2h |

### Priority 5 Ã¢â‚¬â€ UX Polish
| ID | Issue | Module | Severity | Effort |
|---|---|---|---|---|
| F-02 | Frontend hardcoded URLs | Frontend UI | HIGH | 1h |
| F-03 | Frontend POST requests cached improperly | Frontend UI | HIGH | 1h |
| F-04 | getDynamicDashboard parameter naming | Frontend UI | MEDIUM | 30m |
| F-05 | Reports page hardcodes generation date | Frontend UI | LOW | 10m |
| S-03 | Column classification uses hardcoded keywords | Semantic Model | MEDIUM | 4h |
| AI-01 | Copilot answers are template-based | AI Reasoning | MEDIUM | N/A |
| T-01 | No integration tests for core flow | Testing | HIGH | 6h |
| T-02 | Frontend has no tests | Testing | MEDIUM | 8h |

---

## RECOMMENDED FIX ORDER

**Week 1:**
1. Fix B-03 (auth auto-creation) Ã¢â‚¬â€ 2h
2. Fix W-01 (workspace deletion crash) Ã¢â‚¬â€ 5m
3. Fix AU-03 (JWT fallback) Ã¢â‚¬â€ 15m
4. Fix B-05 (RedisCacheManager bug) Ã¢â‚¬â€ 5m
5. Fix F-01 (dashboard intelligence field) Ã¢â‚¬â€ 4h
6. Fix S-01 (parquet matching) Ã¢â‚¬â€ 1h

**Week 2:**
7. Fix W-03 (upload workspace reuse) Ã¢â‚¬â€ 2h
8. Fix W-04 (dashboard mutates global state) Ã¢â‚¬â€ 2h
9. Fix C-01 (copilot performance) Ã¢â‚¬â€ 4h
10. Fix F-01 forecast analytics Ã¢â‚¬â€ 3h
11. Fix R-01 (reports fallback masking) Ã¢â‚¬â€ 1h

**Week 3:**
12. Fix P-01 (dashboard async analytics) Ã¢â‚¬â€ 6h
13. Fix DB-01 (DuckDB connection pooling) Ã¢â‚¬â€ 4h
14. Fix F-02 (hardcoded URLs) Ã¢â‚¬â€ 1h
15. Fix F-03 (POST caching) Ã¢â‚¬â€ 1h
16. Fix CA-01 (dashboard cache invalidation) Ã¢â‚¬â€ 30m

**Week 4+:**
17. Fix R-03 (hardcoded domain sections)
18. Fix S-03 (keyword-based classification)
19. Fix T-01/T-02 (testing gaps)
20. Fix remaining LOW/MEDIUM issues

---

## END OF AUDIT

*This document was generated by Kilo automated system audit. No source code was modified.*
