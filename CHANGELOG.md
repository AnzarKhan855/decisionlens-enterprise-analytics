# Changelog

All notable changes to DecisionLens will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] - 2026-09-03

### Added
- **Universal Analytics Engine**: Orchestrates KPIs, root causes, time-series forecasting, and strategic recommendations in a unified canonical payload.
- **Enterprise Security Hardening**: Constant-time digest verification, strict RBAC dependencies on all 18 private endpoints, HSTS/CSP security headers.
- **Next.js Edge Middleware**: Server-side session interception, protected route enforcement, deep-link preservation (`?redirect=...`).
- **Production Notification Center**: Stateful alert hub in Header replacing developer placeholders.
- **Three.js WebGL Spatial Architecture**: Dynamic code-split 3D layer visualization with 2D/3D mode toggling.
- **Performance Engineering**: FastAPI GZip compression (70-90% payload reduction), DuckDB multi-core thread scaling and metadata caching, Axios transparent in-flight request deduplication.
- **WCAG 2.1 AA Compliance**: Global single H1 landmark eradication, accessible Listbox keyboard navigation, 5.44:1 avatar contrast.

### Fixed
- Fixed critical `list[0]` and hardcoded workspace assumptions across all analytics routers.
- Fixed `Starlette` ASGI rate limit exception handling with structured JSON responses.
- Fixed cross-platform `/tmp` upload file validator failure on Windows environments.
- Eliminated 7 orphaned routes by restructuring navigation into 3 clear enterprise sections.

---

## [1.0.0] - 2026-07-01

### Added
- Initial release of DecisionLens Decision Intelligence Platform.
- Automated data ingestion, DuckDB vectorized OLAP engine, and exploratory analysis.
- Multi-domain benchmark generation across Retail, Healthcare, Finance, and Operations.
- LLM-assisted Copilot chat for conversational analytical inquiries.
