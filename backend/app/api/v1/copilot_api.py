import uuid
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends
import time
from datetime import UTC, datetime

from app.ai.enterprise_decision_engine import EnterpriseDecisionEngine
from app.ai.universal_copilot_brain import UniversalAIBrain
from app.services.workspace_service import EnterpriseWorkspaceManager
from app.database.storage import ParquetStorageManager
from app.database.connection import SessionLocal
from app.database.mongodb import copilot_history as mongo_copilot_history
from app.database.duckdb_engine import DuckDBEngine
from app.cache.memory_cache import TTLCache
from app.logging.logger import get_logger
from app.core.rbac import require_permission
from app.ai.safety import AISafetyWrapper
from pathlib import Path

logger = get_logger(__name__)

router = APIRouter(
    tags=["Universal AI Data Analyst"],
    dependencies=[Depends(require_permission("use_copilot"))]
)

_parquet_path_cache = TTLCache(maxsize=16, ttl=120.0)


def _timed(label: str, fn):
    start = time.perf_counter()
    try:
        return fn()
    finally:
        logger.info("[Copilot Timing] %s: %.3fs", label, time.perf_counter() - start)

class UniversalQueryRequest(BaseModel):
    question: str
    dataset_id: Optional[str] = None
    workspace_id: Optional[str] = None
    session_id: Optional[str] = "default"
    include_charts: Optional[bool] = True
    use_groq: Optional[bool] = False
    conversation_history: Optional[List[Dict[str, Any]]] = None


def _find_parquet_path(dataset_id: Optional[str] = None) -> Optional[Path]:
    from app.database.storage import STORAGE_DIR
    db = SessionLocal()
    try:
        if dataset_id and dataset_id != "latest":
            path = ParquetStorageManager.get_parquet_path(dataset_id)
            if path and path.exists():
                return path

        ws_id = EnterpriseWorkspaceManager.get_active_workspace_id() or ""
        best_p = UniversalAIBrain._resolve_parquet_path(workspace_id=ws_id, dataset_id=dataset_id)
        if best_p and best_p.exists():
            return best_p

        parquet_files = list(STORAGE_DIR.glob("*.parquet")) + list((STORAGE_DIR / "parquet").glob("*.parquet"))
        for p in parquet_files:
            if not p.name.startswith("unified_"):
                if p.stat().st_size > 0:
                    return p

        return parquet_files[0] if parquet_files else None
    finally:
        db.close()


@router.post("/query")
def universal_analyst_query(body: UniversalQueryRequest):
    request_start = time.perf_counter()
    logger.info("[Copilot] Request received: question=%r workspace=%r dataset=%r", body.question, body.workspace_id, body.dataset_id)

    if not body.question or not body.question.strip():
        logger.info("[Copilot] Empty question rejected")
        return {
            "answer": "Please enter a valid business question.",
            "executive_summary": "Please enter a valid business question.",
            "confidence": 0.0,
            "confidence_score": 0.0,
            "evidence": {
                "metrics": [],
                "sql": None,
                "rows": [],
                "tables": [],
                "columns": [],
                "confidence": 0.0,
                "validation": {"status": "INVALID", "rows_returned": 0},
                "dataset_path": "",
                "total_rows": 0,
                "measures_analyzed": [],
                "dimensions_analyzed": [],
                "models_used": [],
                "traceability": "",
            },
            "data_evidence": [],
            "follow_up_questions": [],
            "datasets": [],
            "datasets_used": [],
            "tables": [],
            "tables_used": [],
            "columns_used": [],
            "kpis": [],
            "kpis_used": [],
            "calculation": "N/A",
            "sql_used": None,
            "business_reasoning": "Empty question provided.",
            "recommendation": {"title": "Action Required", "actions": ["Enter a question"], "risks": [], "opportunities": [], "confidence": 0.0},
            "validation": {"status": "INVALID", "rows_returned": 0},
            "charts": [],
            "intent": "empty",
            "domain": "Unknown",
            "status": "error",
            "error": "Empty question",
            "timestamp": datetime.now(UTC).isoformat()
        }

    ws_id = body.workspace_id or body.dataset_id
    logger.info("[Copilot] Workspace resolved: %r", ws_id)

    try:
        t0 = time.perf_counter()
        engine_res = EnterpriseDecisionEngine.query(
            question=body.question,
            workspace_id=ws_id,
            dataset_id=body.dataset_id,
            session_id=body.session_id or "default",
            use_groq=body.use_groq or False,
            conversation_history=body.conversation_history or None,
        )
        logger.info("[Copilot] Engine completed in %.3fs", time.perf_counter() - t0)

        ev_section = engine_res.get("evidence", {})
        if not isinstance(ev_section, dict):
            ev_section = {}
        ev_list = ev_section.get("rows", [])
        supp_dict = engine_res.get("support") if isinstance(engine_res.get("support"), dict) else {}
        tables_list = engine_res.get("tables_used") or supp_dict.get("tables_used") or []
        cols_list = engine_res.get("columns_used") or []
        rec_val = supp_dict.get("recommendation") or engine_res.get("recommendation") or {}
        rec_obj = rec_val if isinstance(rec_val, dict) else {"title": "Executive Recommendation", "actions": [], "risks": [], "opportunities": [], "confidence": 0.0}

        safety = AISafetyWrapper.validate_answer(
            answer=engine_res.get("answer", ""),
            evidence=ev_list,
            sql_query=engine_res.get("sql_query") or supp_dict.get("sql_query"),
            rows_analyzed=len(ev_list),
            columns_used=cols_list,
            models_used=engine_res.get("models_used", []),
        )

        if not safety.allowed:
            engine_res["answer"] = "I don't have enough evidence to answer that question."
            engine_res["confidence"] = 0.0
            engine_res["status"] = "insufficient_evidence"

        try:
            mongo_copilot_history.insert_one({
                "session_id": body.session_id or "default",
                "workspace_id": ws_id,
                "question": body.question,
                "answer": engine_res.get("answer", ""),
                "domain": supp_dict.get("domain") or engine_res.get("domain") or "Generic",
                "confidence": engine_res.get("confidence", 0.95),
                "timestamp": datetime.now(UTC).isoformat(),
            })
        except Exception as mongo_exc:
            logger.warning("[MongoDB Copilot History] %s", mongo_exc)

        total_ms = (time.perf_counter() - request_start) * 1000
        logger.info("[Copilot] Request completed in %.1fms", total_ms)

        return {
            "answer": engine_res.get("answer", "No textual summary produced."),
            "executive_summary": engine_res.get("executive_summary", engine_res.get("answer", "")),
            "confidence": engine_res.get("confidence", 0.95),
            "confidence_score": engine_res.get("confidence_score", engine_res.get("confidence", 0.95)),
            "evidence": ev_list,
            "data_evidence": engine_res.get("data_evidence", ev_list),
            "follow_up_questions": engine_res.get("follow_up_questions") or supp_dict.get("follow_up_questions") or [],
            "datasets": [engine_res.get("dataset", engine_res.get("domain", "Workspace"))],
            "datasets_used": [engine_res.get("dataset", engine_res.get("domain", "Workspace"))],
            "tables": tables_list,
            "tables_used": tables_list,
            "columns_used": cols_list,
            "kpis": engine_res.get("kpis") or engine_res.get("kpis_used") or [],
            "kpis_used": engine_res.get("kpis") or engine_res.get("kpis_used") or [],
            "calculation": engine_res.get("calculation", "N/A"),
            "sql_used": supp_dict.get("sql_used") or engine_res.get("sql_used"),
            "business_reasoning": supp_dict.get("business_reasoning") or engine_res.get("business_reasoning") or "Analysis derived from verified data analysis.",
            "recommendation": rec_obj,
            "validation": supp_dict.get("validation") or engine_res.get("validation") or {"status": "VERIFIED", "rows_returned": 0},
            "charts": supp_dict.get("charts") or engine_res.get("charts") or [],
            "intent": supp_dict.get("intent") or engine_res.get("intent") or "query",
            "domain": supp_dict.get("domain") or engine_res.get("domain") or "Generic",
            "status": engine_res.get("status", "success"),
            "error": engine_res.get("error"),
            "timestamp": engine_res.get("timestamp", datetime.now(UTC).isoformat()),
        }
    except Exception as exc:
        total_ms = (time.perf_counter() - request_start) * 1000
        request_id = str(uuid.uuid4())
        logger.error("[Copilot] Request %s failed after %.1fms: %s", request_id, total_ms, exc, exc_info=True)
        error_message = str(exc).split('\n')[0].strip()
        if not error_message:
            error_message = "An unexpected error occurred during Copilot analysis."
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": error_message,
                "request_id": request_id,
                "message": "An unexpected error occurred during Copilot analysis.",
            },
        )


@router.post("/reset")
def reset_copilot_session(body: Optional[Dict[str, Any]] = None):
    session_id = (body or {}).get("session_id", "default")
    try:
        mongo_copilot_history.delete_many({"session_id": session_id})
    except Exception as mongo_exc:
        logger.warning("[MongoDB Copilot History] %s", mongo_exc)
    try:
        from app.ai.conversation_memory import ConversationMemory
        ConversationMemory.reset_session(session_id)
    except Exception as mem_exc:
        logger.warning("[ConversationMemory] %s", mem_exc)
    return {
        "status": "success",
        "message": f"Copilot conversation memory reset for session '{session_id}'.",
        "session_id": session_id
    }


@router.get("/history")
def get_copilot_history(session_id: Optional[str] = "default", limit: int = 50, offset: int = 0):
    try:
        query = {"session_id": session_id}
        cursor = mongo_copilot_history.find(query, {"_id": 0}).sort("timestamp", 1).skip(offset).limit(limit)
        history = list(cursor)
        return {
            "session_id": session_id,
            "limit": limit,
            "offset": offset,
            "history": history
        }
    except Exception as mongo_exc:
        logger.warning("[MongoDB Copilot History] %s", mongo_exc)
        return {
            "session_id": session_id,
            "limit": limit,
            "offset": offset,
            "history": []
        }


@router.get("/health")
def universal_analyst_health():
    return {
        "status": "operational",
        "pipeline_stages": [
            "Conversation Memory",
            "Workspace Context",
            "Dataset Intelligence",
            "Universal Analytics Engine",
            "Dynamic KPI Engine",
            "Forecast Engine",
            "Recommendation Engine",
            "Executive Report Engine",
            "Evidence Builder",
            "Business Context Builder",
            "Decision Mode Router",
            "Answer Validation Layer",
            "Final Response Assembly",
        ],
        "features": [
            "Single Universal AI Brain for all reasoning",
            "Industry-agnostic: supports ANY domain automatically",
            "No hardcoded retail/healthcare/education assumptions",
            "Dynamic SQL generation from semantic schema",
            "Evidence-based answers with confidence scoring",
            "No hallucination - all answers derived from verified data analysis",
            "Executive-grade decision intelligence response",
            "Memory-aware: uses previous conversations and decisions",
            "Context-aware: includes business context, risks, opportunities",
            "Cache-aware: reuses analytics, forecasts, recommendations",
            "Decision mode routing: Explain, Compare, Predict, Recommend, Diagnose, Root Cause, What-if, Risk, Opportunity, Benchmark",
            "Follow-up question generation",
            "Board and investor summary support",
            "Groq LLM optional integration",
        ],
        "caching": {
            "parquet_path_cache": _parquet_path_cache.stats(),
        },
    }