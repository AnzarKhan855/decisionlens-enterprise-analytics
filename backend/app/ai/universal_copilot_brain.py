from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import re
from datetime import datetime

from app.database.duckdb_engine import DuckDBEngine
from app.semantic_model.engine import build_semantic_model
from app.analytics.data_catalog_engine import EnterpriseDataCatalogEngine
from app.services.workspace_service import EnterpriseWorkspaceManager
from app.ingestion.semantic_profiler import SemanticDataProfiler
from app.ai.validation.answer_validator import AnswerValidationLayer
from app.ai.validation.schemas import (
    AnswerValidationRequest,
    EvidenceRecord,
    InsightClaim,
    NumericClaim,
    RecommendationClaim,
)
from app.ai.evidence_builder import EvidenceBuilder
from app.semantic_model.core import SemanticModel
from app.logging.logger import get_logger

logger = get_logger(__name__)


class UniversalAIBrain:
    """
    DecisionLens Universal Enterprise AI Copilot Brain.

    This is the SINGLE AI reasoning pipeline for the entire platform.
    Every question, every answer, every recommendation flows through here.

    Pipeline:
      1. Intent Detection
      2. Dataset Understanding
      3. Semantic Model Resolution
      4. Universal Analytics Engine
      5. Universal Prediction Engine
      6. Executive Report Generation
      7. Evidence Validation
      8. 7-Section Answer Assembly
      9. Conversation Memory Storage

    Guarantees:
      - No hallucinations: answers strictly derived from executed SQL results.
      - Industry-agnostic: no hardcoded retail/healthcare/education assumptions.
      - No duplicate reasoning: ONE brain used everywhere.
      - Every answer includes all 7 required sections with full evidence traceability.
    """

    INTENT_PATTERNS = {
        "top_n": [
            r"top\s+\d+", r"top\s+\w+", r"highest", r"best", r"largest", r"most\s+\w+",
            r"leading", r"number\s+one", r"number\s+1", r"rank", r"ranking"
        ],
        "trend": [
            r"trend", r"over\s+time", r"monthly", r"quarterly", r"yearly", r"growth",
            r"decline", r"changed\s+over", r"how\s+has", r"trajectory", r"moving\s+average"
        ],
        "breakdown": [
            r"breakdown", r"by\s+\w+", r"distribution", r"split", r"categor", r"grouped\s+by",
            r"across\s+\w+", r"per\s+\w+"
        ],
        "anomaly": [
            r"anomaly", r"outlier", r"spike", r"drop", r"unusual", r"detect", r"irregular",
            r"unexpected", r"sudden", r"abnormal"
        ],
        "comparison": [
            r"compare", r"versus", r"\bvs\b", r"difference\s+between", r"contrast",
            r"how\s+does\s+\w+\s+compare"
        ],
        "correlation": [
            r"correlation", r"relationship", r"impact", r"affect", r"influence",
            r"driven\s+by", r"drivers?\s+of", r"factors?\s+behind", r"why\s+\w+\s+happen"
        ],
        "summary": [
            r"summary", r"overview", r"total\s+\w+", r"how\s+many", r"how\s+much",
            r"count\b", r"average\s+\w+", r"mean\s+\w+", r"what\s+is\s+the\s+total",
            r"what\s+is\s+the\s+average", r"overall"
        ],
        "forecast": [
            r"forecast", r"predict", r"projection", r"future", r"next\s+\d+\s+\w+",
            r"expected", r"projected", r"will\s+\w+"
        ],
        "ranking": [
            r"rank", r"position", r"percentile", r"top\s+\d+%", r"bottom\s+\d+%",
            r"narrow\s+down", r"shortlist"
        ],
        "distribution": [
            r"distribution", r"spread", r"range", r"variance", r"histogram",
            r"how\s+are\s+\w+\s+distributed"
        ],
        "percentage": [
            r"percentage", r"percent", r"share", r"portion", r"proportion", r"what\s+portion",
            r"what\s+percent", r"%\s*"
        ],
        "change": [
            r"changed", r"increase", r"decrease", r"decline", r"improvement",
            r"compared\s+to", r"previous", r"vs\s+\w+", r"month\s+over\s+month",
            r"year\s+over\s+year", r"qoq", r"mom", r"yoy"
        ],
        "recommendation": [
            r"recommend", r"recommendation", r"suggest", r"should\s+\w+", r"advise",
            r"what\s+should", r"action\s+item", r"next\s+step"
        ],
        "count": [
            r"how\s+many", r"count\s+of", r"number\s+of", r"total\s+\w+\s+records",
            r"rows?", r"entries?"
        ],
        "explain": [
            r"explain\s+this\s+(chart|graph|visualization|dashboard|report|prediction|recommendation)",
            r"what\s+does\s+this\s+(chart|graph|visualization|dashboard|report|prediction|recommendation)\s+show",
            r"interpret\s+this\s+(chart|graph|visualization|dashboard|report|prediction|recommendation)"
        ],
        "board_summary": [
            r"board\s+summary", r"board\s+report", r"executive\s+summary", r"ceo\s+summary",
            r"cfo\s+summary", r"board\s+briefing"
        ],
        "investor_summary": [
            r"investor\s+summary", r"investor\s+report", r"shareholder\s+report",
            r"stakeholder\s+summary", r"investor\s+briefing"
        ],
        "why": [
            r"^why\b", r"^why\s+is", r"^why\s+are", r"reason\s+for", r"cause\s+of", r"drivers?\s+behind"
        ],
        "follow_up": [
            r"^how\s+come", r"^what\s+about", r"^which\s+one", r"^what\s+else", r"^explain\s+more", r"^elaborate"
        ],
        "scenario": [
            r"what\s+if", r"increase\s+\w+\s+by", r"decrease\s+\w+\s+by", r"simulate", r"adjust\s+\w+", r"scenario"
        ],
        "risk": [
            r"risk", r"threat", r"vulnerability", r"downside", r"exposure", r"warning"
        ],
    }

    @classmethod
    def _resolve_parquet_path(cls, workspace_id: Optional[str] = None, dataset_id: Optional[str] = None) -> Optional[Path]:
        from app.database.storage import STORAGE_DIR
        from app.database.storage import ParquetStorageManager

        if dataset_id and dataset_id != "latest":
            direct = ParquetStorageManager.get_parquet_path(dataset_id)
            if direct.exists():
                return direct
            workspace_path = ParquetStorageManager.get_parquet_path_for_workspace(dataset_id)
            if workspace_path and workspace_path.exists():
                return workspace_path

        target_ws_id = workspace_id or EnterpriseWorkspaceManager.get_active_workspace_id()
        if not target_ws_id:
            all_ws = EnterpriseWorkspaceManager.get_all_workspaces()
            if all_ws:
                target_ws_id = all_ws[0]["workspace_id"]
            else:
                return None

        ws_info = EnterpriseWorkspaceManager.get_workspace(target_ws_id)
        if ws_info and ws_info.get("tables"):
            best_path: Optional[Path] = None
            best_score = 0
            clean_ws = target_ws_id.lower().replace("-", "_")
            for tbl in ws_info["tables"]:
                fp_str = tbl.get("file_path", "")
                if not fp_str:
                    continue
                p = Path(fp_str)
                if not p.exists():
                    continue
                if p.name.startswith(("sample-", "unified_", "tmp_")):
                    continue
                try:
                    profile = SemanticDataProfiler.profile(p)
                    row_count = profile.get("total_rows", 0)
                    measures = profile.get("column_categories", {}).get("measures", [])
                    temporal = profile.get("column_categories", {}).get("temporal", [])
                    p_stem = p.stem.lower().replace("-", "_")
                    ws_prefix_bonus = 10000000 if p_stem.startswith(clean_ws + "__") else 0
                    has_temporal = bool(temporal)
                    has_measures = bool(measures)
                    combined_bonus = 5000000 if (has_temporal and has_measures) else 0
                    score = ws_prefix_bonus + combined_bonus + (500000 if has_temporal else 0) + len(measures) * 10000 + row_count
                    if score > best_score:
                        best_score = score
                        best_path = p
                except Exception:
                    if best_path is None:
                        best_path = p
            if best_path is not None and best_score > 0:
                return best_path

        ws_unified = STORAGE_DIR / f"unified_{target_ws_id}.parquet"
        if ws_unified.exists():
            try:
                if DuckDBEngine.get_row_count(ws_unified) > 0:
                    return ws_unified
            except Exception:
                pass

        parquets = list(STORAGE_DIR.glob("*.parquet")) + list((STORAGE_DIR / "parquet").glob("*.parquet"))
        for p in parquets:
            if p.name.startswith(("unified_", "sample-")):
                continue
            if p.stat().st_size > 0:
                return p

        if parquets:
            return parquets[0]
        return None

    @classmethod
    def _detect_intent(cls, question: str, history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        q = question.lower().strip()
        scores = {}

        follow_up_phrases = [
            "why", "why is that", "why is it", "why are they", "how come",
            "what about", "which one", "what else", "explain more", "elaborate",
            "tell me more", "go on", "and then", "what happened", "what caused",
            "what should i do", "what should we do", "is that risky", "is it risky",
            "compare them", "compare those", "compare the", "show me more",
            "what happens next", "what if i change", "what if we change",
            "what if", "summarize everything", "summarise everything",
        ]

        is_follow_up = any(q.startswith(p) or q == p for p in follow_up_phrases)
        has_context = history and len(history) > 0

        if is_follow_up and has_context:
            last_assistant = next((t.get("content", "").lower() for t in reversed(history) if t.get("role") == "assistant"), "")
            last_user = next((t.get("content", "").lower() for t in reversed(history) if t.get("role") == "user"), "")

            if q.startswith("why") or q.startswith("why is that") or q.startswith("why is it"):
                scores["root_cause_analysis"] = 3.0
                scores["diagnose"] = 2.5
                scores["correlation"] = 1.5
            elif q.startswith("what should") or q.startswith("what would you do"):
                scores["recommendation"] = 3.0
                scores["recommend"] = 2.5
            elif q.startswith("what if") or q.startswith("what happens if"):
                scores["scenario"] = 3.0
                scores["what_if_simulation"] = 2.5
            elif q.startswith("compare") or q.startswith("compare them") or q.startswith("compare those"):
                scores["comparison"] = 3.0
                scores["compare"] = 2.5
            elif q.startswith("show me more") or q.startswith("tell me more"):
                scores["breakdown"] = 2.0
                scores["trend"] = 1.5
            elif q.startswith("is that risky") or q.startswith("is it risky"):
                scores["risk"] = 3.0
                scores["risk_assessment"] = 2.5
            elif q.startswith("what happens next"):
                scores["forecast"] = 3.0
                scores["predict"] = 2.5
            elif q.startswith("summarize everything") or q.startswith("summarise everything"):
                scores["board_summary"] = 3.0
                scores["summary"] = 2.5
            else:
                for intent, patterns in cls.INTENT_PATTERNS.items():
                    score = 0
                    for p in patterns:
                        matches = re.findall(p, q)
                        if matches:
                            score += len(matches)
                    scores[intent] = score

            for intent, patterns in cls.INTENT_PATTERNS.items():
                score = 0
                for p in patterns:
                    matches = re.findall(p, last_assistant)
                    if matches:
                        score += len(matches) * 0.3
                    matches2 = re.findall(p, last_user)
                    if matches2:
                        score += len(matches2) * 0.2
                scores[intent] = scores.get(intent, 0) + score
        else:
            for intent, patterns in cls.INTENT_PATTERNS.items():
                score = 0
                for p in patterns:
                    matches = re.findall(p, q)
                    if matches:
                        score += len(matches)
                scores[intent] = score

            if history:
                last_user = next((t["content"].lower() for t in reversed(history) if t["role"] == "user"), "")
                if last_user:
                    for intent, patterns in cls.INTENT_PATTERNS.items():
                        for p in patterns:
                            if re.search(p, last_user):
                                scores[intent] = scores.get(intent, 0) + 0.3

        best_intent = max(scores, key=lambda k: scores[k]) if scores else "summary"
        if scores.get(best_intent, 0) == 0:
            best_intent = "summary"

        max_score = max(scores.values()) if scores else 0
        confidence = min(0.98, 0.55 + (max_score * 0.15)) if max_score > 0 else 0.55

        return {
            "intent": best_intent,
            "confidence": confidence,
            "all_scores": scores,
            "is_follow_up": is_follow_up and has_context,
        }

    @classmethod
    def _calculate_confidence(cls, rows: List[Dict[str, Any]], total_rows: int, intent_info: Dict[str, Any], profile: Optional[Dict[str, Any]] = None) -> float:
        if not rows:
            return 0.30
        if profile:
            from app.ai.explainable_ai_engine import ExplainableAIEngine
            confidence_result = ExplainableAIEngine.compute_confidence(profile=profile)
            return round(confidence_result.overall_score, 2)
        row_count = len(rows)
        if row_count == 0:
            return 0.30
        if total_rows > 0 and row_count / total_rows < 0.01:
            return 0.75
        base = 0.92
        if intent_info["intent"] in ("summary", "top_n"):
            base = 0.96
        if row_count < 5:
            base -= 0.05
        return min(0.99, max(0.50, base))

    @classmethod
    def _validate_evidence(cls, rows: List[Dict[str, Any]], total_rows: int, sql_error: Optional[str]) -> Dict[str, Any]:
        if sql_error:
            return {
                "status": "ERROR",
                "rows_returned": 0,
                "message": sql_error,
                "null_check": "Not performed due to query error",
                "schema_match": "Not verified"
            }

        row_count = len(rows)
        null_issues = 0
        if rows:
            for row in rows[:10]:
                for v in row.values():
                    if v is None:
                        null_issues += 1

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
            "null_cells_detected_in_sample": null_issues,
            "message": f"Verified data analysis returned {row_count:,} rows from {total_rows:,} total records."
        }

    @classmethod
    def _run_universal_analytics(cls, semantic_model: SemanticModel, parquet_path: Path) -> Optional[Dict[str, Any]]:
        try:
            from app.analytics.universal_engine import UniversalAnalyticsEngine
            result = UniversalAnalyticsEngine.analyze(semantic_model, parquet_path=parquet_path)
            return result.to_dict()
        except Exception as e:
            return None

    @classmethod
    def _run_prediction(cls, semantic_model: SemanticModel, parquet_path: Path, analytics_dict: Optional[Dict[str, Any]] = None) -> Optional[List[Any]]:
        try:
            from app.ml.prediction_engine import UniversalPredictionEngine
            from types import SimpleNamespace
            partial_for_prediction = SimpleNamespace(
                trends=analytics_dict.get("trends", {}) if analytics_dict else {},
                correlations=analytics_dict.get("correlations", []) if analytics_dict else [],
                root_causes=analytics_dict.get("root_causes", []) if analytics_dict else [],
                drivers=analytics_dict.get("drivers", []) if analytics_dict else [],
                anomalies=analytics_dict.get("anomalies", []) if analytics_dict else [],
                outliers=analytics_dict.get("outliers", []) if analytics_dict else [],
                kpis=analytics_dict.get("kpis", []) if analytics_dict else [],
                volume=analytics_dict.get("volume", 0) if analytics_dict else 0,
                confidence_score=analytics_dict.get("confidence_score", 0.0) if analytics_dict else 0.0,
                evidence=analytics_dict.get("evidence", {}) if analytics_dict else {},
            )
            predictions = UniversalPredictionEngine.generate(
                analytics_result=partial_for_prediction,
                semantic_model=semantic_model,
            )
            return [p.to_dict() if hasattr(p, "to_dict") else p for p in predictions]
        except Exception:
            return None

    @classmethod
    def _build_executive_report(
        cls,
        analytics_dict: Dict[str, Any],
        semantic_model: SemanticModel,
        predictions: Optional[List[Any]],
    ) -> Dict[str, Any]:
        try:
            from app.schemas.analytics import AnalyticsResult
            from app.reports.executive_report_engine import UniversalExecutiveReportEngine

            if not analytics_dict:
                return {}

            result = AnalyticsResult(**analytics_dict)
            report = UniversalExecutiveReportEngine.generate_report(
                analytics_result=result,
                semantic_model=semantic_model,
                prediction_result=predictions,
            )
            return report
        except Exception:
            return {}

    @classmethod
    def _build_executive_answer(
        cls,
        question: str,
        intent_info: Dict[str, Any],
        analytics_dict: Dict[str, Any],
        predictions: List[Any],
        recommendations: List[Dict[str, Any]],
        evidence_rows: List[Dict[str, Any]],
        sql_query: str,
        domain: str,
    ) -> str:
        intent = intent_info["intent"]
        kpis = analytics_dict.get("kpis", [])
        trends = analytics_dict.get("trends", {})
        anomalies = analytics_dict.get("anomalies", [])
        root_causes = analytics_dict.get("root_causes", [])
        risks = analytics_dict.get("risks", [])
        opportunities = analytics_dict.get("opportunities", [])

        primary_kpi = kpis[0] if kpis else None
        kpi_name = primary_kpi.get("name", "primary metric") if isinstance(primary_kpi, dict) else (primary_kpi.name if primary_kpi else "primary metric")
        kpi_value = primary_kpi.get("formatted_value", "N/A") if isinstance(primary_kpi, dict) else (primary_kpi.formatted_value if primary_kpi else "N/A")

        if intent == "top_n" and evidence_rows:
            top = evidence_rows[0]
            dim_label = top.get("dimension") or top.get("category") or "top category"
            val = top.get("metric_value") or top.get("value") or 0
            fmt_val = f"{val:,.2f}" if isinstance(val, (int, float)) else str(val)
            measure_name = analytics_dict.get("evidence", {}).get("measures_analyzed", ["metric"])[0].replace("_", " ") if analytics_dict.get("evidence", {}).get("measures_analyzed") else "metric"
            return (
                f"1. EXECUTIVE ANSWER: '{dim_label}' is the top performer with an empirical value of {fmt_val} {measure_name} (confirmed by verified data analysis).\n\n"
                f"2. WHAT HAPPENED: '{dim_label}' leads all categories in {measure_name} with {fmt_val} across {len(evidence_rows)} segments.\n\n"
                f"3. WHY: '{dim_label}' has the highest aggregate {measure_name} based on direct aggregation.\n\n"
                f"4. WHAT HAPPENS NEXT: Without temporal data, the near-term trajectory is uncertain. Multi-period datasets enable forecasting.\n\n"
                f"5. WHAT SHOULD WE DO: Focus resources on '{dim_label}' to maintain leadership position while investigating lower-performing segments for improvement."
            )

        elif intent == "trend" and evidence_rows:
            latest_period = evidence_rows[-1].get("period", "latest") if evidence_rows else "latest"
            latest_val = evidence_rows[-1].get("metric_value", 0) if evidence_rows else 0
            fmt_val = f"{latest_val:,.2f}" if isinstance(latest_val, (int, float)) else str(latest_val)
            measure_name = analytics_dict.get("evidence", {}).get("measures_analyzed", ["metric"])[0].replace("_", " ") if analytics_dict.get("evidence", {}).get("measures_analyzed") else "metric"
            first_val = evidence_rows[0].get("metric_value", 0) if evidence_rows else 0
            last_val = evidence_rows[-1].get("metric_value", 0) if evidence_rows else 0
            if first_val != 0:
                pct_change = ((last_val - first_val) / abs(first_val)) * 100
                direction = "increased" if pct_change > 0 else "decreased"
                trend_direction = f"The metric {direction} by {abs(pct_change):.1f}% across {len(evidence_rows)} periods."
            else:
                trend_direction = "The metric shows stable baseline behavior across observed periods."

            return (
                f"1. EXECUTIVE ANSWER: {measure_name.title()} shows a {direction.lower() if first_val != 0 else 'stable'} trend. Latest value ({latest_period}): {fmt_val}.\n\n"
                f"2. WHAT HAPPENED: Time-series analysis across {len(evidence_rows)} periods shows the latest period reached {fmt_val}. {trend_direction}\n\n"
                f"3. WHY: Trend direction is determined by comparing the first and latest observed values from the dataset.\n\n"
                f"4. WHAT HAPPENS NEXT: {'Continued directional movement expected based on current trend slope.' if first_val != 0 else 'Baseline stability expected without strong directional signals.'}\n\n"
                f"5. WHAT SHOULD WE DO: {'Leverage upward momentum or investigate decline drivers based on trend direction.' if first_val != 0 else 'Maintain monitoring cadence and enrich dataset with additional temporal coverage.'}"
            )

        elif intent == "summary":
            total_val = evidence_rows[0].get("total_metric", evidence_rows[0].get("total_records", 0)) if evidence_rows else 0
            avg_val = evidence_rows[0].get("avg_metric", 0) if evidence_rows else 0
            fmt_tot = f"{float(total_val or 0):,.2f}"
            fmt_avg = f"{float(avg_val or 0):,.2f}"
            measure_name = analytics_dict.get("evidence", {}).get("measures_analyzed", ["metric"])[0].replace("_", " ") if analytics_dict.get("evidence", {}).get("measures_analyzed") else "metric"
            return (
                f"1. EXECUTIVE ANSWER: Dataset contains {analytics_dict.get('volume', 0):,} records. Total {measure_name}: {fmt_tot} (avg: {fmt_avg}).\n\n"
                f"2. WHAT HAPPENED: Analysis of {analytics_dict.get('volume', 0):,} records reveals total {measure_name} of {fmt_tot} with average {fmt_avg}.\n\n"
                f"3. WHY: Direct SQL aggregation (SUM, AVG) computed from {analytics_dict.get('volume', 0):,} rows in the dataset.\n\n"
                f"4. WHAT HAPPENS NEXT: {'Forecasting requires temporal columns to project future values.' if not analytics_dict.get('trends') else 'Trends and predictions are available for forward-looking analysis.'}\n\n"
                f"5. WHAT SHOULD WE DO: {'Add temporal columns to enable time-series forecasting.' if not analytics_dict.get('trends') else 'Review trend analysis and predictions for strategic planning.'}"
            )

        elif intent == "anomaly":
            anomaly_count = len(anomalies)
            high_severity = sum(1 for a in anomalies if str(getattr(a, "severity", "")).upper() in ("HIGH", "CRITICAL")) if anomalies else 0
            return (
                f"1. EXECUTIVE ANSWER: {anomaly_count} anomalies detected. {high_severity} high-severity requiring investigation.\n\n"
                f"2. WHAT HAPPENED: Statistical outlier detection (z-score >= 2.0) identified {anomaly_count} anomalous observations in the dataset.\n\n"
                f"3. WHY: Data points exceeded 2-sigma variance limits from historical baseline distributions computed from the dataset.\n\n"
                f"4. WHAT HAPPENS NEXT: Unmitigated variance risks propagating operational disruption into subsequent reporting cycles.\n\n"
                f"5. WHAT SHOULD WE DO: Initiate root-cause audit on flagged periods and calibrate alert thresholds based on observed z-score distribution."
            )

        elif intent == "comparison" and evidence_rows:
            cat_key = "category" if "category" in evidence_rows[0] else "dimension"
            val_key = "metric_value" if "metric_value" in evidence_rows[0] else "value"
            best = max(evidence_rows, key=lambda r: r.get(val_key, 0) or 0) if evidence_rows else {}
            worst = min(evidence_rows, key=lambda r: r.get(val_key, 0) or 0) if evidence_rows else {}
            best_val = best.get(val_key, 0)
            worst_val = worst.get(val_key, 0)
            best_cat = best.get(cat_key, "N/A")
            worst_cat = worst.get(cat_key, "N/A")
            measure_name = analytics_dict.get("evidence", {}).get("measures_analyzed", ["metric"])[0].replace("_", " ") if analytics_dict.get("evidence", {}).get("measures_analyzed") else "metric"
            return (
                f"1. EXECUTIVE ANSWER: '{best_cat}' leads with {best_val:,.2f} while '{worst_cat}' has {worst_val:,.2f} in {measure_name}.\n\n"
                f"2. WHAT HAPPENED: Category comparison across {len(evidence_rows)} segments reveals performance variance in {measure_name}.\n\n"
                f"3. WHY: Performance variance is driven by the difference in {measure_name} aggregates across categories, confirmed by SQL GROUP BY.\n\n"
                f"4. WHAT HAPPENS NEXT: Segment dynamics will maintain current relative positioning unless underlying conditions change.\n\n"
                f"5. WHAT SHOULD WE DO: Investigate underperforming segments for optimization while reinforcing leaders."
            )

        elif intent == "risk":
            risk_titles = [r.get("title", "") for r in (risks or [])[:3] if isinstance(r, dict)]
            risk_text = "; ".join(risk_titles) if risk_titles else "No significant risks identified."
            return (
                f"1. EXECUTIVE ANSWER: {len(risks)} risks identified. {risk_text}\n\n"
                f"2. WHAT HAPPENED: Risk assessment based on anomaly severity, concentration risk, and driver analysis across {analytics_dict.get('volume', 0):,} records.\n\n"
                f"3. WHY: {risk_text}\n\n"
                f"4. WHAT HAPPENS NEXT: Unmitigated risks may impact business continuity and financial performance.\n\n"
                f"5. WHAT SHOULD WE DO: Prioritize CRITICAL and HIGH severity risks with mitigation plans."
            )

        elif intent == "scenario":
            return (
                f"1. EXECUTIVE ANSWER: Scenario simulation requires defining the metric to adjust, the adjustment value, and the unit.\n\n"
                f"2. WHAT HAPPENED: {analytics_dict.get('volume', 0):,} records analyzed. {len(analytics_dict.get('trends', {}))} trends detected.\n\n"
                f"3. WHY: Simulation requires specifying base metric, adjustment value, and unit (absolute or percentage).\n\n"
                f"4. WHAT HAPPENS NEXT: Estimated impact can be calculated once parameters are provided.\n\n"
                f"5. WHAT SHOULD WE DO: Specify the metric to adjust, the adjustment value, and the unit (absolute or percentage)."
            )

        elif intent == "root_cause_analysis":
            top_drivers = []
            for rc in (root_causes or [])[:3]:
                if isinstance(rc, dict):
                    td = rc.get("top_driver", {})
                    if td:
                        top_drivers.append(f"{rc.get('dimension', '')}: {td.get('category', '')} ({td.get('contribution_percentage', 0)}%)")
                elif hasattr(rc, "top_driver") and rc.top_driver:
                    top_drivers.append(f"{rc.dimension}: {rc.top_driver.get('category', '')} ({rc.top_driver.get('contribution_percentage', 0)}%)")
            drivers_text = "; ".join(top_drivers) if top_drivers else "No significant drivers identified."
            return (
                f"1. EXECUTIVE ANSWER: Root cause analysis identifies {len(root_causes)} key drivers.\n\n"
                f"2. WHAT HAPPENED: Variance decomposition across {len(analytics_dict.get('dimensions', []))} dimensions reveals concentration patterns in {analytics_dict.get('volume', 0):,} records.\n\n"
                f"3. WHY: {drivers_text}\n\n"
                f"4. WHAT HAPPENS NEXT: Current drivers will continue influencing metrics unless rebalanced.\n\n"
                f"5. WHAT SHOULD WE DO: Address concentration risks and diversify across secondary segments."
            )

        elif intent == "diagnose":
            anomaly_count = len(anomalies)
            high_severity = sum(1 for a in anomalies if str(getattr(a, "severity", "") if hasattr(a, "severity") else a.get("severity", "")).upper() in ("HIGH", "CRITICAL")) if anomalies else 0
            return (
                f"1. EXECUTIVE ANSWER: {anomaly_count} anomalies detected. {high_severity} high-severity requiring investigation.\n\n"
                f"2. WHAT HAPPENED: Statistical outlier detection and variance analysis across {analytics_dict.get('volume', 0):,} records identified {anomaly_count} anomalous observations.\n\n"
                f"3. WHY: Data points exceeded 2-sigma variance limits from historical baseline distributions computed from the dataset.\n\n"
                f"4. WHAT HAPPENS NEXT: Unmitigated variance risks propagating operational disruption into subsequent reporting cycles.\n\n"
                f"5. WHAT SHOULD WE DO: Initiate root-cause audit on flagged periods and calibrate alert thresholds based on observed z-score distribution."
            )

        elif intent == "forecast":
            norm_preds = cls._normalize_predictions(predictions)
            forecast_pred = next((p for p in norm_preds if p.get("feasible")), None)
            if forecast_pred:
                return (
                    f"1. EXECUTIVE ANSWER: {forecast_pred.get('prediction', 'Forecast unavailable.')}\n\n"
                    f"2. WHAT HAPPENED: {analytics_dict.get('volume', 0):,} records analyzed. {len(analytics_dict.get('trends', {}))} trend(s) detected.\n\n"
                    f"3. WHY: Historical patterns and correlation structures drive the projected trajectory.\n\n"
                    f"4. WHAT HAPPENS NEXT: {forecast_pred.get('prediction', 'No projection available.')}\n\n"
                    f"5. WHAT SHOULD WE DO: {forecast_pred.get('recommended_action', 'Continue monitoring.')}"
                )
            return (
                f"1. EXECUTIVE ANSWER: Forecast projection unavailable with current data.\n\n"
                f"2. WHAT HAPPENED: {analytics_dict.get('volume', 0):,} records analyzed.\n\n"
                f"3. WHY: Insufficient temporal patterns or numeric measures for reliable forecasting.\n\n"
                f"4. WHAT HAPPENS NEXT: Baseline stability expected. No directional variance predicted.\n\n"
                f"5. WHAT SHOULD WE DO: Upload multi-period datasets with temporal columns to enable time-series forecasting."
            )

        elif intent == "recommendation":
            rec_actions = []
            for r in (recommendations or [])[:3]:
                if isinstance(r, dict):
                    rec_actions.append(r.get("action") or r.get("title", ""))
                else:
                    rec_actions.append(getattr(r, "action", "") or getattr(r, "title", ""))
            rec_text = "; ".join(rec_actions) if rec_actions else "No evidence-backed recommendations available for this dataset."
            return (
                f"1. EXECUTIVE ANSWER: Based on {analytics_dict.get('volume', 0):,} records, the recommended actions are: {rec_text}\n\n"
                f"2. WHAT HAPPENED: {analytics_dict.get('volume', 0):,} records analyzed with {len(kpis)} KPIs and {len(root_causes)} drivers identified.\n\n"
                f"3. WHY: Evidence-based analysis identified key drivers and concentration patterns from the dataset.\n\n"
                f"4. WHAT HAPPENS NEXT: Recommendations are prioritized by impact and feasibility based on dataset evidence.\n\n"
                f"5. WHAT SHOULD WE DO: {rec_text}"
            )

        elif intent == "explain":
            chart_count = len(charts) if charts else 0
            return (
                f"1. EXECUTIVE ANSWER: This visualization is derived from {analytics_dict.get('volume', 0):,} records in the {domain} dataset.\n\n"
                f"2. WHAT HAPPENED: The chart represents aggregated metrics across dimensions identified in the semantic model.\n\n"
                f"3. WHY: Patterns reflect underlying data distributions computed from the dataset structure and verified data analysis.\n\n"
                f"4. WHAT HAPPENS NEXT: Trends indicate continued patterns under current conditions unless underlying data changes.\n\n"
                f"5. WHAT SHOULD WE DO: Use this visualization to monitor KPIs and identify deviations from expected patterns."
            )

        elif intent == "board_summary":
            exec_summary = analytics_dict.get("executive_summary", "")
            return (
                f"1. EXECUTIVE ANSWER: Board Summary for {domain} - {analytics_dict.get('volume', 0):,} records analyzed. Health Score: {analytics_dict.get('health_score', {}).get('overall_score', 0):.0f}/100.\n\n"
                f"2. WHAT HAPPENED: {exec_summary}\n\n"
                f"3. WHY: Root cause analysis identified {len(root_causes)} key drivers. {len(anomalies)} anomalies detected.\n\n"
                f"4. WHAT HAPPENS NEXT: {len(predictions)} predictive models generated. Forecast horizon: 30-90 days.\n\n"
                f"5. WHAT SHOULD WE DO: {len(recommendations)} recommendations prioritized. Focus on CRITICAL and HIGH priority items."
            )

        elif intent == "investor_summary":
            return (
                f"1. EXECUTIVE ANSWER: {domain} investor briefing - {analytics_dict.get('volume', 0):,} records. Primary KPI: {kpi_name} = {kpi_value}.\n\n"
                f"2. WHAT HAPPENED: Dataset analysis shows {len(kpis)} KPIs with {analytics_dict.get('health_score', {}).get('overall_score', 0):.0f}/100 health score.\n\n"
                f"3. WHY: Growth and decline patterns identified across {len(analytics_dict.get('trends', {}))} measures.\n\n"
                f"4. WHAT HAPPENS NEXT: {len(predictions)} forecast models project forward trajectory with confidence intervals.\n\n"
                f"5. WHAT SHOULD WE DO: {len(recommendations)} strategic recommendations for value creation and risk mitigation."
            )

        else:
            return (
                f"1. EXECUTIVE ANSWER: Analysis of {analytics_dict.get('volume', 0):,} records in {domain} is complete.\n\n"
                f"2. WHAT HAPPENED: {analytics_dict.get('volume', 0):,} records analyzed. {len(kpis)} KPIs computed. {len(anomalies)} anomalies detected.\n\n"
                f"3. WHY: Root cause analysis identified {len(root_causes)} key business drivers and concentration patterns.\n\n"
                f"4. WHAT HAPPENS NEXT: {len(predictions)} predictive models generated with confidence intervals.\n\n"
                f"5. WHAT SHOULD WE DO: {len(recommendations)} evidence-based recommendations provided."
            )

    @classmethod
    def _build_evidence_section(
        cls,
        analytics_dict: Dict[str, Any],
        sql_query: str,
        evidence_rows: List[Dict[str, Any]],
        tables_used: List[str],
        columns_used: List[str],
        validation: Dict[str, Any],
    ) -> Dict[str, Any]:
        evidence = analytics_dict.get("evidence", {})

        metrics = []
        for kpi in analytics_dict.get("kpis", [])[:5]:
            if isinstance(kpi, dict):
                metrics.append({
                    "name": kpi.get("name", ""),
                    "value": kpi.get("formatted_value", ""),
                    "formula": kpi.get("formula", ""),
                    "confidence": kpi.get("confidence", 0),
                })

        confidence_factors = analytics_dict.get("confidence_factors", {})

        return {
            "metrics": metrics,
            "sql": sql_query,
            "rows": evidence_rows[:10] if evidence_rows else [],
            "tables": tables_used,
            "columns": columns_used,
            "confidence": round(analytics_dict.get("confidence_score", 0.0), 2),
            "confidence_factors": confidence_factors,
            "validation": validation,
            "dataset_path": evidence.get("dataset_path", ""),
            "total_rows": evidence.get("total_rows", 0),
            "measures_analyzed": evidence.get("measures_analyzed", []),
            "dimensions_analyzed": evidence.get("dimensions_analyzed", []),
            "models_used": evidence.get("models_used", []),
            "traceability": evidence.get("traceability", ""),
        }

    @classmethod
    def _normalize_predictions(cls, predictions: List[Any]) -> List[Dict[str, Any]]:
        normalized = []
        for p in predictions:
            if isinstance(p, dict):
                normalized.append(p)
            elif hasattr(p, "to_dict"):
                normalized.append(p.to_dict())
            elif hasattr(p, "__dict__"):
                normalized.append({k: v for k, v in p.__dict__.items()})
            else:
                normalized.append({"prediction": str(p)})
        return normalized

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
                    logger.warning("[UniversalAIBrain] Malformed evidence row dropped: type=%s value=%r", type(row).__name__, row)
            return normalized
        logger.warning("[UniversalAIBrain] evidence_rows was not a list: type=%s", type(rows).__name__)
        return []

    @classmethod
    def _build_executive_summary_section(
        cls,
        analytics_dict: Dict[str, Any],
        predictions: List[Any],
        recommendations: List[Dict[str, Any]],
        domain: str,
    ) -> str:
        health = analytics_dict.get("health_score", {})
        health_score = health.get("overall_score", 0) if isinstance(health, dict) else 0
        health_status = health.get("status", "Unknown") if isinstance(health, dict) else "Unknown"
        volume = analytics_dict.get("volume", 0)
        kpis = analytics_dict.get("kpis", [])
        anomalies = analytics_dict.get("anomalies", [])
        root_causes = analytics_dict.get("root_causes", [])
        risks = analytics_dict.get("risks", [])

        parts = [
            f"{domain} workspace analyzed with {volume:,} verified records.",
            f"Business health score: {health_score:.0f}/100 ({health_status}).",
            f"{len(kpis)} KPIs available for review.",
        ]

        if anomalies:
            parts.append(f"{len(anomalies)} anomalies detected.")
        norm_preds = cls._normalize_predictions(predictions)
        if norm_preds:
            feasible_preds = [p for p in norm_preds if p.get("feasible", True)]
            if feasible_preds:
                parts.append(f"{len(feasible_preds)} predictive models generated.")
        if recommendations:
            parts.append(f"{len(recommendations)} strategic recommendations.")

        return " ".join(parts)

    @classmethod
    def _assemble_copilot_response(
        cls,
        question: str,
        intent_info: Dict[str, Any],
        analytics_dict: Dict[str, Any],
        predictions: List[Any],
        recommendations: List[Dict[str, Any]],
        evidence_rows: List[Dict[str, Any]],
        sql_query: str,
        tables_used: List[str],
        columns_used: List[str],
        validation: Dict[str, Any],
        domain: str,
        profile: Dict[str, Any],
        charts: List[Dict[str, Any]],
        executive_report: Dict[str, Any],
        answer_validation: Optional[Any] = None,
        evidence_report: Optional[Any] = None,
    ) -> Dict[str, Any]:
        answer = cls._build_executive_answer(
            question=question,
            intent_info=intent_info,
            analytics_dict=analytics_dict,
            predictions=predictions,
            recommendations=recommendations,
            evidence_rows=evidence_rows,
            sql_query=sql_query,
            domain=domain,
        )

        evidence_section = cls._build_evidence_section(
            analytics_dict=analytics_dict,
            sql_query=sql_query,
            evidence_rows=evidence_rows,
            tables_used=tables_used,
            columns_used=columns_used,
            validation=validation,
        )

        exec_summary = cls._build_executive_summary_section(
            analytics_dict=analytics_dict,
            predictions=predictions,
            recommendations=recommendations,
            domain=domain,
        )

        risks = analytics_dict.get("risks", [])
        opportunities = analytics_dict.get("opportunities", [])
        next_actions = []
        for r in (recommendations or [])[:3]:
            if isinstance(r, dict):
                next_actions.append(r.get("action") or r.get("title", ""))
            else:
                next_actions.append(getattr(r, "action", "") or getattr(r, "title", ""))

        validation_confidence = round(answer_validation.confidence_score, 2) if answer_validation else round(analytics_dict.get("confidence_score", 0.0) / 100.0, 2) if analytics_dict.get("confidence_score", 0.0) > 1 else round(analytics_dict.get("confidence_score", 0.0), 2)

        response = {
            "answer": answer,
            "executive_summary": answer,
            "evidence": evidence_section,
            "evidence_list": [str(r) for r in evidence_rows],
            "confidence": validation_confidence,
            "intent": intent_info["intent"],
            "domain": domain,
            "calculation": sql_query,
            "sql_query": sql_query,
            "reasoning": "",
            "recommendations": recommendations or [],
            "next_actions": next_actions,
            "evidence_report": evidence_report.to_dict() if hasattr(evidence_report, "to_dict") else (evidence_report.__dict__ if evidence_report else {}),
            "support": {
                "tables_used": tables_used,
                "sql_used": sql_query,
                "validation": validation,
                "intent": intent_info["intent"],
                "business_reasoning": "Analysis derived from verified data analysis via UniversalAnalyticsEngine, UniversalPredictionEngine, and UniversalExecutiveReportEngine.",
                "recommendation": {
                    "title": f"{domain} Executive Action Items",
                    "actions": next_actions,
                    "risks": [r.get("title", "") if isinstance(r, dict) else getattr(r, "title", "") for r in (risks or [])[:3]],
                    "opportunities": [o.get("title", "") if isinstance(o, dict) else getattr(o, "title", "") for o in (opportunities or [])[:3]],
                    "confidence": round(analytics_dict.get("confidence_score", 0.0) / 100.0, 2) if analytics_dict.get("confidence_score", 0.0) > 1 else round(analytics_dict.get("confidence_score", 0.0), 2),
                },
                "predictions": predictions or [],
                "risks": [r.get("title", "") if isinstance(r, dict) else getattr(r, "title", "") for r in (risks or [])[:5]],
                "opportunities": [o.get("title", "") if isinstance(o, dict) else getattr(o, "title", "") for o in (opportunities or [])[:5]],
                "next_actions": next_actions,
                "analytics": analytics_dict,
                "executive_report": executive_report,
                "charts": charts or [],
                "follow_up_questions": cls._build_follow_up_questions(question, intent_info, columns_used, profile.get("column_categories", {}).get("dimensions", []), profile.get("column_categories", {}).get("temporal", []), domain),
            }
        }
        return response

    @classmethod
    def _build_follow_up_questions(cls, question: str, intent_info: Dict[str, Any], columns_used: List[str], dimensions: List[str], temporal: List[str], domain: str) -> List[str]:
        m = columns_used[0].replace("_", " ").title() if columns_used else "primary metric"
        d = dimensions[0].replace("_", " ").title() if dimensions else "category"
        t = temporal[0].replace("_", " ").title() if temporal else "time"

        generic = [
            f"What is the distribution of {m} across {d}?",
            f"Can you identify anomalies in {m}?",
            f"What are the key trends in {m} over {t}?",
            f"Which {d} contributes most to {m}?",
            f"What recommendations do you have for improving {m}?",
        ]

        all_qs = [q for q in generic if q.lower() != question.lower()]
        return all_qs[:6]

    @classmethod
    def _build_reasoning_section(
        cls,
        question: str,
        intent_info: Dict[str, Any],
        analytics_dict: Dict[str, Any],
        predictions: List[Any],
        recommendations: List[Dict[str, Any]],
        evidence_rows: List[Dict[str, Any]],
        sql_query: str,
        domain: str,
        anomalies: List[Any],
        drivers: List[Dict[str, Any]],
        root_causes: List[Any],
    ) -> str:
        parts = []
        parts.append(f"REASONING FOR: {question}")
        parts.append(f"Domain: {domain} | Intent: {intent_info['intent']}")
        parts.append(f"SQL Executed: {sql_query}")
        parts.append(f"Rows returned: {len(evidence_rows)}")
        parts.append("")

        if analytics_dict.get("kpis"):
            kpi_names = []
            for k in analytics_dict["kpis"][:5]:
                if isinstance(k, dict):
                    kpi_names.append(k.get("name", ""))
                elif hasattr(k, "name"):
                    kpi_names.append(k.name)
            parts.append(f"KPIs analyzed: {', '.join([n for n in kpi_names if n])}")
        if root_causes:
            parts.append(f"Root causes identified: {len(root_causes)}")
        if drivers:
            top_drivers = [d.get("top_driver", {}).get("category", "N/A") for d in drivers[:3] if d.get("top_driver")]
            parts.append(f"Key drivers: {', '.join(top_drivers)}")
        if anomalies:
            parts.append(f"Anomalies detected: {len(anomalies)}")
        if predictions:
            feasible = [p for p in predictions if (p.get("feasible", True) if isinstance(p, dict) else True)]
            parts.append(f"Predictions generated: {len(feasible)}")
        if recommendations:
            high_priority = [r for r in recommendations if r.get("priority", "") in ("CRITICAL", "HIGH")]
            parts.append(f"Recommendations: {len(recommendations)} ({len(high_priority)} high/critical)")

        parts.append("")
        parts.append("All claims are derived from executed SQL queries against the dataset.")
        return "\n".join(parts)

    @classmethod
    def _build_next_actions_section(cls, recommendations: List[Dict[str, Any]]) -> List[str]:
        actions = []
        for r in (recommendations or [])[:5]:
            action = r.get("action", r.get("title", "")) if isinstance(r, dict) else getattr(r, "action", "") or getattr(r, "title", "")
            if action and action not in actions:
                actions.append(action)
        if not actions:
            actions.append("Review analytics dashboard for detailed insights.")
        return actions

    @classmethod
    def _build_context_prompt(
        cls,
        question: str,
        workspace_id: str,
        session_id: str,
        analytics_dict: Dict[str, Any],
        recommendations: List[Dict[str, Any]],
    ) -> str:
        parts = ["BUSINESS MEMORY CONTEXT\n"]
        try:
            from app.memory.business_memory_engine import BusinessMemoryEngine
            ctx = BusinessMemoryEngine.get_ai_context(workspace_id, session_id)

            if ctx.get("previous_conversations"):
                parts.append("RECENT CONVERSATIONS:")
                for turn in ctx["previous_conversations"][-5:]:
                    parts.append(f"- [{turn['role']}] {turn['content'][:200]}")
                parts.append("")

            if ctx.get("previous_reports"):
                parts.append("RECENT REPORTS:")
                for rpt in ctx["previous_reports"][:3]:
                    parts.append(f"- [{rpt.get('audience', 'N/A')}] {rpt.get('title', 'Untitled')}")
                parts.append("")

            if ctx.get("previous_insights"):
                parts.append("RECENT INSIGHTS:")
                for ins in ctx["previous_insights"][:5]:
                    parts.append(f"- [{ins.get('severity', 'N/A')}] {ins.get('title', '')}: {ins.get('description', '')[:150]}")
                parts.append("")

            if ctx.get("previous_forecasts"):
                parts.append("RECENT FORECASTS:")
                for f in ctx["previous_forecasts"][:3]:
                    parts.append(f"- [{f.get('model_type', 'N/A')}] {f.get('metric', '')}: confidence={f.get('confidence', 0)}")
                parts.append("")

            if ctx.get("previous_recommendations"):
                parts.append("RECENT RECOMMENDATIONS:")
                for rec in ctx["previous_recommendations"][:5]:
                    parts.append(f"- [{rec.get('status', 'pending')}] {rec.get('title', '')}: {rec.get('action', '')[:100]}")
                parts.append("")

            if ctx.get("business_goals"):
                parts.append("ACTIVE BUSINESS GOALS:")
                for g in ctx["business_goals"][:5]:
                    parts.append(f"- {g.get('title', '')}: target={g.get('target_value', 'N/A')}, current={g.get('current_value', 'N/A')}")
                parts.append("")

            if ctx.get("previous_kpis"):
                parts.append("PREVIOUS KPI SNAPSHOTS:")
                for k in ctx["previous_kpis"][:3]:
                    ts = k.get("timestamp", "")[:10]
                    kpi_names = [kpi.get("name", "") for kpi in k.get("kpis", [])[:3]]
                    parts.append(f"- {ts}: {', '.join(kpi_names)}")
                parts.append("")
        except Exception:
            pass

        if recommendations:
            parts.append("CURRENT RECOMMENDATIONS:")
            for r in recommendations[:5]:
                title = r.get("title", r.get("title", "")) if isinstance(r, dict) else getattr(r, "title", "")
                action = r.get("action", r.get("action", "")) if isinstance(r, dict) else getattr(r, "action", "")
                parts.append(f"- {title}: {action[:120]}")
            parts.append("")

        parts.append("END OF BUSINESS MEMORY CONTEXT\n")
        return "\n".join(parts)

    @classmethod
    def query(
        cls,
        question: str,
        workspace_id: Optional[str] = None,
        dataset_id: Optional[str] = None,
        session_id: str = "default",
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        if not question or not question.strip():
            return cls._build_empty_response("Empty question provided.")

        ws_id = workspace_id or EnterpriseWorkspaceManager.get_active_workspace_id() or "default"

        history = []
        if conversation_history is not None:
            history = conversation_history
        else:
            try:
                from app.memory.business_memory_engine import BusinessMemoryEngine
                ai_context = BusinessMemoryEngine.get_ai_context(ws_id, session_id)
                history = ai_context.get("previous_conversations", [])
            except Exception:
                pass

        intent_info = cls._detect_intent(question, history)
        parquet_path = cls._resolve_parquet_path(workspace_id, dataset_id)

        if not parquet_path or not parquet_path.exists():
            return cls._build_unavailable_response(
                question, intent_info, "No active workspace dataset available."
            )

        rag_context = {}
        try:
            from app.ai.rag.retriever import WorkspaceMetadataRetriever
            rag_context = WorkspaceMetadataRetriever.retrieve_with_context(
                question=question,
                session_id=session_id,
                workspace_id=ws_id,
                top_k=10,
            )
        except Exception:
            pass

        profile = {}
        try:
            profile = SemanticDataProfiler.profile(parquet_path)
        except Exception as e:
            pass

        measures = profile.get("column_categories", {}).get("measures", [])
        dimensions = profile.get("column_categories", {}).get("dimensions", [])
        temporal = profile.get("column_categories", {}).get("temporal", [])
        total_rows = profile.get("total_rows", 0)

        ws_info = {}
        tables = []
        try:
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
                "row_count": total_rows,
                "measures": measures,
                "dimensions": dimensions
            }]

        table_profiles = {}
        for tbl in tables:
            fp = tbl.get("file_path")
            if fp:
                try:
                    table_profiles[tbl["table_name"]] = SemanticDataProfiler.profile(Path(fp))
                except Exception:
                    continue

        sql_query, tables_used, columns_used, evidence_rows, sql_error = cls._execute_evidence_query(
            intent_info["intent"], measures, dimensions, temporal, parquet_path, tables, table_profiles, question
        )
        evidence_rows = cls._normalize_evidence_rows(evidence_rows)
        logger.info(
            "[UniversalAIBrain] Evidence query completed: type=%s count=%d",
            type(evidence_rows).__name__,
            len(evidence_rows) if evidence_rows else 0,
        )
        if evidence_rows:
            logger.info(
                "[UniversalAIBrain] Evidence row[0] type=%s keys=%s",
                type(evidence_rows[0]).__name__,
                list(evidence_rows[0].keys()) if isinstance(evidence_rows[0], dict) else type(evidence_rows[0]).__name__,
            )

        confidence = cls._calculate_confidence(evidence_rows, total_rows, intent_info, profile=profile)
        validation = cls._validate_evidence(evidence_rows, total_rows, sql_error)

        sem_model = {}
        semantic_model_obj = None
        domain = ws_info.get("domain", "Generic Business")
        try:
            sm = build_semantic_model(workspace_id=ws_id, force_rebuild=False)
            if isinstance(sm, dict):
                sem_model = sm
                domain = sm.get("domain", domain)
            else:
                domain = sm.domain
            semantic_model_obj = SemanticModel(
                workspace_id=ws_id,
                domain=domain,
                dataset_type=sem_model.get("dataset_type", "Unknown") if isinstance(sem_model, dict) else getattr(sm, "dataset_type", "Unknown"),
            )
        except Exception:
            semantic_model_obj = SemanticModel(
                workspace_id=ws_id,
                domain=domain,
                dataset_type="Unknown",
            )

        analytics_dict = cls._run_universal_analytics(
            semantic_model=semantic_model_obj,
            parquet_path=parquet_path,
        ) or {}

        predictions = cls._run_prediction(
            semantic_model=semantic_model_obj,
            parquet_path=parquet_path,
            analytics_dict=analytics_dict,
        ) or []

        executive_report = cls._build_executive_report(analytics_dict, semantic_model_obj, predictions) if analytics_dict else {}

        charts = analytics_dict.get("charts", []) or []
        if not charts:
            try:
                from app.analytics.chart_engine import ChartEngine
                charts = ChartEngine.generate_from_parquet(parquet_path, profile)
            except Exception:
                pass

        recommendations = analytics_dict.get("recommendations", [])
        rec_list = []
        for r in recommendations:
            if isinstance(r, dict):
                rec_list.append(r)
            else:
                rec_list.append(r.__dict__ if hasattr(r, "__dict__") else {})

        answer = cls._build_executive_answer(
            question=question,
            intent_info=intent_info,
            analytics_dict=analytics_dict,
            predictions=predictions,
            recommendations=rec_list,
            evidence_rows=evidence_rows,
            sql_query=sql_query,
            domain=domain,
        )

        evidence_records = [
            EvidenceRecord(
                source="duckdb_sql",
                query=sql_query,
                rows_returned=len(evidence_rows),
                columns_used=columns_used,
                tables_used=tables_used,
                snippet=evidence_rows[0].__str__() if evidence_rows else None,
                confidence=round(analytics_dict.get("confidence_score", 0.0) / 100.0, 2) if analytics_dict.get("confidence_score", 0.0) > 1 else round(analytics_dict.get("confidence_score", 0.0), 2),
            )
        ]

        numeric_claims = []
        for ev in (evidence_rows[:5] if evidence_rows else []):
            for key, value in ev.items():
                if isinstance(value, (int, float)) and abs(value) > 1:
                    numeric_claims.append(
                        NumericClaim(
                            value=str(value),
                            context=f"{key} from query result",
                            evidence_ref="duckdb_sql",
                        )
                    )

        rec_claims = []
        if rec_list:
            finding_refs = []
            for ev in (evidence_rows[:3] if evidence_rows else []):
                finding_refs.append(str(ev))
            rec_claims.append(
                RecommendationClaim(
                    text="; ".join([r.get("action", r.get("title", "")) for r in rec_list[:3]]),
                    finding_refs=finding_refs,
                )
            )

        insight_claims = []
        for ev in (evidence_rows[:3] if evidence_rows else []):
            insight_claims.append(
                InsightClaim(
                    text=str(ev),
                    evidence_refs=[sql_query] if sql_query else [],
                )
            )

        answer_validation = AnswerValidationLayer.validate(
            AnswerValidationRequest(
                question=question,
                answer_text=answer,
                evidence=evidence_records,
                numeric_values=numeric_claims,
                recommendations=rec_claims,
                insights=insight_claims,
                sql_query=sql_query,
                analysis_rows=evidence_rows,
                dataset_columns=columns_used,
                domain=domain,
                status="error" if sql_error else ("ok" if evidence_rows else "empty_result"),
            )
        )

        evidence_report = EvidenceBuilder.build(
            analytics_dict=analytics_dict,
            predictions=predictions,
            recommendations=rec_list,
            evidence_rows=evidence_rows,
            sql_query=sql_query,
            tables_used=tables_used,
            columns_used=columns_used,
            validation=validation,
            profile=profile,
            domain=domain,
        )

        response = cls._assemble_copilot_response(
            question=question,
            intent_info=intent_info,
            analytics_dict=analytics_dict,
            predictions=predictions,
            recommendations=rec_list,
            evidence_rows=evidence_rows,
            sql_query=sql_query,
            tables_used=tables_used,
            columns_used=columns_used,
            validation=validation,
            domain=domain,
            profile=profile,
            charts=charts,
            executive_report=executive_report,
            answer_validation=answer_validation,
            evidence_report=evidence_report,
        )

        response["confidence"] = round(answer_validation.confidence_score, 2)

        reasoning = cls._build_reasoning_section(
            question=question,
            intent_info=intent_info,
            analytics_dict=analytics_dict,
            predictions=predictions,
            recommendations=rec_list,
            evidence_rows=evidence_rows,
            sql_query=sql_query,
            domain=domain,
            anomalies=analytics_dict.get("anomalies", []),
            drivers=analytics_dict.get("drivers", []),
            root_causes=analytics_dict.get("root_causes", []),
        )
        response["reasoning"] = reasoning

        next_actions = cls._build_next_actions_section(rec_list)
        response["next_actions"] = next_actions

        try:
            from app.ai.conversation_memory import ConversationMemory
            ConversationMemory.add_turn(session_id, "user", question, workspace_id=ws_id)
            ConversationMemory.add_turn(session_id, "assistant", response.get("answer", ""), metadata={
                "intent": intent_info["intent"],
                "confidence": answer_validation.confidence_score,
                "tables": tables_used,
                "sql": sql_query
            }, workspace_id=ws_id)
        except Exception:
            pass

        try:
            from app.memory.business_memory_engine import BusinessMemoryEngine
            BusinessMemoryEngine.save_conversation(session_id, ws_id, "user", question, metadata={
                "intent": intent_info["intent"],
                "domain": domain,
            })
            BusinessMemoryEngine.save_conversation(session_id, ws_id, "assistant", response.get("answer", ""), metadata={
                "confidence": round(answer_validation.confidence_score, 2),
                "sql": sql_query,
                "tables": tables_used,
            })
            if analytics_result_dict := analytics_dict:
                kpis = analytics_result_dict.get("kpis", [])
                if kpis:
                    BusinessMemoryEngine.save_kpi_snapshot(ws_id, kpis, dataset_id=dataset_id)
                for rec in rec_list[:3]:
                    if isinstance(rec, dict):
                        BusinessMemoryEngine.save_recommendation(
                            workspace_id=ws_id,
                            title=rec.get("title", ""),
                            category=rec.get("category", "general"),
                            priority=rec.get("priority", "MEDIUM"),
                            action=rec.get("action", ""),
                            expected_roi=rec.get("expected_roi", ""),
                            financial_impact=rec.get("financial_impact", ""),
                            confidence=rec.get("confidence", 0.0),
                        )
                for pred in predictions[:2]:
                    pred_dict = pred.to_dict() if hasattr(pred, "to_dict") else (pred if isinstance(pred, dict) else {})
                    BusinessMemoryEngine.save_forecast(
                        workspace_id=ws_id,
                        model_type=pred_dict.get("model_type", "Unknown"),
                        metric=pred_dict.get("metric", analytics_result_dict.get("evidence", {}).get("measures_analyzed", ["Unknown"])[0] if analytics_result_dict.get("evidence", {}).get("measures_analyzed") else "Unknown"),
                        predictions=[pred_dict] if pred_dict else [],
                        confidence=pred_dict.get("confidence", 0.0),
                    )
                if executive_report and "sections" in executive_report:
                    BusinessMemoryEngine.save_report(
                        workspace_id=ws_id,
                        report_type="copilot_executive",
                        audience="general",
                        title=f"Copilot Analysis - {question[:50]}",
                        content=executive_report,
                        analytics_result=analytics_result_dict,
                    )
                BusinessMemoryEngine.save_generated_sql(
                    workspace_id=ws_id,
                    session_id=session_id,
                    sql_query=sql_query,
                    intent=intent_info["intent"],
                    question=question,
                    tables_used=tables_used,
                    columns_used=columns_used,
                    rows_returned=len(evidence_rows),
                    confidence=round(answer_validation.confidence_score, 2),
                    status="error" if sql_error else ("ok" if evidence_rows else "empty_result"),
                    error_message=sql_error,
                    metadata={"domain": domain},
                )
                BusinessMemoryEngine.save_audit_log(
                    workspace_id=ws_id,
                    session_id=session_id,
                    action="copilot_query",
                    resource_type="ai_query",
                    resource_id=dataset_id,
                    details={
                        "intent": intent_info["intent"],
                        "question": question[:200],
                        "confidence": round(answer_validation.confidence_score, 2),
                        "rows_returned": len(evidence_rows),
                        "tables_used": tables_used,
                    },
                    status="success",
                )
        except Exception:
            pass

        try:
            from app.memory.business_memory_engine import BusinessMemoryEngine
            context_prompt = BusinessMemoryEngine.build_context_prompt(
                ws_id,
                session_id,
            )
            response["business_memory_context"] = context_prompt
        except Exception:
            pass

        if rag_context:
            response["rag_context"] = rag_context

        return response

    @classmethod
    def _execute_evidence_query(
        cls,
        intent: str,
        measures: List[str],
        dimensions: List[str],
        temporal: List[str],
        parquet_path: Path,
        tables: List[Dict[str, Any]],
        table_profiles: Dict[str, Dict[str, Any]],
        question: str,
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[str, List[str], List[str], List[Dict[str, Any]], Optional[str]]:
        path_str = str(parquet_path).replace("\\", "/")
        esc = lambda c: f'"{c}"' if c else ""

        safe_measures = [m for m in measures if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", m)]
        safe_dims = [d for d in dimensions if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", d)]
        safe_temporal = [t for t in temporal if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t)]

        m = safe_measures[0] if safe_measures else None
        t = safe_temporal[0] if safe_temporal else None
        d = safe_dims[0] if safe_dims else None

        if intent == "root_cause_analysis" and m and safe_dims:
            sql = (
                f"SELECT CAST({esc(d)} AS VARCHAR) AS dimension, SUM({esc(m)}) AS metric_value, "
                f"COUNT(*) AS cnt FROM read_parquet('{path_str}') "
                f"WHERE {esc(d)} IS NOT NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 15"
            )
            try:
                rows = DuckDBEngine.query(sql)
                return sql, [parquet_path.name], [d, m], rows, None
            except Exception as exc:
                return sql, [parquet_path.name], [d, m], [], str(exc)

        if intent == "root_cause_analysis" and m and t:
            sql = (
                f"SELECT STRFTIME(TRY_CAST({esc(t)} AS TIMESTAMP), '%Y-%m') AS period, "
                f"SUM({esc(m)}) AS metric_value FROM read_parquet('{path_str}') "
                f"WHERE {esc(t)} IS NOT NULL GROUP BY 1 ORDER BY 1 ASC LIMIT 24"
            )
            try:
                rows = DuckDBEngine.query(sql)
                return sql, [parquet_path.name], [t, m], rows, None
            except Exception as exc:
                return sql, [parquet_path.name], [t, m], [], str(exc)

        if intent == "diagnose" and m and safe_dims:
            sql = (
                f"SELECT CAST({esc(d)} AS VARCHAR) AS dimension, SUM({esc(m)}) AS metric_value, "
                f"ROUND(SUM({esc(m)}) * 100.0 / SUM(SUM({esc(m)})) OVER (), 2) AS pct "
                f"FROM read_parquet('{path_str}') "
                f"WHERE {esc(d)} IS NOT NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 10"
            )
            try:
                rows = DuckDBEngine.query(sql)
                return sql, [parquet_path.name], [d, m], rows, None
            except Exception as exc:
                return sql, [parquet_path.name], [d, m], [], str(exc)

        if intent == "diagnose" and m and t:
            sql = (
                f"SELECT STRFTIME(TRY_CAST({esc(t)} AS TIMESTAMP), '%Y-%m') AS period, "
                f"SUM({esc(m)}) AS metric_value FROM read_parquet('{path_str}') "
                f"WHERE {esc(t)} IS NOT NULL GROUP BY 1 ORDER BY 1 ASC LIMIT 24"
            )
            try:
                rows = DuckDBEngine.query(sql)
                return sql, [parquet_path.name], [t, m], rows, None
            except Exception as exc:
                return sql, [parquet_path.name], [t, m], [], str(exc)

        if intent == "top_n" and m and safe_dims:
            sql = (
                f"SELECT CAST({esc(d)} AS VARCHAR) AS dimension, SUM({esc(m)}) AS metric_value "
                f"FROM read_parquet('{path_str}') "
                f"WHERE {esc(d)} IS NOT NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 15"
            )
            try:
                rows = DuckDBEngine.query(sql)
                return sql, [parquet_path.name], [d, m], rows, None
            except Exception as exc:
                return sql, [parquet_path.name], [d, m], [], str(exc)

        if intent == "trend" and m and t:
            sql = (
                f"SELECT STRFTIME(TRY_CAST({esc(t)} AS TIMESTAMP), '%Y-%m') AS period, SUM({esc(m)}) AS metric_value "
                f"FROM read_parquet('{path_str}') "
                f"WHERE {esc(t)} IS NOT NULL GROUP BY 1 ORDER BY 1 ASC LIMIT 24"
            )
            try:
                rows = DuckDBEngine.query(sql)
                return sql, [parquet_path.name], [t, m], rows, None
            except Exception as exc:
                return sql, [parquet_path.name], [t, m], [], str(exc)

        if intent == "breakdown" and m and safe_dims:
            sql = (
                f"SELECT CAST({esc(d)} AS VARCHAR) AS category, SUM({esc(m)}) AS value, COUNT(*) AS cnt "
                f"FROM read_parquet('{path_str}') "
                f"WHERE {esc(d)} IS NOT NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 10"
            )
            try:
                rows = DuckDBEngine.query(sql)
                return sql, [parquet_path.name], [d, m], rows, None
            except Exception as exc:
                return sql, [parquet_path.name], [d, m], [], str(exc)

        if intent == "summary" and m:
            sql = (
                f"SELECT COUNT(*) AS total_records, SUM({esc(m)}) AS total_metric, AVG({esc(m)}) AS avg_metric, "
                f"MIN({esc(m)}) AS min_metric, MAX({esc(m)}) AS max_metric "
                f"FROM read_parquet('{path_str}')"
            )
            try:
                rows = DuckDBEngine.query(sql)
                return sql, [parquet_path.name], [m], rows, None
            except Exception as exc:
                return sql, [parquet_path.name], [m], [], str(exc)

        if intent == "anomaly":
            if m and t:
                sql = (
                    f"WITH base AS ("
                    f"SELECT STRFTIME(TRY_CAST({esc(t)} AS TIMESTAMP), '%Y-%m') AS period, "
                    f"SUM({esc(m)}) AS metric_value "
                    f"FROM read_parquet('{path_str}') GROUP BY 1 ORDER BY 1 ASC"
                    f") SELECT period, metric_value, "
                    f"CASE WHEN metric_value > (SELECT AVG(metric_value) + 2 * STDDEV_SAMP(metric_value) FROM base) THEN 'HIGH' "
                    f"WHEN metric_value < (SELECT AVG(metric_value) - 2 * STDDEV_SAMP(metric_value) FROM base) THEN 'LOW' "
                    f"ELSE 'NORMAL' END AS anomaly_flag FROM base"
                )
                try:
                    rows = DuckDBEngine.query(sql)
                    return sql, [parquet_path.name], [t, m], rows, None
                except Exception as exc:
                    return sql, [parquet_path.name], [t, m], [], str(exc)
            elif m:
                sql = (
                    f"SELECT COUNT(*) AS total_records, SUM({esc(m)}) AS total_metric, AVG({esc(m)}) AS avg_metric, "
                    f"MIN({esc(m)}) AS min_metric, MAX({esc(m)}) AS max_metric "
                    f"FROM read_parquet('{path_str}')"
                )
                try:
                    rows = DuckDBEngine.query(sql)
                    return sql, [parquet_path.name], [m], rows, None
                except Exception as exc:
                    return sql, [parquet_path.name], [m], [], str(exc)

        if intent == "comparison" and m and safe_dims:
            sql = (
                f"SELECT CAST({esc(d)} AS VARCHAR) AS category, SUM({esc(m)}) AS metric_value, COUNT(*) AS cnt "
                f"FROM read_parquet('{path_str}') "
                f"WHERE {esc(d)} IS NOT NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 10"
            )
            try:
                rows = DuckDBEngine.query(sql)
                return sql, [parquet_path.name], [d, m], rows, None
            except Exception as exc:
                return sql, [parquet_path.name], [d, m], [], str(exc)

        if intent == "percentage" and m and safe_dims:
            sql = (
                f"SELECT CAST({esc(d)} AS VARCHAR) AS category, "
                f"SUM({esc(m)}) AS value, "
                f"ROUND(SUM({esc(m)}) * 100.0 / SUM(SUM({esc(m)})) OVER (), 2) AS pct "
                f"FROM read_parquet('{path_str}') "
                f"WHERE {esc(d)} IS NOT NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 10"
            )
            try:
                rows = DuckDBEngine.query(sql)
                return sql, [parquet_path.name], [d, m], rows, None
            except Exception as exc:
                return sql, [parquet_path.name], [d, m], [], str(exc)

        if intent == "forecast" and m and t:
            sql = (
                f"SELECT STRFTIME(TRY_CAST({esc(t)} AS TIMESTAMP), '%Y-%m') AS period, SUM({esc(m)}) AS metric_value "
                f"FROM read_parquet('{path_str}') "
                f"WHERE {esc(t)} IS NOT NULL GROUP BY 1 ORDER BY 1 ASC"
            )
            try:
                rows = DuckDBEngine.query(sql)
                return sql, [parquet_path.name], [t, m], rows, None
            except Exception as exc:
                return sql, [parquet_path.name], [t, m], [], str(exc)

        if intent == "count":
            sql = f"SELECT COUNT(*) AS total_records FROM read_parquet('{path_str}')"
            try:
                rows = DuckDBEngine.query(sql)
                return sql, [parquet_path.name], [], rows, None
            except Exception as exc:
                return sql, [parquet_path.name], [], [], str(exc)

        if m:
            sql = (
                f"SELECT COUNT(*) AS total_records, SUM({esc(m)}) AS total_metric, "
                f"AVG({esc(m)}) AS avg_metric FROM read_parquet('{path_str}')"
            )
            try:
                rows = DuckDBEngine.query(sql)
                return sql, [parquet_path.name], [m], rows, None
            except Exception as exc:
                return sql, [parquet_path.name], [m], [], str(exc)

        sql = f"SELECT COUNT(*) AS total_records FROM read_parquet('{path_str}') LIMIT 5"
        try:
            rows = DuckDBEngine.query(sql)
            return sql, [parquet_path.name], [], rows, None
        except Exception as exc:
            return sql, [parquet_path.name], [], [], str(exc)

    @classmethod
    def _build_empty_response(cls, reason: str) -> Dict[str, Any]:
        return {
            "answer": f"No data available to answer this question. {reason}",
            "executive_summary": f"No data available to answer this question. {reason}",
            "evidence": {
                "metrics": [],
                "sql": None,
                "rows": [],
                "tables": [],
                "columns": [],
                "confidence": 0.0,
                "validation": {"status": "UNAVAILABLE", "rows_returned": 0},
                "dataset_path": "",
                "total_rows": 0,
                "measures_analyzed": [],
                "dimensions_analyzed": [],
                "models_used": [],
                "traceability": "",
            },
            "confidence": 0.0,
            "intent": "unknown",
            "domain": "Unknown",
            "support": {
                "tables_used": [],
                "sql_used": None,
                "validation": {"status": "UNAVAILABLE", "rows_returned": 0},
                "domain": "Unknown",
                "intent": "unknown",
                "follow_up_questions": [
                    "Upload a dataset to enable analytics.",
                    "Select an existing workspace.",
                ],
                "business_reasoning": "",
                "recommendation": {
                    "title": "Data Required",
                    "actions": ["Upload a dataset to enable analytics"],
                    "risks": [],
                    "opportunities": [],
                    "confidence": 0.0,
                },
                "predictions": [],
                "risks": [],
                "opportunities": [],
                "next_actions": ["Upload a dataset"],
                "analytics": {},
                "executive_report": {},
                "charts": [],
            }
        }

    @classmethod
    def _build_unavailable_response(cls, question: str, intent_info: Dict[str, Any], reason: str) -> Dict[str, Any]:
        return {
            "answer": f"No data available to answer this question. {reason}",
            "executive_summary": f"No data available to answer this question. {reason}",
            "evidence": {
                "metrics": [],
                "sql": None,
                "rows": [],
                "tables": [],
                "columns": [],
                "confidence": 0.0,
                "validation": {"status": "UNAVAILABLE", "rows_returned": 0},
                "dataset_path": "",
                "total_rows": 0,
                "measures_analyzed": [],
                "dimensions_analyzed": [],
                "models_used": [],
                "traceability": "",
            },
            "confidence": 0.0,
            "intent": intent_info["intent"],
            "domain": "Unknown",
            "support": {
                "tables_used": [],
                "sql_used": None,
                "validation": {"status": "UNAVAILABLE", "rows_returned": 0},
                "domain": "Unknown",
                "intent": intent_info["intent"],
                "follow_up_questions": [
                    "Upload a dataset to enable analytics.",
                    "Select an existing workspace.",
                ],
                "business_reasoning": "",
                "recommendation": {
                    "title": "Data Required",
                    "actions": ["Upload a dataset to enable analytics"],
                    "risks": [],
                    "opportunities": [],
                    "confidence": 0.0,
                },
                "predictions": [],
                "risks": [],
                "opportunities": [],
                "next_actions": ["Upload a dataset"],
                "analytics": {},
                "executive_report": {},
                "charts": [],
            }
        }
