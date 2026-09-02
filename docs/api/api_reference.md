# DecisionLens API Reference

## Base URL
- Production: `https://decisionlens-enterprise-analytics.onrender.com/api/v1`
- Local Development: `http://127.0.0.1:8000/api/v1`

## Authentication
All private endpoints require a Bearer token in the `Authorization` header:
```http
Authorization: Bearer <JWT_ACCESS_TOKEN>
```
Workspace-scoped endpoints accept the active workspace identifier via header or query parameter:
```http
X-Workspace-Id: <WORKSPACE_ID>
```

---

## Core Endpoints

### 1. Authentication (`/auth`)
- `POST /auth/register`: Create user account.
- `POST /auth/login`: Authenticate and receive JWT access/refresh tokens.
- `POST /auth/verify-otp`: Validate 2FA one-time passcode.
- `GET /auth/me`: Retrieve current authenticated user profile and roles.

### 2. Workspaces & Datasets (`/workspaces`, `/workspace`)
- `GET /workspaces`: List all workspaces accessible to user.
- `POST /workspace/upload-single`: Upload and profile individual CSV/Parquet file.
- `POST /workspace/upload-zip`: Ingest multi-table ZIP archive with automatic relational join discovery.
- `DELETE /workspace/{workspace_id}`: Securely delete workspace and purge associated columnar and cache records.

### 3. Universal Analytics (`/analytics`)
- `GET /analytics/universal`: Execute full 4-stage analytics engine and return canonical `AnalyticsResult`.
- `GET /analytics/scenario/levers`: Retrieve sensitivity levers for what-if simulations.
- `POST /analytics/scenario/simulate`: Execute Monte Carlo scenario simulation with custom lever adjustments.

### 4. Executive Reports (`/reports`)
- `GET /reports`: Retrieve structured executive board report for workspace.
- `GET /reports/export/csv`: Stream executive summary KPIs and driver data as CSV attachment.

### 5. Diagnostics & Governance (`/diagnostics`, `/audit`, `/cybersecurity`)
- `GET /diagnostics/status`: Platform uptime, process memory, and engine health.
- `GET /audit/logs`: Filterable enterprise audit trail of all platform activities.
- `GET /cybersecurity/dashboard`: RBAC-restricted security posture metrics.
