# Polyglot Database Architecture & Schema

DecisionLens utilizes a hybrid polyglot persistence architecture designed for analytical throughput and relational integrity:

```
+-------------------------------------------------------------------------+
|                              DecisionLens                               |
+-------------------+--------------------+--------------------------------+
| DuckDB + Parquet  | SQLite Catalog     | MongoDB Atlas                  |
| (OLAP Columnar)   | (Relational State) | (Business Memory & Telemetry)  |
+-------------------+--------------------+--------------------------------+
| - Raw transactions| - Workspaces       | - Canonical Analytics Cache    |
| - Vectorized SQL  | - Users & Roles    | - Audit Logs                   |
| - Fast aggregations- Ingestion runs    | - Copilot Conversation History |
| - Columnar files  | - Dataset pointers | - Scenario Simulations         |
+-------------------+--------------------+--------------------------------+
```

## 1. Apache Parquet & DuckDB
- **Storage Location**: `storage/parquet/{workspace_id}/`
- **Engine**: In-process vectorized DuckDB OLAP engine.
- **Capabilities**: Zero-copy querying of columnar data, sub-millisecond aggregations on multi-million row datasets.

## 2. SQLite Workspace Relational Catalog (`decisionlens.db`)
- **Tables**:
  - `workspaces`: `id`, `name`, `owner_id`, `created_at`, `status`.
  - `datasets`: `id`, `workspace_id`, `filename`, `file_path`, `row_count`, `column_count`.
  - `users`: `id`, `email`, `hashed_password`, `role`, `is_active`.

## 3. MongoDB Collections
- `analytics_cache`: Cached `AnalyticsResult` payloads indexed by `workspace_id`.
- `audit_logs`: Audit events with compound indexes on `(workspace_id, action, timestamp)`.
- `copilot_history`: Multi-turn conversational memory indexed by `(session_id, timestamp)`.
- `scenario_simulations`: Preserved what-if simulation runs.
