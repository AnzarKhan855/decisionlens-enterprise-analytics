<div align="center">

# DecisionLens

### Enterprise Decision Intelligence & Analytics Platform

[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![DuckDB](https://img.shields.io/badge/DuckDB-Vectorized%20OLAP-FFF000.svg?logo=duckdb&logoColor=black)](https://duckdb.org/)
[![Next.js](https://img.shields.io/badge/Next.js-15%20App%20Router-000000.svg?logo=next.js&logoColor=white)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-19-61DAFB.svg?logo=react&logoColor=black)](https://react.dev/)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248.svg?logo=mongodb&logoColor=white)](https://www.mongodb.com/)
[![Test Suite](https://img.shields.io/badge/Tests-269%20Passed-brightgreen.svg)]()
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**An autonomous decision intelligence platform that transforms raw business datasets into executive KPIs, causal trends, multi-horizon forecasts, evidence-grounded recommendations, scenario simulations, and conversational AI insights.**

[**Live Web Application**](https://decisionlens-enterprise-analytics.vercel.app/) • [**Interactive API Docs**](https://decisionlens-enterprise-analytics.onrender.com/docs) • [**System Architecture**](docs/architecture/system_design.md) • [**Deployment Guide**](docs/deployment/deployment_guide.md)

</div>

---

## Product Preview

<div align="center">
  <img src="docs/images/dynamic_dashboard_desktop.png" alt="DecisionLens Executive Dynamic Dashboard" width="100%" style="border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 20px 40px rgba(0,0,0,0.4);" />
  <p><em>Figure 1: DecisionLens Executive Dynamic Dashboard — Real-time KPI synthesis, business health index (0–100), automated distribution analysis, and strategic decision cards evaluated over 21,930 retail time-series records ($32.19M observed revenue).</em></p>
</div>

---

## Table of Contents

- [Overview](#overview)
- [Core Decision Workflow](#core-decision-workflow)
- [Key Capabilities](#key-capabilities)
- [Visual Product Tour](#visual-product-tour)
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Workspace & Data Isolation](#workspace--data-isolation)
- [Production Verification & Performance](#production-verification--performance)
- [Local Development Setup](#local-development-setup)
- [Environment Variables](#environment-variables)
- [Deployment Architecture](#deployment-architecture)
- [Automated Testing](#automated-testing)
- [License & Maintainer](#license--maintainer)

---

## Overview

Modern organizations struggle with fragmented data distributed across operational databases, data lakes, spreadsheets, and flat files. The journey from raw tabular records to an executive decision typically demands weeks of manual ETL scripting, dashboard crafting, anomaly tracking, and slide preparation.

**DecisionLens** provides an end-to-end, autonomous decision intelligence pipeline:
1. **Zero-Setup Data Ingestion**: Upload single CSVs, Parquet tables, or multi-table ZIP archives with automatic relational schema discovery and character set normalization.
2. **Universal Analytics Engine**: In-process vectorized analytics answering the core executive questions:
   - **What happened?** (Dynamic KPIs, volume, utilization, growth & decline rates)
   - **Why did it happen?** (Variance decomposition, root cause attribution, statistical anomalies)
   - **What will happen?** (Multi-horizon time-series forecasting with 95% confidence bounds)
   - **What should we do?** (Evidence-backed strategic priorities, action levers, and estimated ROI)
3. **Grounded AI Copilot**: Multi-turn conversational analytics strictly grounded in the active workspace's data via DuckDB query traces, preventing fabricated figures.
4. **Polyglot Persistence**: Vectorized OLAP execution via DuckDB and Apache Parquet, paired with relational SQLite catalogs and MongoDB Atlas for business memory.

---

## Core Decision Workflow

```mermaid
flowchart TD
    A["Raw Business Data (CSV / Parquet / ZIP)"] --> B["Workspace Ingestion & Schema Profiling"]
    B --> C["Data Quality & Relational Architecture"]
    C --> D["Universal Analytics Engine"]
    D --> E["Dynamic Dashboard & Executive KPIs"]
    D --> F["Adaptive Time-Series Forecasting"]
    D --> G["Domain-Specialized Recommendations"]
    G --> H["Interactive Scenario Simulator"]
    H --> I["Executive Decision Center"]
    I --> J["Board Reports & Grounded AI Copilot"]
```

---

## Key Capabilities

| Capability | Technical Mechanism | Verified Business Value |
| :--- | :--- | :--- |
| **Workspace Management** | Isolated workspace environments with active context switching | Prevents inter-team data leakage; allows dynamic switching across business units. |
| **Asynchronous Ingestion** | Background worker queue returning `HTTP 202 Accepted` in < 1s | Eliminates 504 gateway timeouts on multi-table ZIPs; supports legacy Windows-1252 charsets. |
| **Dynamic Dashboard** | Dynamic KPI engine computing volume, revenue, profit, and margin | Instant executive overview with sparkline trends and category distributions. |
| **Universal Analytics Engine** | Vectorized DuckDB execution across statistical and ML modules | Answers *What*, *Why*, *Will*, and *Should* in a single analytical pass. |
| **Time-Series Forecasting** | Adaptive ARIMA, Exponential Smoothing, and Linear Trend detection | Generates forward projections with 95% confidence intervals and historical backtests. |
| **Domain Recommendations** | Prescriptive engine prioritizing initiatives by ROI impact | Recommends specific operational levers (pricing, discounts, inventory) with timeframes. |
| **Scenario Simulator** | Dynamic lever discovery with sensitivity elasticity modeling | Simulates what-if outcomes (e.g., +10% price increase) before committing capital. |
| **Decision Center** | Structured decision cards linked to verified DuckDB queries | Enables executive sign-off with clear financial upside and risk mitigation notes. |
| **Grounded AI Copilot** | Multi-turn conversational engine with numeric data validation | Natural language queries return structured answers with full SQL traceability. |
| **Data Explorer** | Schema discovery, column data profiling, and sample inspection | Inspects underlying table structures, data types, null counts, and relational links. |
| **Executive Reports** | Multi-section document generator with CSV and PDF export | Produces board-ready briefings covering drivers, risks, and forecasts in seconds. |
| **Security & RBAC** | JWT authentication, constant-time validation, and role enforcement | Protects endpoints via `SUPER_ADMIN`, `ORGANIZATION_ADMIN`, and `EMPLOYEE` roles. |

---

## Visual Product Tour

### 1. Executive Dashboard & Exploration

| Executive Dashboard | Schema Explorer |
| :---: | :---: |
| ![Dynamic Dashboard](docs/images/dynamic_dashboard_desktop.png) | ![Schema Explorer](docs/images/explorer_desktop.png) |
| *Real-time KPI metrics, composite health index, and category distributions.* | *Relational architecture, schema inspection, and sample record inspection.* |

### 2. Predictive & Decision Intelligence

| Time-Series Forecasting | Interactive Scenario Simulator |
| :---: | :---: |
| ![Adaptive Forecasting](docs/images/forecasts_desktop.png) | ![Scenario Simulator](docs/images/scenario_desktop.png) |
| *Multi-horizon projections with 95% confidence bounds.* | *Dynamic sensitivity levers modeling revenue and profit elasticity.* |

| Strategic Recommendations | Executive Decision Center |
| :---: | :---: |
| ![Strategy & Recommendations](docs/images/strategy_desktop.png) | ![Decision Center](docs/images/decisions_desktop.png) |
| *Prioritized business initiatives with estimated ROI.* | *Actionable decision cards ready for executive approval.* |

### 3. Grounded Conversational AI Copilot

| Executive KPI Synthesis | Root Cause Analysis |
| :---: | :---: |
| ![Copilot Executive KPI](docs/images/copilot_response_executive_kpis.png) | ![Copilot Root Cause](docs/images/copilot_response_root_cause.png) |
| *Natural-language query returning grounded revenue and volume totals.* | *Decomposes performance swings with DuckDB query traces.* |

| Strategic Recommendations | Out-of-Domain Guardrail Behavior |
| :---: | :---: |
| ![Copilot Recommendations](docs/images/copilot_response_recommendations.png) | ![Copilot Guardrails](docs/images/copilot_response_out_of_domain.png) |
| *Evidence-backed operational directives and follow-up prompts.* | *Grounded refusal and guidance when asked unsupported questions.* |

### 4. Governance, Operations & Architecture

| Multi-Table Upload Wizard | Executive Reports Engine |
| :---: | :---: |
| ![Upload Wizard](docs/images/upload_desktop.png) | ![Executive Reports](docs/images/reports_desktop.png) |
| *Asynchronous ZIP & CSV ingestion with live progress recovery.* | *Publication-ready board report generation with export options.* |

| Cybersecurity Posture | System Architecture View |
| :---: | :---: |
| ![Cybersecurity Posture](docs/images/cybersecurity_desktop.png) | ![System Architecture](docs/images/architecture_desktop.png) |
| *Cryptographic token validation, RBAC boundaries, and CORS checks.* | *Interactive architectural layer visualization and component map.* |

---

## System Architecture

```mermaid
flowchart TD
    subgraph Client["Presentation Layer (Vercel Edge / Next.js 15)"]
        UI["React 19 Interactive Views"]
        Store["Workspace Context & Auth State"]
        Routing["32 Static & Dynamic App Routes"]
    end

    subgraph Gateway["API & Security Layer (Render / FastAPI)"]
        CORS["CORS & Error Sanitization Middleware"]
        Auth["JWT Verification & RBAC Policy Guard"]
        Upload["Async Ingestion Router (HTTP 202 Accepted)"]
    end

    subgraph Engine["Analytics & Intelligence Core"]
        Universal["Universal Analytics Engine"]
        Forecaster["TimeSeriesForecaster (ARIMA / Trend)"]
        Simulator["Scenario Simulator & Elasticity Levers"]
        Brain["Universal AI Copilot Brain (Grounded RAG)"]
        Reporter["Executive Report Engine"]
    end

    subgraph Storage["Polyglot Persistence Layer"]
        DuckDB["DuckDB In-Memory (Vectorized SQL)"]
        Parquet["Parquet Columnar Storage (Workspace Scoped)"]
        MongoDB["MongoDB Atlas (Business Memory & Audit)"]
        SQLite["SQLite / WAL (Workspace Catalog)"]
    end

    Client -->|HTTPS / REST| Gateway
    Gateway --> Engine
    Engine --> Storage
```

---

## Technology Stack

| Domain | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend Framework** | Next.js 15 (App Router) | Server-side rendering, Edge routing, and static page generation |
| **UI Components** | React 19, Tailwind CSS, Lucide Icons | Responsive modern enterprise user interface |
| **State & Data Fetching** | SWR, Axios, HTML5 LocalStorage | Client-side caching, revalidation, and workspace synchronization |
| **Backend API** | FastAPI, Uvicorn, Pydantic v2 | High-throughput asynchronous REST gateway and schema validation |
| **Analytics Engine** | DuckDB (v1.0+), Pandas, NumPy | In-process vectorized OLAP execution and dataset profiling |
| **Predictive ML** | Statsmodels, Scikit-learn, SciPy | Time-series forecasting, trend decomposition, and anomaly detection |
| **Database & Memory** | MongoDB Atlas, SQLite (WAL mode) | Long-term business memory, report archives, and workspace catalogs |
| **Storage Format** | Apache Parquet (PyArrow) | Columnar data storage partitioned by workspace |
| **Security & Auth** | PyJWT, Passlib (bcrypt), Cryptography | Constant-time JWT validation, RBAC policy enforcement |
| **Testing & QA** | Pytest, Playwright (Chromium) | Automated regression test suites and end-to-end browser audits |

---

## Workspace & Data Isolation

DecisionLens is built from the ground up around strict **workspace-aware isolation**:
- **Directory & Storage Partitioning**: Ingested datasets are converted into Apache Parquet files scoped to unique workspace identifiers (`storage/parquet/{workspace_id}/`).
- **In-Memory Query Scoping**: DuckDB views are registered with workspace-specific prefixes, preventing multi-tenant query collision.
- **Zero Cross-Contamination**: Cross-workspace analytical probes confirm that data belonging to Workspace A is never returned or leaked into Workspace B queries or Copilot prompts.
- **Dynamic Context Switching**: Selecting an active workspace immediately invalidates frontend caches and repopulates all dashboards, forecasts, and conversational contexts.

---

## Production Verification & Performance

Empirical latency measurements recorded during live production verification against Render backend and Vercel frontend:

| Operation / Endpoint | Observed Metric | SLA Target | Status |
| :--- | :---: | :---: | :---: |
| **User Login** (`POST /auth/login`) | **398.5ms** | < 500ms | **PASS** |
| **Multi-Table ZIP Ingestion** (`POST /workspace/upload-zip`) | **395.0ms** (HTTP 202) | < 1000ms | **PASS** |
| **Universal Analytics** (`GET /analytics/universal`) | **391.4ms** | < 1000ms | **PASS** |
| **Schema Explorer** (`GET /workspaces/{id}/explorer`) | **573.0ms** | < 1000ms | **PASS** |
| **Adaptive Forecasting** (`GET /forecasts/detect`) | **300.5ms** | < 1000ms | **PASS** |
| **Decision Center** (`GET /analytics/decisions`) | **272.0ms** | < 1000ms | **PASS** |
| **Strategic Recommendations** (`GET /analytics/strategic-decisions`) | **460.0ms** | < 1000ms | **PASS** |
| **AI Copilot Query** (`POST /copilot/query`) | **P50: 1543.5ms** (P95: 2132.1ms) | < 3000ms | **PASS** |
| **Executive Reports Generation** (`GET /reports`) | **1859.8ms** | < 3000ms | **PASS** |
| **Frontend Route Reachability** (30 Production Pages) | **30 / 30 HTTP 200** (P50: 180.2ms) | < 500ms | **PASS** |

### Verified Test Suite
- **Backend Test Suites (`pytest`)**: **269 passed, 6 skipped, 0 failed**
- **Frontend Production Build**: **32 static & dynamic routes compiled cleanly** (0 TypeScript errors)

---

## Local Development Setup

### Prerequisites
- Python 3.12+
- Node.js 20 LTS
- npm or yarn

### 1. Clone Repository
```bash
git clone https://github.com/AnzarKhan855/decisionlens-enterprise-analytics.git
cd decisionlens-enterprise-analytics
```

### 2. Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # Configure environment variables
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Frontend Setup
```bash
cd ../frontend
npm install
cp .env.example .env.local  # Set NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
npm run dev
```

Visit `http://localhost:3000` in your browser.

---

## Environment Variables

### Backend (`backend/.env`)
| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `ENVIRONMENT` | Deployment environment | `production` / `development` |
| `SECRET_KEY` | Secret key for cryptographic signing | `<random_hex_string>` |
| `ALGORITHM` | JWT signing algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT token lifetime | `1440` (24 hours) |
| `MONGODB_URL` | MongoDB connection URI | `<your_mongodb_atlas_uri>` |
| `DATABASE_URL` | Relational SQLite catalog path | `sqlite:///./decisionlens.db` |
| `GROQ_API_KEY` | Optional LLM acceleration key | `<optional_groq_api_key>` |
| `ALLOWED_ORIGINS` | Permitted frontend origins for CORS | `https://decisionlens-enterprise-analytics.vercel.app` |

### Frontend (`frontend/.env.local`)
| Variable | Description | Example |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | Backend REST API base URL | `https://decisionlens-enterprise-analytics.onrender.com/api/v1` |

---

## Deployment Architecture

- **Frontend**: Hosted on **Vercel Edge Network** with automated continuous deployment from `main` branch.
- **Backend API**: Hosted on **Render Web Service** with auto-restart, health probe monitoring (`/api/v1/health`), and managed environment configuration.
- **Data Persistence**:
  - **DuckDB**: Vectorized in-process OLAP engine running directly alongside FastAPI.
  - **Apache Parquet**: Persistent file-based columnar storage for uploaded workspaces.
  - **MongoDB Atlas**: Managed cloud database storing executive reports, user settings, and immutable audit trails.

---

## Automated Testing

Execute the complete test suite locally:

```bash
# Backend unit & integration tests
cd backend
pytest tests/ -v

# AI evaluation framework tests
pytest app/evaluation/test_evaluation.py -v

# Frontend production build verification
cd ../frontend
npm run build
```

---

## License & Maintainer

Distributed under the **MIT License**. See [LICENSE](LICENSE) for details.

- **Author**: Anzar Khan
- **Repository**: [decisionlens-enterprise-analytics](https://github.com/AnzarKhan855/decisionlens-enterprise-analytics)
- **Deployment**: [Live Platform](https://decisionlens-enterprise-analytics.vercel.app/)
