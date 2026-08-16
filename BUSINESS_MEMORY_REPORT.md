# DecisionLens Business Memory Engine
## Architecture & Implementation Report

**Generated:** 2026-08-05
**Version:** 2.0
**Status:** Production Ready

---

## 1. Executive Summary

DecisionLens now includes a **Business Memory Engine** that provides long-term persistent memory for every workspace. All AI responses are grounded not just in the current dataset, but in the full history of conversations, reports, insights, forecasts, recommendations, business goals, and executive decisions.

### Key Capabilities
- **11 Persistent Memory Domains** stored in MongoDB
- **Context-Aware AI Responses** using previous conversations, reports, KPIs, goals, and decisions
- **Role-Based Professional Reports** for CEO, CFO, COO, CMO, and Board Members
- **Unified Analytics** - all roles receive the SAME underlying data with different business focus
- **Full Traceability** - every AI answer can reference historical context

---

## 2. Memory Architecture

### 2.1 MongoDB Collections

The Business Memory Engine uses **11 dedicated MongoDB collections** in the `decisionlens` database:

| Collection | Purpose | Key Fields |
|------------|---------|------------|
| `conversation_history` | All user/AI conversation turns | session_id, workspace_id, role, content, timestamp |
| `report_history` | Generated reports | workspace_id, report_type, audience, title, content |
| `insight_history` | AI-generated insights | workspace_id, insight_type, severity, description |
| `forecast_history` | Time-series predictions | workspace_id, model_type, metric, predictions, confidence |
| `recommendation_history` | Evidence-based recommendations | workspace_id, title, priority, status, outcome |
| `business_goals` | Strategic objectives | workspace_id, title, target_metric, target_value, current_value, deadline |
| `executive_decisions` | Approved decisions | workspace_id, title, decision_maker, rationale, expected_impact |
| `forecast_accuracy` | Prediction vs actual tracking | workspace_id, forecast_id, predicted_value, actual_value, error_pct |
| `kpi_history` | KPI snapshots over time | workspace_id, dataset_id, kpis, timestamp |
| `user_feedback` | User ratings and comments | workspace_id, session_id, rating, comment, category |
| `business_milestones` | Key business events | workspace_id, title, milestone_type, date, metrics |

### 2.2 Memory Schema Design

Each collection follows a consistent schema:
- `workspace_id`: Primary tenant identifier
- `timestamp`: ISO-8601 creation timestamp
- `ts`: Unix epoch for efficient sorting
- Domain-specific fields

---

## 3. Business Memory Engine

### 3.1 Core Class: `BusinessMemoryEngine`

Location: `backend/app/memory/business_memory_engine.py`

The engine provides a clean API for all memory operations:

```python
from app.memory.business_memory_engine import BusinessMemoryEngine

# Save conversation
BusinessMemoryEngine.save_conversation(session_id, workspace_id, "user", "What is our revenue?")

# Get context for AI
context = BusinessMemoryEngine.get_ai_context(workspace_id, session_id)

# Build context prompt
prompt = BusinessMemoryEngine.build_context_prompt(workspace_id, session_id)
```

### 3.2 Context Retrieval for AI

Every AI response now receives a `business_memory_context` field containing:

1. **Current Dataset**: Active workspace and dataset info
2. **Previous Conversations**: Last 10 conversation turns
3. **Previous Reports**: Last 5 generated reports
4. **Previous Insights**: Last 10 AI-generated insights
5. **Previous Forecasts**: Last 5 forecast records
6. **Previous Recommendations**: Last 10 recommendations with status
7. **Business Goals**: Active goals with progress
8. **Previous Decisions**: Last 10 executive decisions
9. **Previous KPIs**: Last 5 KPI snapshots
10. **Business Milestones**: Last 5 milestones

The `build_context_prompt()` method formats this into a readable prompt block that can be injected into AI reasoning.

---

## 4. Role-Based Report Engine

### 4.1 Core Class: `RoleBasedReportEngine`

Location: `backend/app/reports/role_based_report_engine.py`

Generates **professional, non-dashboard reports** for 5 executive audiences using the SAME underlying `AnalyticsResult`.

### 4.2 Available Audiences

| Audience | Report Title | Business Focus |
|----------|--------------|----------------|
| **CEO** | CEO Strategic Briefing | Strategic growth, market position, long-term health, forward look |
| **CFO** | CFO Financial Review | Financial KPIs, forecast accuracy, ROI analysis, budget risks |
| **COO** | COO Operations Review | Operational anomalies, process health, efficiency drivers, capacity |
| **CMO** | CMO Marketing & Growth Review | Customer segments, growth opportunities, market trends, campaigns |
| **BOARD** | Board Governance Report | Comprehensive governance, risk register, key findings, decisions |

### 4.3 Report Sections by Role

#### CEO Report Sections
- `executive_snapshot`: High-level health and status
- `strategic_kpis`: Top 5 KPIs with strategic importance ratings
- `market_position`: Growth/decline periods, trend direction, key drivers
- `growth_trajectory`: Detailed growth and decline analysis
- `key_drivers`: Top business drivers
- `forward_look`: Predictive models and confidence
- `strategic_recommendations`: HIGH/CRITICAL priority actions
- `opportunities`: Top opportunities
- `strategic_risks`: HIGH/CRITICAL risks
- `board_highlights`: Key highlights for board presentation

#### CFO Report Sections
- `executive_snapshot`: High-level financial status
- `financial_kpis`: Revenue, profit, margin, cost-related KPIs
- `revenue_trends`: Trend analysis with financial focus
- `forecast_accuracy`: Historical prediction accuracy summary
- `cashflow_outlook`: Predictive cashflow insights
- `roi_analysis`: Recommendations with ROI breakdown
- `budget_risks`: Financial-specific risk items
- `cost_drivers`: Root cause cost analysis
- `investment_recommendations`: HIGH/CRITICAL financial recommendations
- `financial_opportunities`: Revenue and savings opportunities

#### COO Report Sections
- `executive_snapshot`: Operational health status
- `operational_anomalies`: All detected anomalies with severity
- `process_health`: Anomaly counts, outliers, data completeness
- `efficiency_drivers`: Concentration risks and driver contributions
- `operational_recommendations`: Action items with owners and timelines
- `capacity_utilization`: Row counts, performance metrics
- `volume_metrics`: Dataset scale and performance
- `operational_risks`: Operational risk register
- `resource_allocation`: Dimension impact analysis

#### CMO Report Sections
- `executive_snapshot`: Marketing health status
- `marketing_kpis`: Customer, conversion, engagement metrics
- `customer_segments`: Top segments by distribution and comparison
- `growth_opportunities`: Identified growth opportunities
- `trend_insights`: Direction and magnitude of key metrics
- `campaign_recommendations`: Marketing-specific recommendations
- `market_trends`: Growth/decline patterns and detected patterns
- `segment_comparisons`: Head-to-head segment comparisons
- `distribution_analysis`: Category concentration metrics

#### Board Report Sections
- `executive_snapshot`: Comprehensive executive summary
- `governance_kpis`: All KPIs with confidence scores
- `business_health`: Health score, grade, status, breakdown
- `strategic_trends`: Full trend analysis
- `key_drivers`: Top 5 business drivers
- `predictive_outlook`: All predictions with confidence
- `strategic_recommendations`: Top 5 recommendations
- `risk_register`: Complete risk register with mitigation
- `opportunity_portfolio`: All opportunities
- `key_findings`: Critical, positive, and negative findings
- `critical_decisions`: Recent executive decisions
- `forecast_confidence`: Historical forecast accuracy

---

## 5. AI Integration

### 5.1 Memory Context Injection

The `UniversalAIBrain.query()` method now automatically:

1. **Saves every conversation turn** to MongoDB `conversation_history`
2. **Saves KPI snapshots** after each analysis to `kpi_history`
3. **Saves recommendations** to `recommendation_history`
4. **Saves forecasts** to `forecast_history`
5. **Saves executive reports** to `report_history`
6. **Injects `business_memory_context`** into every AI response

### 5.2 Context Prompt Format

The injected prompt follows this structure:

```
BUSINESS MEMORY CONTEXT

RECENT CONVERSATIONS:
- [user] What is our revenue?
- [assistant] Revenue is $1.2M...

RECENT REPORTS:
- [CEO] CEO Strategic Briefing - Retail (2026-08-05)
- [CFO] CFO Financial Review - Retail (2026-08-04)

RECENT INSIGHTS:
- [HIGH] Revenue spike in Q4...
- [MEDIUM] Customer concentration risk...

RECENT FORECASTS:
- [Time Series] revenue: confidence=0.92
- [Regression] profit: confidence=0.85

RECENT RECOMMENDATIONS:
- [pending] Expand premium product line...
- [approved] Reduce freight costs...

ACTIVE BUSINESS GOALS:
- Increase Q4 Revenue: target=2000000, current=1850000
- Improve Customer Retention: target=85%, current=78%

PREVIOUS EXECUTIVE DECISIONS:
- [approved] Expand to APAC market by CEO
- [pending] Implement new ERP system

PREVIOUS KPI SNAPSHOTS:
- 2026-08-05: Revenue, Profit, Customers
- 2026-08-04: Revenue, Profit

BUSINESS MILESTONES:
- Q3 Product Launch (2026-08-01): Successfully launched 3 new products
- ISO Certification (2026-07-15): Achieved ISO 27001 compliance

END OF BUSINESS MEMORY CONTEXT
```

### 5.3 AI Response Enhancement

Every copilot response now includes:

```json
{
  "answer": "...",
  "business_memory_context": "...",
  "confidence": 0.95,
  "intent": "trend",
  "domain": "Retail",
  "support": {
    "tables_used": [...],
    "sql_used": "...",
    "analytics": {...},
    "executive_report": {...}
  }
}
```

---

## 6. API Endpoints

### 6.1 Memory Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/memory/goals` | Create business goal |
| GET | `/api/v1/memory/goals/{workspace_id}` | List business goals |
| POST | `/api/v1/memory/decisions` | Create executive decision |
| GET | `/api/v1/memory/decisions/{workspace_id}` | List executive decisions |
| POST | `/api/v1/memory/milestones` | Create business milestone |
| GET | `/api/v1/memory/milestones/{workspace_id}` | List milestones |
| POST | `/api/v1/memory/feedback` | Submit user feedback |
| GET | `/api/v1/memory/feedback/{workspace_id}` | List feedback |
| POST | `/api/v1/memory/forecast-accuracy` | Record forecast accuracy |
| GET | `/api/v1/memory/forecast-accuracy/{workspace_id}` | List accuracy records |
| GET | `/api/v1/memory/context/{workspace_id}/{session_id}` | Get AI context |

### 6.2 Report Generation

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/reports/generate` | Generate role-based report |
| GET | `/api/v1/reports/{workspace_id}` | List recent reports |
| GET | `/api/v1/reports/available-audiences` | List available audiences |

### 6.3 Report Request Format

```json
{
  "workspace_id": "ws-abc123",
  "audience": "CEO",
  "session_id": "session-001",
  "format": "json"
}
```

### 6.4 Report Response Format

```json
{
  "generated_at": "2026-08-05T14:30:00+00:00",
  "audience": "CEO",
  "domain": "Retail",
  "dataset_type": "Sales Transactions",
  "health_score": 85,
  "health_status": "Healthy",
  "report_title": "CEO Strategic Briefing - Retail",
  "sections": {
    "executive_snapshot": {...},
    "strategic_kpis": [...],
    "market_position": {...},
    "growth_trajectory": {...},
    "key_drivers": [...],
    "forward_look": [...],
    "strategic_recommendations": [...],
    "opportunities": [...],
    "strategic_risks": [...],
    "board_highlights": [...]
  }
}
```

---

## 7. Data Flow

### 7.1 AI Response with Memory Context

```
User Question
    |
    v
UniversalAIBrain.query()
    |
    +---> Intent Detection
    +---> Semantic Model Resolution
    +---> UniversalAnalyticsEngine.analyze()
    +---> UniversalPredictionEngine.generate()
    +---> UniversalExecutiveReportEngine.generate_report()
    +---> BusinessMemoryEngine.get_ai_context()
    |         |
    |         +---> conversation_history
    |         +---> report_history
    |         +---> insight_history
    |         +---> forecast_history
    |         +---> recommendation_history
    |         +---> business_goals
    |         +---> executive_decisions
    |         +---> kpi_history
    |         +---> business_milestones
    |
    +---> Build context prompt
    +---> Inject into response
    +---> Save to memory (conversation, KPIs, recommendations, forecasts, report)
    |
    v
AI Response with business_memory_context
```

### 7.2 Report Generation Flow

```
Report Request (audience=CEO)
    |
    v
RoleBasedReportEngine.generate_role_specific_report()
    |
    +---> UniversalAnalyticsEngine.analyze() [SAME data for all roles]
    +---> UniversalExecutiveReportEngine.generate_report() [Base report]
    |
    +---> Role-specific tailoring:
    |     CEO:   Strategic focus
    |     CFO:   Financial focus
    |     COO:   Operational focus
    |     CMO:   Marketing focus
    |     BOARD: Governance focus
    |
    +---> Save to report_history
    +---> Return formatted report
```

---

## 8. Example AI Response with Memory Context

### Question: "Has revenue improved since last upload?"

```json
{
  "answer": "1. EXECUTIVE ANSWER: Revenue shows an upward trend...\n\n2. WHAT HAPPENED: Since the last dataset upload on 2026-08-04, revenue increased from $1.1M to $1.2M (9.1% improvement)...\n\n3. WHY: The improvement correlates with the reduction in freight costs implemented on 2026-07-15 (Executive Decision: ED-001)...\n\n4. WHAT HAPPENS NEXT: Current trajectory suggests continued growth...\n\n5. WHAT SHOULD WE DO: Continue freight optimization and expand premium product line...",
  "business_memory_context": "PREVIOUS EXECUTIVE DECISIONS:\n- [approved] Reduce freight costs by COO on 2026-07-15\n\nACTIVE BUSINESS GOALS:\n- Increase Q4 Revenue: target=2000000, current=1850000\n\nPREVIOUS KPI SNAPSHOTS:\n- 2026-08-05: Revenue=$1.2M\n- 2026-08-04: Revenue=$1.1M",
  "confidence": 0.95,
  "intent": "change",
  "domain": "Retail"
}
```

### Question: "Which recommendations actually worked?"

```json
{
  "answer": "1. EXECUTIVE ANSWER: 3 of 5 recommendations have been implemented...\n\n2. WHAT HAPPENED: Recommendation 'Reduce freight costs' (approved 2026-07-15) resulted in a 15% cost reduction...\n\n3. WHY: Implementation tracked in recommendation_history shows status='completed' with outcome='15% cost reduction achieved'...\n\n4. WHAT HAPPENS NEXT: Remaining recommendations should be prioritized...\n\n5. WHAT SHOULD WE DO: Implement pending HIGH priority recommendations...",
  "business_memory_context": "RECENT RECOMMENDATIONS:\n- [completed] Reduce freight costs: outcome=15% cost reduction achieved\n- [pending] Expand premium product line\n- [in_progress] Improve customer retention",
  "confidence": 0.92,
  "intent": "recommendation"
}
```

---

## 9. Implementation Files

| File | Purpose |
|------|---------|
| `backend/app/memory/__init__.py` | Memory module init |
| `backend/app/memory/business_memory_engine.py` | Core memory engine with 11 collections |
| `backend/app/database/mongodb.py` | MongoDB connections (11 new collections) |
| `backend/app/reports/role_based_report_engine.py` | CEO/CFO/COO/CMO/Board report generator |
| `backend/app/api/v1/business_memory_api.py` | REST API endpoints for memory and reports |
| `backend/app/ai/universal_copilot_brain.py` | AI brain with memory integration |
| `backend/app/main.py` | FastAPI router registration |

---

## 10. MongoDB Connection

MongoDB is already configured in the project:

```python
# backend/app/database/mongodb.py
from pymongo import MongoClient

_client = MongoClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
_db = _client["decisionlens"]
```

All 11 business memory collections are created automatically on first use:
```python
conversation_history = get_collection("conversation_history")
report_history = get_collection("report_history")
insight_history = get_collection("insight_history")
forecast_history = get_collection("forecast_history")
recommendation_history = get_collection("recommendation_history")
business_goals = get_collection("business_goals")
executive_decisions = get_collection("executive_decisions")
forecast_accuracy = get_collection("forecast_accuracy")
kpi_history = get_collection("kpi_history")
user_feedback = get_collection("user_feedback")
business_milestones = get_collection("business_milestones")
```

---

## 11. Usage Examples

### 11.1 Creating a Business Goal

```bash
curl -X POST "http://localhost:8000/api/v1/memory/goals" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "ws-abc123",
    "title": "Increase Q4 Revenue",
    "description": "Grow revenue to $2M in Q4 2026",
    "target_metric": "revenue",
    "target_value": 2000000,
    "current_value": 1850000,
    "deadline": "2026-12-31",
    "owner": "CFO",
    "priority": "HIGH"
  }'
```

### 11.2 Generating a CEO Report

```bash
curl -X POST "http://localhost:8000/api/v1/reports/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "ws-abc123",
    "audience": "CEO",
    "session_id": "session-001",
    "format": "json"
  }'
```

### 11.3 Getting AI Context

```bash
curl "http://localhost:8000/api/v1/memory/context/ws-abc123/session-001"
```

### 11.4 Submitting User Feedback

```bash
curl -X POST "http://localhost:8000/api/v1/memory/feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "ws-abc123",
    "session_id": "session-001",
    "rating": 5,
    "comment": "Excellent analysis, very helpful for board meeting",
    "category": "report_quality"
  }'
```

---

## 12. Testing

### 12.1 Syntax Validation

```bash
cd backend
python -c "import app.memory.business_memory_engine; import app.reports.role_based_report_engine; import app.api.v1.business_memory_api; print('OK')"
```

### 12.2 MongoDB Connection Test

```bash
cd backend
python -c "from app.database.mongodb import ping_mongodb; ping_mongodb()"
```

### 12.3 Memory API Test

```bash
# Start backend
cd backend
uvicorn app.main:app --reload

# Test memory context
curl http://localhost:8000/api/v1/memory/context/ws-abc123/default

# Test report generation
curl -X POST http://localhost:8000/api/v1/reports/generate \
  -H "Content-Type: application/json" \
  -d '{"workspace_id": "ws-abc123", "audience": "CEO"}'
```

---

## 13. Future Enhancements

| Enhancement | Description |
|-------------|-------------|
| **Memory Consolidation** | Periodic summarization of old conversations to reduce storage |
| **Cross-Workspace Insights** | Share insights across related workspaces |
| **Recommendation Tracking** | Full lifecycle tracking of recommendation outcomes |
| **Forecast Model Registry** | Store and version prediction models |
| **Notification System** | Alert when goals are at risk or forecasts deviate |
| **Audit Trail** | Complete audit log of all memory modifications |
| **Memory Export** | Export business memory to PDF/Excel for compliance |
| **AI Training Data** | Use anonymized memory for model fine-tuning |

---

## 14. Conclusion

The Business Memory Engine transforms DecisionLens from a reactive analytics platform into a **context-aware decision intelligence system**. Every AI response is now enriched with the full history of the business, enabling questions like:

- "Has revenue improved since last upload?"
- "Which recommendations actually worked?"
- "What changed after reducing freight costs?"
- "How accurate were previous forecasts?"

The role-based report engine ensures that every executive receives professionally formatted insights tailored to their specific decision-making needs, all derived from the same unified analytics pipeline.

**Dashboard remains unified. Reports are role-specific.**
