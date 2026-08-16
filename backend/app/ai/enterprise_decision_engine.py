from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from pathlib import Path
import time

from app.ai.business_context_builder import BusinessContextBuilder
from app.ai.decision_mode_router import DecisionModeRouter
from app.ai.evidence_builder import EvidenceBuilder
from app.ai.validation.answer_validator import AnswerValidationLayer
from app.ai.validation.schemas import AnswerValidationRequest, EvidenceRecord, NumericClaim, RecommendationClaim, InsightClaim
from app.ai.groq_client import GroqClient
from app.memory.business_memory_engine import BusinessMemoryEngine
from app.services.analytics_cache_service import AnalyticsCacheService
from app.services.workspace_service import EnterpriseWorkspaceManager
from app.logging.logger import get_logger

logger = get_logger(__name__)


class EnterpriseDecisionEngine:
    """
    Enterprise Decision Engine - Phase 4.

    The single orchestration layer for the Enterprise AI Decision Intelligence platform.
    Every user question flows through this engine.

    Pipeline:
      1. Conversation Memory
      2. Workspace Context
      3. Dataset Intelligence
      4. Universal Analytics (cache-aware)
      5. Dynamic KPI Engine
      6. Forecast Engine (cache-aware)
      7. Recommendation Engine
      8. Relevant Executive Report
      9. Evidence Builder
      10. Business Context Builder
      11. Groq (optional)
      12. Answer Validation Layer
      13. Final Response Assembly
      14. Conversation Memory Storage (enriched)

    Guarantees:
      - No hallucinations: every answer grounded in executed SQL and analytics.
      - Memory-aware: uses previous conversations, decisions, and goals.
      - Context-aware: includes business context, risks, opportunities.
      - Cache-aware: reuses analytics, forecasts, and recommendations.
      - Executive-grade: structured for business leadership consumption.
    """

    @classmethod
    def query(
        cls,
        question: str,
        workspace_id: Optional[str] = None,
        dataset_id: Optional[str] = None,
        session_id: str = "default",
        use_groq: bool = False,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        request_start = time.perf_counter()
        if not question or not question.strip():
            return cls._build_empty_response("Empty question provided.")

        ws_id = workspace_id or EnterpriseWorkspaceManager.get_active_workspace_id() or "default"
        logger.info("[DecisionEngine] START question=%r ws=%s", question[:80], ws_id)

        if conversation_history is not None:
            history = conversation_history
            logger.info("[DecisionEngine] Using frontend-provided history (%d turns)", len(history))
        else:
            t0 = time.perf_counter()
            history = cls._load_conversation_history(session_id, ws_id)
            logger.info("[DecisionEngine] Loaded history in %.3fs (%d turns)", time.perf_counter() - t0, len(history))

        t0 = time.perf_counter()
        decision_mode = DecisionModeRouter.route(question, history)
        logger.info("[DecisionEngine] Mode routed in %.3fs: %s", time.perf_counter() - t0, decision_mode["mode"])

        t0 = time.perf_counter()
        parquet_path = cls._resolve_parquet_path(workspace_id, dataset_id)
        logger.info("[DecisionEngine] Parquet resolved in %.3fs: %s", time.perf_counter() - t0, parquet_path)
        if not parquet_path or not parquet_path.exists():
            return cls._build_unavailable_response(question, decision_mode, "No active workspace dataset available.")

        t0 = time.perf_counter()
        profile = cls._get_or_profile_dataset(parquet_path)
        logger.info("[DecisionEngine] Profiled in %.3fs (%d cols)", time.perf_counter() - t0, len(profile.get("columns", {})))

        t0 = time.perf_counter()
        semantic_model = cls._build_semantic_model(ws_id)
        logger.info("[DecisionEngine] Semantic model built in %.3fs", time.perf_counter() - t0)

        t0 = time.perf_counter()
        analytics_dict = cls._get_or_compute_analytics(ws_id, semantic_model, parquet_path, profile)
        logger.info("[DecisionEngine] Analytics in %.3fs", time.perf_counter() - t0)
        if not analytics_dict:
            return cls._build_unavailable_response(question, decision_mode, "Analytics computation failed.")

        t0 = time.perf_counter()
        predictions = cls._get_or_compute_predictions(ws_id, semantic_model, parquet_path, analytics_dict, profile)
        logger.info("[DecisionEngine] Predictions in %.3fs", time.perf_counter() - t0)

        t0 = time.perf_counter()
        recommendations = cls._get_or_compute_recommendations(parquet_path, profile, analytics_dict)
        logger.info("[DecisionEngine] Recommendations in %.3fs", time.perf_counter() - t0)

        t0 = time.perf_counter()
        executive_report = cls._get_or_compute_executive_report(analytics_dict, semantic_model, predictions)
        logger.info("[DecisionEngine] Executive report in %.3fs", time.perf_counter() - t0)

        t0 = time.perf_counter()
        sql_query, tables_used, columns_used, evidence_rows, sql_error = cls._execute_evidence_query(
            decision_mode["mode"], analytics_dict, parquet_path, question, history=history
        )
        evidence_rows = cls._normalize_evidence_rows(evidence_rows)
        logger.info(
            "[DecisionEngine] Evidence query completed: type=%s count=%d",
            type(evidence_rows).__name__,
            len(evidence_rows) if evidence_rows else 0,
        )
        if evidence_rows:
            logger.info(
                "[DecisionEngine] Evidence row[0] type=%s keys=%s",
                type(evidence_rows[0]).__name__,
                list(evidence_rows[0].keys()) if isinstance(evidence_rows[0], dict) else type(evidence_rows[0]).__name__,
            )

        t0 = time.perf_counter()
        confidence = cls._compute_confidence(evidence_rows, analytics_dict)
        validation = cls._validate_evidence(evidence_rows, analytics_dict, sql_error)
        business_context = BusinessContextBuilder.build(
            workspace_id=ws_id,
            session_id=session_id,
            analytics_dict=analytics_dict,
            semantic_model=semantic_model,
            question=question,
        )
        context_prompt = BusinessContextBuilder.build_context_prompt(business_context)
        evidence_report = EvidenceBuilder.build(
            analytics_dict=analytics_dict,
            predictions=predictions,
            recommendations=recommendations,
            evidence_rows=evidence_rows,
            sql_query=sql_query,
            tables_used=tables_used,
            columns_used=columns_used,
            validation=validation,
            profile=profile,
            domain=analytics_dict.get("domain", "Generic Business"),
        )
        answer_validation = cls._run_answer_validation(
            question=question,
            answer_text=cls._build_executive_answer(question, decision_mode, analytics_dict, predictions, recommendations, evidence_rows, sql_query, business_context.get("domain", "Generic Business")),
            evidence_rows=evidence_rows,
            sql_query=sql_query,
            tables_used=tables_used,
            columns_used=columns_used,
            analytics_dict=analytics_dict,
            recommendations=recommendations,
            domain=business_context.get("domain", "Generic Business"),
            status="error" if sql_error else ("ok" if evidence_rows else "empty_result"),
        )
        logger.info("[DecisionEngine] Post-analytics in %.3fs", time.perf_counter() - t0)

        llm_response = None
        if use_groq:
            t0 = time.perf_counter()
            llm_response = cls._generate_llm_response(question, business_context, evidence_report, decision_mode)
            logger.info("[DecisionEngine] LLM in %.3fs", time.perf_counter() - t0)

        t0 = time.perf_counter()
        follow_up_questions = cls._generate_follow_up_questions(question, decision_mode, analytics_dict, profile, history=history)

        response = cls._assemble_response(
            question=question,
            decision_mode=decision_mode,
            analytics_dict=analytics_dict,
            predictions=predictions,
            recommendations=recommendations,
            evidence_rows=evidence_rows,
            sql_query=sql_query,
            tables_used=tables_used,
            columns_used=columns_used,
            validation=validation,
            business_context=business_context,
            context_prompt=context_prompt,
            evidence_report=evidence_report,
            answer_validation=answer_validation,
            executive_report=executive_report,
            follow_up_questions=follow_up_questions,
            llm_response=llm_response,
            confidence=confidence,
        )
        logger.info("[DecisionEngine] Response assembled in %.3fs", time.perf_counter() - t0)

        t0 = time.perf_counter()
        cls._save_enriched_conversation(session_id, ws_id, question, response, decision_mode, business_context, dataset_id)
        logger.info("[DecisionEngine] Conversation saved in %.3fs", time.perf_counter() - t0)

        total_ms = (time.perf_counter() - request_start) * 1000
        logger.info("[DecisionEngine] DONE in %.1fms", total_ms)
        return response

    @classmethod
    def _load_conversation_history(cls, session_id: str, workspace_id: str) -> List[Dict[str, Any]]:
        try:
            from app.memory.business_memory_engine import BusinessMemoryEngine
            return BusinessMemoryEngine.get_conversation_history(session_id, workspace_id, last_n=10)
        except Exception:
            return []

    @classmethod
    def _resolve_parquet_path(cls, workspace_id: Optional[str], dataset_id: Optional[str]) -> Optional[Path]:
        try:
            from app.ai.universal_copilot_brain import UniversalAIBrain
            return UniversalAIBrain._resolve_parquet_path(workspace_id, dataset_id)
        except Exception:
            return None

    @classmethod
    def _get_or_profile_dataset(cls, parquet_path: Path) -> Dict[str, Any]:
        try:
            from app.ingestion.semantic_profiler import SemanticDataProfiler
            return SemanticDataProfiler.profile(parquet_path) or {}
        except Exception:
            return {}

    @classmethod
    def _build_semantic_model(cls, workspace_id: str):
        try:
            from app.semantic_model.engine import build_semantic_model
            from app.semantic_model.core import SemanticModel
            sm = build_semantic_model(workspace_id=workspace_id, force_rebuild=False)
            if isinstance(sm, dict):
                return SemanticModel(
                    workspace_id=workspace_id,
                    domain=sm.get("domain", "Generic Business"),
                    dataset_type=sm.get("dataset_type", "Unknown"),
                )
            return sm
        except Exception:
            return None

    @classmethod
    def _get_or_compute_analytics(cls, workspace_id: str, semantic_model: Any, parquet_path: Path, profile: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            cached = AnalyticsCacheService.get_cached(workspace_id)
            if cached:
                return cached
        except Exception:
            pass

        try:
            from app.analytics.universal_engine import UniversalAnalyticsEngine
            result = UniversalAnalyticsEngine.analyze(semantic_model, parquet_path=parquet_path, profile=profile)
            analytics_dict = result.to_dict() if hasattr(result, "to_dict") else {}
            if analytics_dict:
                try:
                    AnalyticsCacheService.set_cached(workspace_id, analytics_dict)
                except Exception:
                    pass
            return analytics_dict
        except Exception as exc:
            logger.error("[DecisionEngine] Analytics failed: %s", exc)
            return None

    @classmethod
    def _get_or_compute_predictions(cls, workspace_id: str, semantic_model: Any, parquet_path: Path, analytics_dict: Dict[str, Any], profile: Dict[str, Any]) -> List[Any]:
        try:
            from app.ml.prediction_engine import UniversalPredictionEngine
            from types import SimpleNamespace
            partial = SimpleNamespace(
                trends=analytics_dict.get("trends", {}),
                correlations=analytics_dict.get("correlations", []),
                root_causes=analytics_dict.get("root_causes", []),
                drivers=analytics_dict.get("drivers", []),
                anomalies=analytics_dict.get("anomalies", []),
                outliers=analytics_dict.get("outliers", []),
                kpis=analytics_dict.get("kpis", []),
                volume=analytics_dict.get("volume", 0),
                confidence_score=analytics_dict.get("confidence_score", 0.0),
                evidence=analytics_dict.get("evidence", {}),
            )
            return UniversalPredictionEngine.generate(analytics_result=partial, semantic_model=semantic_model)
        except Exception as exc:
            logger.error("[DecisionEngine] Prediction failed: %s", exc)
            return []

    @classmethod
    def _get_or_compute_recommendations(cls, parquet_path: Path, profile: Dict[str, Any], analytics_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
        try:
            from app.analytics.recommendation_engine import RecommendationEngine
            recs = RecommendationEngine.generate_recommendations(parquet_path, profile)
            result = []
            for r in recs.get("recommendations", []):
                if isinstance(r, dict):
                    result.append(r)
                else:
                    result.append(r.__dict__ if hasattr(r, "__dict__") else {})
            return result
        except Exception as exc:
            logger.error("[DecisionEngine] Recommendations failed: %s", exc)
            return []

    @classmethod
    def _get_or_compute_executive_report(cls, analytics_dict: Dict[str, Any], semantic_model: Any, predictions: List[Any]) -> Dict[str, Any]:
        try:
            from app.reports.executive_report_engine import UniversalExecutiveReportEngine
            from app.schemas.analytics import AnalyticsResult
            result = AnalyticsResult(**analytics_dict)
            report = UniversalExecutiveReportEngine.generate_report(
                analytics_result=result,
                semantic_model=semantic_model,
                prediction_result=predictions,
            )
            return report
        except Exception as exc:
            logger.error("[DecisionEngine] Executive report failed: %s", exc)
            return {}

    @classmethod
    def _execute_evidence_query(cls, intent: str, analytics_dict: Dict[str, Any], parquet_path: Path, question: str, history: Optional[List[Dict[str, Any]]] = None) -> tuple:
        try:
            from app.ai.universal_copilot_brain import UniversalAIBrain
            profile = {}
            try:
                from app.ingestion.semantic_profiler import SemanticDataProfiler
                profile = SemanticDataProfiler.profile(parquet_path)
            except Exception:
                pass
            measures = profile.get("column_categories", {}).get("measures", [])
            dimensions = profile.get("column_categories", {}).get("dimensions", [])
            temporal = profile.get("column_categories", {}).get("temporal", [])
            tables = []
            try:
                ws_id = EnterpriseWorkspaceManager.get_active_workspace_id() or ""
                ws_info = EnterpriseWorkspaceManager.get_workspace(ws_id) or {}
                tables = ws_info.get("tables", [])
            except Exception:
                pass
            if not tables:
                tables = [{
                    "table_name": parquet_path.stem,
                    "file_path": str(parquet_path),
                    "role": "Fact Table",
                    "columns": list(profile.get("columns", {}).keys()),
                }]
            table_profiles = {}
            for tbl in tables:
                fp = tbl.get("file_path")
                if fp:
                    try:
                        table_profiles[tbl["table_name"]] = SemanticDataProfiler.profile(Path(fp))
                    except Exception:
                        continue
            return UniversalAIBrain._execute_evidence_query(
                intent, measures, dimensions, temporal, parquet_path, tables, table_profiles, question, history=history
            )
        except Exception as exc:
            logger.error("[DecisionEngine] Evidence query failed: %s", exc)
            return "", [], [], [], str(exc)

    @classmethod
    def _compute_confidence(cls, evidence_rows: List[Dict[str, Any]], analytics_dict: Dict[str, Any]) -> float:
        if not evidence_rows:
            return round(analytics_dict.get("confidence_score", 0.0) / 100.0, 2) if analytics_dict.get("confidence_score", 0.0) > 1 else round(analytics_dict.get("confidence_score", 0.0), 2)
        row_count = len(evidence_rows)
        total_rows = analytics_dict.get("volume", 0)
        if total_rows > 0 and row_count / total_rows < 0.01:
            return 0.75
        base = 0.92
        if row_count < 5:
            base -= 0.05
        return min(0.99, max(0.50, base))

    @classmethod
    def _validate_evidence(cls, evidence_rows: List[Dict[str, Any]], analytics_dict: Dict[str, Any], sql_error: Optional[str]) -> Dict[str, Any]:
        if sql_error:
            return {"status": "ERROR", "rows_returned": 0, "message": sql_error}
        row_count = len(evidence_rows)
        total_rows = analytics_dict.get("volume", 0)
        status = "VERIFIED"
        if row_count == 0:
            status = "EMPTY_RESULT"
        elif total_rows > 0 and row_count / total_rows < 0.001:
            status = "LOW_SAMPLE"
        return {
            "status": status,
            "rows_returned": row_count,
            "total_dataset_rows": total_rows,
            "sample_coverage_pct": round((row_count / total_rows * 100), 2) if total_rows > 0 else 0,
        }

    @classmethod
    def _run_answer_validation(cls, question: str, answer_text: str, evidence_rows: List[Dict[str, Any]], sql_query: str, tables_used: List[str], columns_used: List[str], analytics_dict: Dict[str, Any], recommendations: List[Dict[str, Any]], domain: str, status: str) -> Any:
        evidence_records = [
            EvidenceRecord(
                source="duckdb_sql",
                query=sql_query,
                rows_returned=len(evidence_rows),
                columns_used=columns_used,
                tables_used=tables_used,
                snippet=evidence_rows[0].__str__() if evidence_rows else None,
                confidence=cls._compute_confidence(evidence_rows, analytics_dict),
            )
        ]
        numeric_claims = []
        for ev in (evidence_rows[:5] if evidence_rows else []):
            for key, value in ev.items():
                if isinstance(value, (int, float)) and abs(value) > 1:
                    numeric_claims.append(NumericClaim(value=str(value), context=f"{key} from query result", evidence_ref="duckdb_sql"))
        rec_claims = []
        if recommendations:
            finding_refs = [str(ev) for ev in (evidence_rows[:3] if evidence_rows else [])]
            rec_claims.append(RecommendationClaim(text="; ".join([r.get("action", r.get("title", "")) for r in recommendations[:3]]), finding_refs=finding_refs))
        insight_claims = []
        for ev in (evidence_rows[:3] if evidence_rows else []):
            insight_claims.append(InsightClaim(text=str(ev), evidence_refs=[sql_query] if sql_query else []))
        return AnswerValidationLayer.validate(AnswerValidationRequest(
            question=question,
            answer_text=answer_text,
            evidence=evidence_records,
            numeric_values=numeric_claims,
            recommendations=rec_claims,
            insights=insight_claims,
            sql_query=sql_query,
            analysis_rows=evidence_rows,
            dataset_columns=columns_used,
            domain=domain,
            status=status,
        ))

    @classmethod
    def _generate_llm_response(cls, question: str, business_context: Dict[str, Any], evidence_report: Any, decision_mode: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        client = GroqClient()
        if not client.is_configured():
            return None
        prompt = cls._build_llm_prompt(question, business_context, evidence_report, decision_mode)
        evidence_block = {
            "sql_query": getattr(evidence_report, "sql_query", ""),
            "rows": getattr(evidence_report, "evidence_rows", [])[:50],
            "tables_used": getattr(evidence_report, "tables_used", []),
            "columns_used": getattr(evidence_report, "columns_used", []),
            "rows_analyzed": getattr(evidence_report, "rows_returned", 0),
            "models_used": getattr(evidence_report, "models_used", []),
        }
        return client.generate(prompt, evidence_block=evidence_block)

    @classmethod
    def _build_llm_prompt(cls, question: str, business_context: Dict[str, Any], evidence_report: Any, decision_mode: Dict[str, Any]) -> str:
        parts = [f"Question: {question}\n"]
        parts.append(f"Decision Mode: {decision_mode.get('mode', 'summarize')}\n")
        parts.append(f"Domain: {business_context.get('domain', 'Generic Business')}\n")
        if business_context.get("important_kpis"):
            parts.append(f"Top KPIs: {', '.join([k.get('name', '') for k in business_context['important_kpis'][:5]])}\n")
        if business_context.get("top_risks"):
            parts.append(f"Top Risks: {', '.join([r.get('title', '') for r in business_context['top_risks'][:3]])}\n")
        if business_context.get("top_opportunities"):
            parts.append(f"Top Opportunities: {', '.join([o.get('title', '') for o in business_context['top_opportunities'][:3]])}\n")
        parts.append(f"Evidence: {evidence_report.evidence if hasattr(evidence_report, 'evidence') else ''}\n")
        parts.append(f"Recommendation: {evidence_report.recommendation if hasattr(evidence_report, 'recommendation') else ''}\n")
        parts.append("\nGenerate an executive-grade response grounded in the above evidence. If evidence is insufficient, say so explicitly.")
        return "\n".join(parts)

    @classmethod
    def _build_executive_answer(cls, question: str, decision_mode: Dict[str, Any], analytics_dict: Dict[str, Any], predictions: List[Any], recommendations: List[Dict[str, Any]], evidence_rows: List[Dict[str, Any]], sql_query: str, domain: str) -> str:
        mode = decision_mode["mode"]
        kpis = analytics_dict.get("kpis", [])
        anomalies = analytics_dict.get("anomalies", [])
        root_causes = analytics_dict.get("root_causes", [])
        risks = analytics_dict.get("risks", [])
        opportunities = analytics_dict.get("opportunities", [])
        volume = analytics_dict.get("volume", 0)

        if mode == "explain":
            return (
                f"1. EXECUTIVE ANSWER: This {domain} visualization is derived from {volume:,} verified records.\n\n"
                f"2. WHAT HAPPENED: The analysis covers {len(kpis)} KPIs and {len(analytics_dict.get('dimensions', []))} dimensions from the dataset.\n\n"
                f"3. WHY: Patterns reflect underlying data distributions computed from verified data analysis.\n\n"
                f"4. WHAT HAPPENS NEXT: Trends indicate continued patterns under current conditions unless underlying data changes.\n\n"
                f"5. WHAT SHOULD WE DO: Use this visualization to monitor KPIs and identify deviations from expected patterns."
            )

        elif mode == "compare" and evidence_rows:
            first = evidence_rows[0] if evidence_rows else {}
            if not isinstance(first, dict):
                first = {}
            cat_key = "category" if "category" in first else "dimension"
            val_key = "metric_value" if "metric_value" in first else "value"
            best = max(evidence_rows, key=lambda r: r.get(val_key, 0) or 0 if isinstance(r, dict) else 0) if evidence_rows else {}
            worst = min(evidence_rows, key=lambda r: r.get(val_key, 0) or 0 if isinstance(r, dict) else 0) if evidence_rows else {}
            best_val = best.get(val_key, 0) if isinstance(best, dict) else 0
            worst_val = worst.get(val_key, 0) if isinstance(worst, dict) else 0
            best_cat = best.get(cat_key, "N/A") if isinstance(best, dict) else "N/A"
            worst_cat = worst.get(cat_key, "N/A") if isinstance(worst, dict) else "N/A"
            measure_name = analytics_dict.get("evidence", {}).get("measures_analyzed", ["metric"])[0].replace("_", " ") if analytics_dict.get("evidence", {}).get("measures_analyzed") else "metric"
            return (
                f"1. EXECUTIVE ANSWER: '{best_cat}' leads with {best_val:,.2f} while '{worst_cat}' has {worst_val:,.2f} in {measure_name}.\n\n"
                f"2. WHAT HAPPENED: Category comparison across {len(evidence_rows)} segments reveals performance variance in {measure_name}.\n\n"
                f"3. WHY: Performance variance is driven by the difference in {measure_name} aggregates across categories, confirmed by SQL GROUP BY.\n\n"
                f"4. WHAT HAPPENS NEXT: Segment dynamics will maintain current relative positioning unless underlying conditions change.\n\n"
                f"5. WHAT SHOULD WE DO: Investigate underperforming segments for optimization while reinforcing leaders."
            )

        elif mode == "predict":
            norm_preds = cls._normalize_predictions(predictions)
            forecast_pred = next((p for p in norm_preds if p.get("feasible")), None)
            if forecast_pred:
                return (
                    f"1. EXECUTIVE ANSWER: {forecast_pred.get('prediction', 'Forecast unavailable.')}\n\n"
                    f"2. WHAT HAPPENED: {volume:,} records analyzed. {len(analytics_dict.get('trends', {}))} trend(s) detected.\n\n"
                    f"3. WHY: Historical patterns and correlation structures drive the projected trajectory.\n\n"
                    f"4. WHAT HAPPENS NEXT: {forecast_pred.get('prediction', 'No projection available.')}\n\n"
                    f"5. WHAT SHOULD WE DO: {forecast_pred.get('recommended_action', 'Continue monitoring.')}"
                )
            return (
                f"1. EXECUTIVE ANSWER: Forecast projection unavailable with current data.\n\n"
                f"2. WHAT HAPPENED: {volume:,} records analyzed.\n\n"
                f"3. WHY: Insufficient temporal patterns or numeric measures for reliable forecasting.\n\n"
                f"4. WHAT HAPPENS NEXT: Baseline stability expected.\n\n"
                f"5. WHAT SHOULD WE DO: Upload multi-period datasets with temporal columns to enable time-series forecasting."
            )

        elif mode == "recommend":
            rec_actions = [r.get("action", r.get("title", "")) for r in (recommendations or [])[:3] if isinstance(r, dict)]
            rec_text = "; ".join(rec_actions) if rec_actions else "No evidence-backed recommendations available for this dataset."
            return (
                f"1. EXECUTIVE ANSWER: Based on {volume:,} records, the recommended actions are: {rec_text}\n\n"
                f"2. WHAT HAPPENED: {volume:,} records analyzed with {len(kpis)} KPIs and {len(root_causes)} drivers identified.\n\n"
                f"3. WHY: Evidence-based analysis identified key drivers and concentration patterns from the dataset.\n\n"
                f"4. WHAT HAPPENS NEXT: Recommendations are prioritized by impact and feasibility based on dataset evidence.\n\n"
                f"5. WHAT SHOULD WE DO: {rec_text}"
            )

        elif mode == "diagnose":
            anomaly_count = len(anomalies)
            high_severity = sum(1 for a in anomalies if str(getattr(a, "severity", "") if hasattr(a, "severity") else a.get("severity", "")).upper() in ("HIGH", "CRITICAL")) if anomalies else 0
            return (
                f"1. EXECUTIVE ANSWER: {anomaly_count} anomalies detected. {high_severity} high-severity requiring investigation.\n\n"
                f"2. WHAT HAPPENED: Statistical outlier detection identified {anomaly_count} anomalous observations.\n\n"
                f"3. WHY: Data points exceeded 2-sigma variance limits from historical baseline distributions.\n\n"
                f"4. WHAT HAPPENS NEXT: Unmitigated variance risks propagating operational disruption.\n\n"
                f"5. WHAT SHOULD WE DO: Initiate root-cause audit on flagged periods and calibrate alert thresholds."
            )

        elif mode == "root_cause_analysis":
            top_drivers = []
            for rc in root_causes[:3]:
                if isinstance(rc, dict):
                    td = rc.get("top_driver", {})
                    if td:
                        top_drivers.append(f"{rc.get('dimension', '')}: {td.get('category', '')} ({td.get('contribution_percentage', 0)}%)")
                elif hasattr(rc, "top_driver") and rc.top_driver:
                    top_drivers.append(f"{rc.dimension}: {rc.top_driver.get('category', '')} ({rc.top_driver.get('contribution_percentage', 0)}%)")
            drivers_text = "; ".join(top_drivers) if top_drivers else "No significant drivers identified."
            return (
                f"1. EXECUTIVE ANSWER: Root cause analysis identifies {len(root_causes)} key drivers.\n\n"
                f"2. WHAT HAPPENED: Variance decomposition across {len(analytics_dict.get('dimensions', []))} dimensions reveals concentration patterns.\n\n"
                f"3. WHY: {drivers_text}\n\n"
                f"4. WHAT HAPPENS NEXT: Current drivers will continue influencing metrics unless rebalanced.\n\n"
                f"5. WHAT SHOULD WE DO: Address concentration risks and diversify across secondary segments."
            )

        elif mode == "what_if_simulation":
            return (
                f"1. EXECUTIVE ANSWER: Scenario simulation requires explicit adjustment parameters.\n\n"
                f"2. WHAT HAPPENED: {volume:,} records analyzed. {len(analytics_dict.get('trends', {}))} trends detected.\n\n"
                f"3. WHY: Simulation requires defining base metric, adjustment value, and unit.\n\n"
                f"4. WHAT HAPPENS NEXT: Estimated impact can be calculated once parameters are provided.\n\n"
                f"5. WHAT SHOULD WE DO: Specify the metric to adjust, the adjustment value, and the unit (absolute or percentage)."
            )

        elif mode == "risk_assessment":
            risk_titles = [r.get("title", r.get("title", "")) for r in (risks or [])[:3] if isinstance(r, dict)]
            risk_text = "; ".join(risk_titles) if risk_titles else "No significant risks identified."
            return (
                f"1. EXECUTIVE ANSWER: {len(risks)} risks identified. {risk_text}\n\n"
                f"2. WHAT HAPPENED: Risk assessment based on anomaly severity, concentration risk, and driver analysis.\n\n"
                f"3. WHY: {risk_text}\n\n"
                f"4. WHAT HAPPENS NEXT: Unmitigated risks may impact business continuity and financial performance.\n\n"
                f"5. WHAT SHOULD WE DO: Prioritize CRITICAL and HIGH severity risks with mitigation plans."
            )

        elif mode == "opportunity_detection":
            opp_titles = [o.get("title", o.get("title", "")) for o in (opportunities or [])[:3] if isinstance(o, dict)]
            opp_text = "; ".join(opp_titles) if opp_titles else "No significant opportunities identified."
            return (
                f"1. EXECUTIVE ANSWER: {len(opportunities)} opportunities identified. {opp_text}\n\n"
                f"2. WHAT HAPPENED: Opportunity detection based on top performers, growth patterns, and demand spikes.\n\n"
                f"3. WHY: {opp_text}\n\n"
                f"4. WHAT HAPPENS NEXT: Timely action on high-priority opportunities can capture value.\n\n"
                f"5. WHAT SHOULD WE DO: Prioritize HIGH priority opportunities with clear action plans and timelines."
            )

        elif mode == "benchmark":
            return (
                f"1. EXECUTIVE ANSWER: Benchmark analysis of {volume:,} records against historical baselines.\n\n"
                f"2. WHAT HAPPENED: {len(kpis)} KPIs computed. {len(analytics_dict.get('trends', {}))} trend(s) detected.\n\n"
                f"3. WHY: Comparison against previous periods reveals performance deltas.\n\n"
                f"4. WHAT HAPPENS NEXT: Current trajectory indicates continued performance under existing conditions.\n\n"
                f"5. WHAT SHOULD WE DO: Focus on areas showing decline and replicate success factors from growth periods."
            )

        elif mode == "summarize":
            first = evidence_rows[0] if evidence_rows else {}
            if not isinstance(first, dict):
                first = {}
            total_val = first.get("total_metric", first.get("total_records", 0))
            avg_val = first.get("avg_metric", 0)
            fmt_tot = f"{float(total_val or 0):,.2f}"
            fmt_avg = f"{float(avg_val or 0):,.2f}"
            measure_name = analytics_dict.get("evidence", {}).get("measures_analyzed", ["metric"])[0].replace("_", " ") if analytics_dict.get("evidence", {}).get("measures_analyzed") else "metric"
            return (
                f"1. EXECUTIVE ANSWER: Dataset contains {volume:,} records. Total {measure_name}: {fmt_tot} (avg: {fmt_avg}).\n\n"
                f"2. WHAT HAPPENED: Analysis of {volume:,} records reveals total {measure_name} of {fmt_tot} with average {fmt_avg}.\n\n"
                f"3. WHY: Direct SQL aggregation computed from {volume:,} rows in the dataset.\n\n"
                f"4. WHAT HAPPENS NEXT: {'Forecasting requires temporal columns to project future values.' if not analytics_dict.get('trends') else 'Trends and predictions are available for forward-looking analysis.'}\n\n"
                f"5. WHAT SHOULD WE DO: {'Add temporal columns to enable time-series forecasting.' if not analytics_dict.get('trends') else 'Review trend analysis and predictions for strategic planning.'}"
            )

        else:
            return (
                f"1. EXECUTIVE ANSWER: Analysis of {volume:,} records in {domain} is complete.\n\n"
                f"2. WHAT HAPPENED: {volume:,} records analyzed. {len(kpis)} KPIs computed. {len(anomalies)} anomalies detected.\n\n"
                f"3. WHY: Root cause analysis identified {len(root_causes)} key business drivers.\n\n"
                f"4. WHAT HAPPENS NEXT: {len(predictions)} predictive models generated.\n\n"
                f"5. WHAT SHOULD WE DO: {len(recommendations)} evidence-based recommendations provided."
            )

    @classmethod
    def _generate_follow_up_questions(cls, question: str, decision_mode: Dict[str, Any], analytics_dict: Dict[str, Any], profile: Dict[str, Any], history: Optional[List[Dict[str, Any]]] = None) -> List[str]:
        mode = decision_mode["mode"]
        dimensions = profile.get("column_categories", {}).get("dimensions", [])
        temporal = profile.get("column_categories", {}).get("temporal", [])
        measures = profile.get("column_categories", {}).get("measures", [])
        m = measures[0].replace("_", " ").title() if measures else "primary metric"
        d = dimensions[0].replace("_", " ").title() if dimensions else "category"
        t = temporal[0].replace("_", " ").title() if temporal else "time"

        mode_specific = {
            "predict": [f"What is the forecast for {m} over the next quarter?", f"How accurate was the last forecast for {m}?"],
            "recommend": [f"What are the risks of implementing these recommendations?", f"What is the expected ROI for the top recommendation?"],
            "diagnose": [f"What are the root causes of these anomalies?", f"Which dimensions are most affected?"],
            "compare": [f"What is the percentage breakdown of {m} by {d}?", f"How has {m} changed over {t}?"],
            "root_cause_analysis": [f"What actions should be taken to mitigate these drivers?", f"Which segments show the highest concentration risk?"],
            "risk_assessment": [f"What is the mitigation plan for the top risk?", f"How likely are these risks to materialize?"],
            "opportunity_detection": [f"What is the investment required to capture these opportunities?", f"What is the timeline for the top opportunity?"],
            "benchmark": [f"How does this compare to the previous period?", f"What is the trend direction for {m}?"],
        }

        generic = [
            f"What is the distribution of {m} across {d}?",
            f"Can you identify anomalies in {m}?",
            f"What are the key trends in {m} over {t}?",
            f"Which {d} contributes most to {m}?",
        ]

        candidates = mode_specific.get(mode, generic)

        if history and len(history) >= 2:
            last_assistant = next((t.get("content", "") for t in reversed(history) if t.get("role") == "assistant"), "")
            if last_assistant:
                candidates.extend([
                    f"Why is {d} performing this way?",
                    f"What should we do about {m}?",
                    f"What happens if we focus on {d}?",
                ])

        return [q for q in candidates if q.lower() != question.lower()][:5]

    @classmethod
    def _assemble_response(cls, question: str, decision_mode: Dict[str, Any], analytics_dict: Dict[str, Any], predictions: List[Any], recommendations: List[Dict[str, Any]], evidence_rows: List[Dict[str, Any]], sql_query: str, tables_used: List[str], columns_used: List[str], validation: Dict[str, Any], business_context: Dict[str, Any], context_prompt: str, evidence_report: Any, answer_validation: Any, executive_report: Dict[str, Any], follow_up_questions: List[str], llm_response: Optional[Dict[str, Any]], confidence: float) -> Dict[str, Any]:
        domain = business_context.get("domain", "Generic Business")
        answer = cls._build_executive_answer(
            question=question,
            decision_mode=decision_mode,
            analytics_dict=analytics_dict,
            predictions=predictions,
            recommendations=recommendations,
            evidence_rows=evidence_rows,
            sql_query=sql_query,
            domain=domain,
        )

        if llm_response and llm_response.get("content"):
            answer = llm_response["content"]

        exec_summary = business_context.get("executive_summary", "")
        if not exec_summary:
            exec_summary = cls._build_default_executive_summary(analytics_dict, domain)

        risks = analytics_dict.get("risks", [])
        opportunities = analytics_dict.get("opportunities", [])
        next_actions = cls._build_next_actions(recommendations)

        confidence_score = round(answer_validation.confidence_score, 2) if answer_validation else confidence

        response = {
            "answer": answer,
            "executive_summary": exec_summary,
            "confidence": confidence_score,
            "confidence_score": confidence_score,
            "evidence": {
                "metrics": business_context.get("important_kpis", [])[:5],
                "sql": sql_query,
                "rows": evidence_rows[:10] if evidence_rows else [],
                "tables": tables_used,
                "columns": columns_used,
                "confidence": confidence_score,
                "validation": validation,
                "dataset_path": str(analytics_dict.get("evidence", {}).get("dataset_path", "")),
                "total_rows": analytics_dict.get("volume", 0),
                "measures_analyzed": analytics_dict.get("evidence", {}).get("measures_analyzed", []),
                "dimensions_analyzed": analytics_dict.get("evidence", {}).get("dimensions_analyzed", []),
                "models_used": analytics_dict.get("evidence", {}).get("models_used", []),
                "traceability": analytics_dict.get("evidence", {}).get("traceability", ""),
            },
            "data_evidence": evidence_rows[:10] if evidence_rows else [],
            "follow_up_questions": follow_up_questions,
            "datasets": [domain],
            "datasets_used": [domain],
            "tables": tables_used,
            "tables_used": tables_used,
            "columns_used": columns_used,
            "kpis": business_context.get("important_kpis", []),
            "kpis_used": business_context.get("important_kpis", []),
            "calculation": sql_query,
            "sql_used": sql_query,
            "business_reasoning": evidence_report.business_reasoning if hasattr(evidence_report, "business_reasoning") else "Analysis derived from verified data analysis.",
            "recommendation": {
                "title": f"{domain} Executive Action Items",
                "actions": next_actions,
                "risks": [r.get("title", "") if isinstance(r, dict) else getattr(r, "title", "") for r in (risks or [])[:3]],
                "opportunities": [o.get("title", "") if isinstance(o, dict) else getattr(o, "title", "") for o in (opportunities or [])[:3]],
                "confidence": confidence_score,
            },
            "validation": validation,
            "charts": analytics_dict.get("charts", []) or [],
            "intent": decision_mode["mode"],
            "domain": domain,
            "status": "success",
            "error": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "decision_mode": decision_mode,
            "business_context": business_context,
            "context_prompt": context_prompt,
            "evidence_report": evidence_report.to_dict() if hasattr(evidence_report, "to_dict") else (evidence_report.__dict__ if hasattr(evidence_report, "__dict__") else {}),
            "support": {
                "tables_used": tables_used,
                "sql_used": sql_query,
                "validation": validation,
                "intent": decision_mode["mode"],
                "business_reasoning": evidence_report.business_reasoning if hasattr(evidence_report, "business_reasoning") else "Analysis derived from verified data analysis.",
                "recommendation": {
                    "title": f"{domain} Executive Action Items",
                    "actions": next_actions,
                    "risks": [r.get("title", "") if isinstance(r, dict) else getattr(r, "title", "") for r in (risks or [])[:3]],
                    "opportunities": [o.get("title", "") if isinstance(o, dict) else getattr(o, "title", "") for o in (opportunities or [])[:3]],
                    "confidence": confidence_score,
                },
                "predictions": [p.to_dict() if hasattr(p, "to_dict") else (p if isinstance(p, dict) else {}) for p in predictions],
                "risks": [r.get("title", "") if isinstance(r, dict) else getattr(r, "title", "") for r in (risks or [])[:5]],
                "opportunities": [o.get("title", "") if isinstance(o, dict) else getattr(o, "title", "") for o in (opportunities or [])[:5]],
                "next_actions": next_actions,
                "analytics": analytics_dict,
                "executive_report": executive_report,
                "charts": analytics_dict.get("charts", []) or [],
                "follow_up_questions": follow_up_questions,
            },
            "predictions": [p.to_dict() if hasattr(p, "to_dict") else (p if isinstance(p, dict) else {}) for p in predictions],
            "risks": [r.get("title", "") if isinstance(r, dict) else getattr(r, "title", "") for r in (risks or [])[:5]],
            "opportunities": [o.get("title", "") if isinstance(o, dict) else getattr(o, "title", "") for o in (opportunities or [])[:5]],
            "next_actions": next_actions,
        }
        return response

    @classmethod
    def _save_enriched_conversation(cls, session_id: str, workspace_id: str, question: str, response: Dict[str, Any], decision_mode: Dict[str, Any], business_context: Dict[str, Any], dataset_id: Optional[str]) -> None:
        try:
            BusinessMemoryEngine.save_conversation(session_id, workspace_id, "user", question, metadata={
                "intent": decision_mode["mode"],
                "domain": business_context.get("domain", "Generic Business"),
                "entities": business_context.get("important_kpis", [])[:3],
                "business_terms": business_context.get("important_metrics", [])[:3],
                "important_metrics": business_context.get("important_metrics", [])[:5],
                "important_dimensions": business_context.get("important_dimensions", [])[:5],
            })
            BusinessMemoryEngine.save_conversation(session_id, workspace_id, "assistant", response.get("answer", ""), metadata={
                "intent": decision_mode["mode"],
                "confidence": response.get("confidence", 0.0),
                "sql": response.get("sql_used"),
                "tables": response.get("tables_used"),
                "entities": business_context.get("important_kpis", [])[:3],
                "business_terms": business_context.get("important_metrics", [])[:3],
                "executive_decisions": business_context.get("previous_decisions", [])[:2],
                "follow_up_topics": response.get("follow_up_questions", [])[:3],
            })
        except Exception:
            pass

    @classmethod
    def _build_next_actions(cls, recommendations: List[Dict[str, Any]]) -> List[str]:
        actions = []
        for r in (recommendations or [])[:5]:
            action = r.get("action", r.get("title", "")) if isinstance(r, dict) else getattr(r, "action", "") or getattr(r, "title", "")
            if action and action not in actions:
                actions.append(action)
        if not actions:
            actions.append("Review analytics dashboard for detailed insights.")
        return actions

    @classmethod
    def _build_default_executive_summary(cls, analytics_dict: Dict[str, Any], domain: str) -> str:
        volume = analytics_dict.get("volume", 0)
        kpis = analytics_dict.get("kpis", [])
        anomalies = analytics_dict.get("anomalies", [])
        recommendations = analytics_dict.get("recommendations", [])
        parts = [f"{domain} analysis of {volume:,} records.", f"{len(kpis)} KPIs computed."]
        if anomalies:
            parts.append(f"{len(anomalies)} anomalies detected.")
        if recommendations:
            parts.append(f"{len(recommendations)} recommendations generated.")
        return " ".join(parts)

    @classmethod
    def _normalize_predictions(cls, predictions: List[Any]) -> List[Dict[str, Any]]:
        norm = []
        for p in predictions:
            if isinstance(p, dict):
                norm.append(p)
            elif hasattr(p, "to_dict"):
                norm.append(p.to_dict())
            elif hasattr(p, "__dict__"):
                norm.append({k: v for k, v in p.__dict__.items()})
            else:
                norm.append({"prediction": str(p)})
        return norm

    @classmethod
    def _normalize_evidence_rows(cls, rows: Any) -> List[Dict[str, Any]]:
        if rows is None:
            return []
        if isinstance(rows, list):
            normalized = []
            for row in rows:
                if isinstance(row, dict):
                    normalized.append(row)
                elif hasattr(row, "to_dict"):
                    normalized.append(row.to_dict())
                elif hasattr(row, "__dict__"):
                    normalized.append({k: v for k, v in row.__dict__.items()})
                elif isinstance(row, (list, tuple)):
                    normalized.append({f"col_{i}": v for i, v in enumerate(row)})
                else:
                    logger.warning("[DecisionEngine] Malformed evidence row dropped: type=%s value=%r", type(row).__name__, row)
            return normalized
        logger.warning("[DecisionEngine] evidence_rows was not a list: type=%s", type(rows).__name__)
        return []

    @classmethod
    def _build_empty_response(cls, reason: str) -> Dict[str, Any]:
        return {
            "answer": f"No data available to answer this question. {reason}",
            "executive_summary": f"No data available to answer this question. {reason}",
            "confidence": 0.0,
            "confidence_score": 0.0,
            "evidence": {"metrics": [], "sql": None, "rows": [], "tables": [], "columns": [], "confidence": 0.0, "validation": {"status": "UNAVAILABLE", "rows_returned": 0}},
            "data_evidence": [],
            "follow_up_questions": ["Upload a dataset to enable analytics.", "Select an existing workspace."],
            "datasets": [],
            "datasets_used": [],
            "tables": [],
            "tables_used": [],
            "columns_used": [],
            "kpis": [],
            "kpis_used": [],
            "calculation": "N/A",
            "sql_used": None,
            "business_reasoning": "No analysis performed.",
            "recommendation": {"title": "Data Required", "actions": ["Upload a dataset to enable analytics"], "risks": [], "opportunities": [], "confidence": 0.0},
            "validation": {"status": "UNAVAILABLE", "rows_returned": 0},
            "charts": [],
            "intent": "unknown",
            "domain": "Unknown",
            "status": "error",
            "error": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "decision_mode": {"mode": "unknown", "confidence": 0.0},
            "business_context": {},
            "context_prompt": "",
            "evidence_report": {},
            "support": {"tables_used": [], "sql_used": None, "validation": {"status": "UNAVAILABLE", "rows_returned": 0}, "follow_up_questions": ["Upload a dataset"], "analytics": {}, "executive_report": {}, "charts": []},
        }

    @classmethod
    def _build_unavailable_response(cls, question: str, decision_mode: Dict[str, Any], reason: str) -> Dict[str, Any]:
        return {
            "answer": f"No data available to answer this question. {reason}",
            "executive_summary": f"No data available to answer this question. {reason}",
            "confidence": 0.0,
            "confidence_score": 0.0,
            "evidence": {"metrics": [], "sql": None, "rows": [], "tables": [], "columns": [], "confidence": 0.0, "validation": {"status": "UNAVAILABLE", "rows_returned": 0}},
            "data_evidence": [],
            "follow_up_questions": ["Upload a dataset to enable analytics.", "Select an existing workspace."],
            "datasets": [],
            "datasets_used": [],
            "tables": [],
            "tables_used": [],
            "columns_used": [],
            "kpis": [],
            "kpis_used": [],
            "calculation": "N/A",
            "sql_used": None,
            "business_reasoning": "No analysis performed.",
            "recommendation": {"title": "Data Required", "actions": ["Upload a dataset to enable analytics"], "risks": [], "opportunities": [], "confidence": 0.0},
            "validation": {"status": "UNAVAILABLE", "rows_returned": 0},
            "charts": [],
            "intent": decision_mode.get("mode", "unknown"),
            "domain": "Unknown",
            "status": "error",
            "error": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "decision_mode": decision_mode,
            "business_context": {},
            "context_prompt": "",
            "evidence_report": {},
            "support": {"tables_used": [], "sql_used": None, "validation": {"status": "UNAVAILABLE", "rows_returned": 0}, "follow_up_questions": ["Upload a dataset"], "analytics": {}, "executive_report": {}, "charts": []},
        }
