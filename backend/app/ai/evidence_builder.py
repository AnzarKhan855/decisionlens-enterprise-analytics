from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EvidenceReport:
    evidence: str = ""
    confidence: float = 0.0
    rows_analyzed: int = 0
    columns_analyzed: List[str] = field(default_factory=list)
    business_reasoning: str = ""
    recommendation: str = ""
    expected_impact: str = ""
    priority: str = "LOW"
    models_used: List[str] = field(default_factory=list)
    sql_query: str = ""
    tables_used: List[str] = field(default_factory=list)
    validation_status: str = "UNKNOWN"
    disclaimer: str = ""
    prediction_feasible: bool = False
    prediction_limitation: Optional[str] = None
    anomalies_detected: int = 0
    drivers_identified: int = 0
    kpi_count: int = 0
    forecast_available: bool = False
    recommendation_count: int = 0
    raw: Dict[str, Any] = field(default_factory=dict)


class EvidenceBuilder:
    """
    Evidence Builder for the DecisionLens AI pipeline.

    This is the SINGLE module that constructs the final evidence-backed
    AI response. Every AI output must flow through here.

    Pipeline position:
      Dataset -> Validation -> Analytics -> KPIs -> Forecast
          -> Recommendation Engine -> Evidence Builder -> Executive Response

    Rules:
      - Never hallucinate. If evidence does not exist, say so.
      - Never guess. Never invent.
      - Every claim must be traceable to executed SQL or computed statistics.
    """

    @classmethod
    def build(
        cls,
        analytics_dict: Dict[str, Any],
        predictions: List[Any],
        recommendations: List[Any],
        evidence_rows: List[Dict[str, Any]],
        sql_query: str,
        tables_used: List[str],
        columns_used: List[str],
        validation: Dict[str, Any],
        profile: Dict[str, Any],
        domain: str = "Generic Business",
    ) -> EvidenceReport:
        rows_analyzed = profile.get("total_rows", 0)
        measures = profile.get("column_categories", {}).get("measures", [])
        dimensions = profile.get("column_categories", {}).get("dimensions", [])
        temporal = profile.get("column_categories", {}).get("temporal", [])
        columns_analyzed = list(measures) + list(dimensions) + list(temporal)
        confidence_score = analytics_dict.get("confidence_score", 0.0)
        if confidence_score > 1.0:
            confidence_score = confidence_score / 100.0

        prediction_list = []
        for p in predictions:
            if isinstance(p, dict):
                prediction_list.append(p)
            elif hasattr(p, "to_dict"):
                prediction_list.append(p.to_dict())
            elif hasattr(p, "__dict__"):
                prediction_list.append({k: v for k, v in p.__dict__.items()})

        norm_recs = []
        for r in recommendations:
            if isinstance(r, dict):
                norm_recs.append(r)
            elif hasattr(r, "__dict__"):
                norm_recs.append({k: v for k, v in r.__dict__.items()})

        feasible_preds = [p for p in prediction_list if p.get("feasible")]
        forecast_available = bool(feasible_preds)
        prediction_limitation = None
        if not feasible_preds:
            lim = next(
                (p.get("limitation") for p in prediction_list if p.get("limitation")),
                "Insufficient data for reliable prediction.",
            )
            prediction_limitation = lim

        evidence = cls._build_evidence_text(
            analytics_dict=analytics_dict,
            evidence_rows=evidence_rows,
            sql_query=sql_query,
            rows_analyzed=rows_analyzed,
            columns_analyzed=columns_analyzed,
            predictions=prediction_list,
            recommendations=norm_recs,
        )

        business_reasoning = cls._build_business_reasoning(
            analytics_dict=analytics_dict,
            evidence_rows=evidence_rows,
            domain=domain,
        )

        recommendation_text, priority, expected_impact = cls._build_recommendation_block(
            recommendations=norm_recs,
            predictions=prediction_list,
            analytics_dict=analytics_dict,
            evidence_rows=evidence_rows,
        )

        models_used = analytics_dict.get("evidence", {}).get("models_used", [])
        if not models_used:
            models_used = [
                "SemanticAnalyticsEngine",
                "StatisticalAnomalyEngine",
                "VarianceDecompositionEngine",
                "AutoInsights",
                "RecommendationEngine",
                "BusinessHealthEngine",
                "UniversalPredictionEngine",
            ]

        anomalies_count = len(analytics_dict.get("anomalies", [])) + len(analytics_dict.get("outliers", []))
        drivers_count = len(analytics_dict.get("drivers", [])) + len(analytics_dict.get("root_causes", []))
        kpi_count = len(analytics_dict.get("kpis", []))

        disclaimer = ""
        if not evidence_rows and not columns_analyzed:
            disclaimer = "No evidence available. The analysis returned no results or the dataset lacks the required columns."
        if prediction_limitation and not feasible_preds:
            disclaimer = f"Prediction not feasible. {prediction_limitation}" if not disclaimer else disclaimer + f" Prediction: {prediction_limitation}"

        report = EvidenceReport(
            evidence=evidence,
            confidence=round(confidence_score, 4),
            rows_analyzed=rows_analyzed,
            columns_analyzed=columns_analyzed,
            business_reasoning=business_reasoning,
            recommendation=recommendation_text,
            expected_impact=expected_impact,
            priority=priority,
            models_used=models_used,
            sql_query=sql_query,
            tables_used=tables_used,
            validation_status=validation.get("status", "UNKNOWN"),
            disclaimer=disclaimer,
            prediction_feasible=forecast_available,
            prediction_limitation=prediction_limitation,
            anomalies_detected=anomalies_count,
            drivers_identified=drivers_count,
            kpi_count=kpi_count,
            forecast_available=forecast_available,
            recommendation_count=len(norm_recs),
            raw={
                "analytics_summary": cls._safe_summary(analytics_dict),
                "predictions": prediction_list[:3],
                "recommendations": norm_recs[:3],
                "validation": validation,
                "profile": {
                    "total_rows": rows_analyzed,
                    "measures": measures,
                    "dimensions": dimensions,
                    "temporal": temporal,
                },
            },
        )
        return report

    @staticmethod
    def _build_evidence_text(
        analytics_dict: Dict[str, Any],
        evidence_rows: List[Dict[str, Any]],
        sql_query: str,
        rows_analyzed: int,
        columns_analyzed: List[str],
        predictions: List[Dict[str, Any]],
        recommendations: List[Dict[str, Any]],
    ) -> str:
        parts: List[str] = []

        if sql_query:
            parts.append(f"Executed SQL: {sql_query}")

        if evidence_rows:
            parts.append(f"Query returned {len(evidence_rows)} verified rows from {rows_analyzed:,} total records.")
        else:
            parts.append(f"No query results returned. Dataset contains {rows_analyzed:,} rows.")

        if columns_analyzed:
            cols = ", ".join(columns_analyzed[:10])
            parts.append(f"Columns analyzed: {cols}")

        kpis = analytics_dict.get("kpis", [])
        if kpis:
            parts.append(f"{len(kpis)} KPIs computed from verified data.")

        anomalies = analytics_dict.get("anomalies", [])
        outliers = analytics_dict.get("outliers", [])
        if anomalies or outliers:
            parts.append(f"{len(anomalies) + len(outliers)} anomalies/outliers detected by statistical methods.")

        if predictions:
            feasible = [p for p in predictions if p.get("feasible")]
            if feasible:
                parts.append(f"{len(feasible)} forecast model(s) generated.")
            else:
                parts.append("Forecast not feasible with current data.")

        if recommendations:
            parts.append(f"{len(recommendations)} evidence-based recommendation(s) generated.")

        return " | ".join(parts) if parts else "No evidence available."

    @staticmethod
    def _build_business_reasoning(
        analytics_dict: Dict[str, Any],
        evidence_rows: List[Dict[str, Any]],
        domain: str,
    ) -> str:
        kpis = analytics_dict.get("kpis", [])
        trends = analytics_dict.get("trends", {})
        anomalies = analytics_dict.get("anomalies", [])
        root_causes = analytics_dict.get("root_causes", [])
        drivers = analytics_dict.get("drivers", [])
        growth = analytics_dict.get("growth", [])
        decline = analytics_dict.get("decline", [])

        parts: List[str] = []
        parts.append(f"Domain context: {domain}.")

        if kpis:
            primary = kpis[0]
            name = primary.get("name", "primary metric") if isinstance(primary, dict) else getattr(primary, "name", "primary metric")
            parts.append(f"Primary metric '{name}' computed from dataset aggregation.")

        if trends:
            trend_measures = list(trends.keys())[:2]
            parts.append(f"Temporal trends detected for: {', '.join(trend_measures)}.")

        if growth:
            parts.append(f"{len(growth)} significant growth period(s) identified.")
        if decline:
            parts.append(f"{len(decline)} significant decline period(s) identified.")

        if root_causes:
            dims = [rc.get("dimension") if isinstance(rc, dict) else getattr(rc, "dimension", "") for rc in root_causes]
            parts.append(f"Root cause analysis completed for dimensions: {', '.join(dims)}.")

        if drivers:
            parts.append(f"{len(drivers)} key business driver(s) identified.")

        if anomalies:
            high = sum(1 for a in anomalies if str(a.get("severity", "")).upper() in ("HIGH", "CRITICAL") if isinstance(a, dict))
            if high:
                parts.append(f"{high} high-severity anomaly(ies) require investigation.")

        return " ".join(parts) if parts else "Analysis complete. No significant business patterns detected in the dataset."

    @staticmethod
    def _build_recommendation_block(
        recommendations: List[Dict[str, Any]],
        predictions: List[Dict[str, Any]],
        analytics_dict: Dict[str, Any],
        evidence_rows: List[Dict[str, Any]],
    ) -> tuple[str, str, str]:
        actions: List[str] = []
        for r in recommendations[:3]:
            action = r.get("action") or r.get("title", "")
            if action:
                actions.append(action)

        if not actions:
            actions = ["No evidence-backed recommendations available for this dataset."]

        priority = "LOW"
        for r in recommendations:
            p = r.get("priority", "LOW")
            if p == "CRITICAL":
                priority = "CRITICAL"
                break
            if p == "HIGH" and priority != "CRITICAL":
                priority = "HIGH"

        forecast_text = ""
        feasible_preds = [p for p in predictions if p.get("feasible")]
        if feasible_preds:
            forecast_text = feasible_preds[0].get("prediction", "")

        expected_impact = "Insufficient evidence"
        for r in recommendations:
            impact = r.get("financial_impact") or r.get("expected_roi") or r.get("business_impact", "")
            if impact and impact != "Insufficient evidence":
                expected_impact = impact
                break

        if expected_impact == "Insufficient evidence" and forecast_text:
            expected_impact = forecast_text[:200]

        if expected_impact == "Insufficient evidence":
            expected_impact = "Impact cannot be estimated without sufficient numeric metrics or temporal data."

        rec_text = "; ".join(actions)
        return rec_text, priority, expected_impact

    @staticmethod
    def _safe_summary(analytics_dict: Dict[str, Any]) -> Dict[str, Any]:
        safe = {}
        for key in [
            "volume",
            "confidence_score",
            "domain",
            "dataset_type",
            "prediction_feasible",
            "prediction_limitation",
            "health_score",
            "generated_at",
        ]:
            if key in analytics_dict:
                val = analytics_dict[key]
                if hasattr(val, "to_dict"):
                    safe[key] = val.to_dict()
                elif hasattr(val, "__dict__"):
                    safe[key] = {k: v for k, v in val.__dict__.items()}
                else:
                    safe[key] = val
        safe["kpi_count"] = len(analytics_dict.get("kpis", []))
        safe["anomaly_count"] = len(analytics_dict.get("anomalies", [])) + len(analytics_dict.get("outliers", []))
        safe["driver_count"] = len(analytics_dict.get("drivers", [])) + len(analytics_dict.get("root_causes", []))
        safe["prediction_count"] = len(analytics_dict.get("predictions", []))
        safe["recommendation_count"] = len(analytics_dict.get("recommendations", []))
        return safe

    @classmethod
    def build_empty(cls, reason: str, profile: Optional[Dict[str, Any]] = None) -> EvidenceReport:
        profile = profile or {}
        rows = profile.get("total_rows", 0)
        cols = list(profile.get("column_categories", {}).get("measures", [])) + list(
            profile.get("column_categories", {}).get("dimensions", [])
        )
        return EvidenceReport(
            evidence=f"None. {reason}",
            confidence=0.0,
            rows_analyzed=rows,
            columns_analyzed=cols,
            business_reasoning=f"No analysis performed. {reason}",
            recommendation="Insufficient evidence for recommendation.",
            expected_impact="Impact cannot be estimated.",
            priority="LOW",
            models_used=[],
            sql_query="",
            tables_used=[],
            validation_status="UNAVAILABLE",
            disclaimer=reason,
            prediction_feasible=False,
            prediction_limitation=reason,
            anomalies_detected=0,
            drivers_identified=0,
            kpi_count=0,
            forecast_available=False,
            recommendation_count=0,
        )
