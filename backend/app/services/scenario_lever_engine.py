from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from app.logging.logger import get_logger

logger = get_logger(__name__)


class ScenarioLeverEngine:
    """
    Universal data-driven scenario lever discovery engine.

    Works with any structured dataset by inspecting all numeric columns
    and excluding only obvious technical fields (IDs, timestamps, lat/long).
    Lever ranking is based on semantic meaning, variance, relationships with
    other variables, and business relevance.
    """

    MIN_NON_NULL_RATIO = 0.6
    MIN_VARIANCE = 1e-6
    MAX_UNIQUENESS_FOR_LEVER = 0.90
    MIN_STDDEV_FOR_LEVER = 1e-4
    HIGH_CARDINALITY_THRESHOLD = 150

    ID_TERMS = {
        "_id", "id_", "zipcode", "zip_code", "latitude", "longitude",
        "lat", "lon", "phone", "ssn", "isbn", "passport", "driving_license",
        "aadhaar", "pan", "voterid", "registration_number", "serial_number",
        "row_number", "index", "uuid", "guid", "token", "session_id",
        "surrogate",
    }

    @classmethod
    def discover_levers(
        cls,
        profile: Dict[str, Any],
        semantic_model: Optional[Dict[str, Any]] = None,
        analytics_result: Optional[Any] = None,
    ) -> Dict[str, Any]:
        columns = profile.get("columns", {})
        total_rows = profile.get("total_rows", 0)
        col_categories = profile.get("column_categories", {})

        semantic_classifications = []
        if semantic_model:
            semantic_classifications = (
                semantic_model.get("column_classifications", [])
                if isinstance(semantic_model, dict)
                else getattr(semantic_model, "column_classifications", []) or []
            )

        correlations: List[Dict[str, Any]] = []
        if analytics_result is not None:
            corr_list = getattr(analytics_result, "correlations", None) or []
            for c in corr_list:
                if hasattr(c, "__dict__"):
                    correlations.append(c.__dict__)
                elif isinstance(c, dict):
                    correlations.append(c)

        corr_map = cls._build_correlation_map(correlations)
        semantic_map = cls._build_semantic_map(semantic_classifications)
        available_levers = []
        unavailable_reasons = []

        for col_name, col_profile in columns.items():
            is_suitable, reason = cls._is_suitable_lever(
                col_name=col_name,
                col_profile=col_profile,
                total_rows=total_rows,
                semantic_info=semantic_map.get(col_name, {}),
            )
            if not is_suitable:
                unavailable_reasons.append({"column": col_name, "reason": reason})
                continue

            affected = cls._affected_metrics(col_name, corr_map, columns)
            confidence = cls._lever_confidence(col_profile, total_rows, affected)

            clean_label = cls._business_label(col_name, semantic_map.get(col_name, {}))
            base_val = cls._safe_current_value(col_profile)
            metric_type = cls._classify_metric_type(col_name, col_profile, semantic_map.get(col_name, {}))

            lever = {
                "id": col_name.lower().replace(" ", "_").replace("-", "_"),
                "column": col_name,
                "label": clean_label,
                "type": "numeric_adjustment",
                "metric_type": metric_type,
                "current_value": base_val,
                "change_pct": 0.0,
                "direction_options": ["increase", "decrease"],
                "affected_metrics": affected,
                "confidence": round(confidence, 2),
                "evidence": {
                    "total_rows": total_rows,
                    "non_null_count": col_profile.get("non_null_count", total_rows),
                    "null_percentage": col_profile.get("null_percentage", 0.0),
                    "stddev": col_profile.get("stats", {}).get("stddev"),
                    "correlations_found": len(affected),
                    "semantic_type": semantic_map.get(col_name, {}).get("semantic_type", "unknown"),
                },
                "methodology": "Hypothetical sensitivity model derived from empirical dataset relationships.",
                "limitation": (
                    "Model-based sensitivity estimate; baseline dataset variance used."
                    if not affected
                    else "Scenario reflects historical correlation, not proven causation."
                ),
            }
            available_levers.append(lever)

        available_levers.sort(
            key=lambda l: (
                -l["confidence"],
                -len(l.get("affected_metrics", [])),
                -(l.get("current_value") or 0),
            )
        )

        domain = "Generic Business"
        if semantic_model:
            domain = semantic_model.get("domain") if isinstance(semantic_model, dict) else getattr(semantic_model, "domain", "Generic Business")
        presets = cls.generate_domain_presets(available_levers, domain=domain)

        supported = len(available_levers) > 0
        reason = (
            "Numeric variables detected for scenario simulation."
            if supported
            else "No suitable numeric variables detected. Upload a dataset with numeric measures."
        )

        return {
            "workspace_id": semantic_model.get("workspace_id") if isinstance(semantic_model, dict) else getattr(semantic_model, "workspace_id", ""),
            "available_levers": available_levers,
            "unavailable_candidates": unavailable_reasons,
            "presets": presets,
            "scenario_capability": {
                "supported": supported,
                "reason": reason,
                "lever_count": len(available_levers),
            },
        }

    @classmethod
    def simulate(
        cls,
        workspace_id: str,
        changes: List[Dict[str, Any]],
        profile: Dict[str, Any],
        semantic_model: Optional[Dict[str, Any]] = None,
        analytics_result: Optional[Any] = None,
    ) -> Dict[str, Any]:
        if not changes:
            return {
                "workspace_id": workspace_id,
                "baseline": {},
                "scenario": {},
                "deltas": {},
                "confidence": 0.0,
                "evidence": "No changes requested.",
                "methodology": "No-op simulation.",
            }

        columns = profile.get("columns", {})
        col_categories = profile.get("column_categories", {})
        semantic_map = cls._build_semantic_map(
            (semantic_model.get("column_classifications", []) if isinstance(semantic_model, dict)
             else getattr(semantic_model, "column_classifications", []) or [])
        )

        correlations: List[Dict[str, Any]] = []
        if analytics_result is not None:
            corr_list = getattr(analytics_result, "correlations", None) or []
            for c in corr_list:
                if hasattr(c, "__dict__"):
                    correlations.append(c.__dict__)
                elif isinstance(c, dict):
                    correlations.append(c)
        corr_map = cls._build_correlation_map(correlations)

        baseline: Dict[str, Any] = {}
        scenario: Dict[str, Any] = {}
        deltas: Dict[str, Any] = {}
        applied_changes = []
        evidence_parts = []
        limitations = []

        for ch in changes:
            lever_id = ch.get("lever_id", "")
            change_pct = float(ch.get("change_pct", 0) or 0)
            lever_col = cls._resolve_lever_column(lever_id, columns)
            if not lever_col or lever_col not in columns:
                continue

            cp = columns[lever_col]
            stats = cp.get("stats", {})
            base_val = stats.get("mean")
            if base_val is None:
                base_val = stats.get("sum")
            if base_val is None:
                base_val = 0
            if base_val is None or (isinstance(base_val, float) and math.isnan(base_val)):
                base_val = 0.0

            factor = 1.0 + (change_pct / 100.0)
            scenario_val = base_val * factor
            abs_delta = scenario_val - base_val
            pct_delta = change_pct

            baseline[lever_col] = round(float(base_val), 4)
            scenario[lever_col] = round(float(scenario_val), 4)
            deltas[lever_col] = {
                "absolute_delta": round(float(abs_delta), 4),
                "percentage_delta": round(float(pct_delta), 2),
                "change_pct": round(float(change_pct), 2),
            }
            applied_changes.append({
                "lever_id": lever_id,
                "column": lever_col,
                "change_pct": round(float(change_pct), 2),
                "baseline": round(float(base_val), 4),
                "scenario": round(float(scenario_val), 4),
            })
            evidence_parts.append(
                f"{lever_col}: {base_val:,.2f} -> {scenario_val:,.2f} ({pct_delta:+.1f}%)"
            )

        affected_metrics_map: Dict[str, Dict[str, Any]] = {}
        for ch in changes:
            lever_id = ch.get("lever_id", "")
            change_pct = float(ch.get("change_pct", 0) or 0)
            lever_col = cls._resolve_lever_column(lever_id, columns)
            if not lever_col:
                continue

            related = corr_map.get(lever_col.lower(), [])
            for rel in related[:8]:
                rel_col = rel.get("column")
                if not rel_col or rel_col.lower() == lever_col.lower():
                    continue
                if rel_col not in columns:
                    continue
                coef = float(rel.get("coefficient", 0) or 0)
                if rel_col not in affected_metrics_map:
                    affected_metrics_map[rel_col] = {
                        "column": rel_col,
                        "correlation_coefficient": coef,
                        "influencing_levers": [],
                    }
                affected_metrics_map[rel_col]["influencing_levers"].append({
                    "lever": lever_col,
                    "change_pct": change_pct,
                    "coefficient": coef,
                })

        estimated_revenue_delta = 0.0
        for metric_name, info in affected_metrics_map.items():
            cp = columns.get(metric_name, {})
            stats = cp.get("stats", {})
            base = stats.get("mean") or stats.get("sum") or 0
            if base is None or (isinstance(base, float) and math.isnan(base)):
                base = 0.0
            estimated_delta = 0.0
            for inf in info["influencing_levers"]:
                lever_col = inf["lever"]
                lever_cp = columns.get(lever_col, {})
                lever_stats = lever_cp.get("stats", {})
                lever_base = lever_stats.get("mean") or lever_stats.get("sum") or 0
                if lever_base and lever_base != 0:
                    pct = inf["change_pct"] / 100.0
                    estimated_delta += base * pct * inf["coefficient"]
            scenario_val = base + estimated_delta
            deltas[metric_name] = {
                "baseline": round(float(base), 4),
                "scenario": round(float(scenario_val), 4),
                "estimated_delta": round(float(estimated_delta), 4),
                "correlation_coefficient": round(info["correlation_coefficient"], 4),
                "note": "Estimated from observed correlation; not a causal prediction.",
            }
            estimated_revenue_delta += estimated_delta

        overall_confidence = cls._estimate_confidence(
            applied_changes, affected_metrics_map, columns
        )

        if not applied_changes:
            overall_confidence = 0.0
            limitations.append("No valid levers were adjusted.")
        elif len(affected_metrics_map) == 0:
            overall_confidence = min(overall_confidence, 0.55)
            limitations.append(
                "No statistically significant correlations found for downstream impact estimation. "
                "Returning directional estimate based on adjusted levers only."
            )

        if overall_confidence < 0.4:
            limitations.append(
                "Insufficient evidence for a reliable predictive estimate. "
                "Consider adjusting levers with stronger historical relationships."
            )

        recommendation = cls._build_recommendation(
            applied_changes, affected_metrics_map, overall_confidence
        )

        metric_categories = cls._categorize_metrics(columns, semantic_map)

        return {
            "workspace_id": workspace_id,
            "baseline": baseline,
            "scenario": scenario,
            "deltas": deltas,
            "applied_changes": applied_changes,
            "affected_metrics": list(affected_metrics_map.values()),
            "confidence": round(overall_confidence, 2),
            "evidence": " ".join(evidence_parts) if evidence_parts else "No adjustments applied.",
            "methodology": "Hypothetical scenario based on observed dataset relationships. Not a causal prediction.",
            "limitations": limitations or ["Prediction accuracy depends on historical correlation stability."],
            "recommendation": recommendation,
            "estimated_impact_summary": {
                "total_estimated_delta": round(float(estimated_revenue_delta), 4),
                "affected_metric_count": len(affected_metrics_map),
            },
            "kpis": metric_categories.get("kpis", []),
            "forecastable_measures": metric_categories.get("forecastable", []),
            "currency_metrics": metric_categories.get("currency", []),
            "percentage_metrics": metric_categories.get("percentage", []),
            "volume_metrics": metric_categories.get("volume", []),
        }

    @classmethod
    def _is_suitable_lever(
        cls,
        col_name: str,
        col_profile: Dict[str, Any],
        total_rows: int,
        semantic_info: Dict[str, Any],
    ) -> Tuple[bool, str]:
        if total_rows <= 0:
            return False, "Dataset has no rows."

        data_type = str(col_profile.get("data_type", "")).upper()
        col_lower = col_name.lower().strip()

        if any(k in data_type for k in ["DATE", "TIME", "TIMESTAMP"]):
            return False, "Temporal column."

        exact_temporal = {"date", "time", "timestamp", "created_at", "updated_at",
                          "created_time", "modified_at", "modified_time"}
        if col_lower in exact_temporal:
            return False, "Temporal column by exact name match."

        stats = col_profile.get("stats") or {}
        if not stats:
            return False, "Non-numeric column."

        stddev = stats.get("stddev")
        if stddev is None:
            return False, "Non-numeric column."

        if semantic_info.get("is_temporal"):
            return False, "Classified as temporal."
        if semantic_info.get("is_identifier"):
            return False, "Classified as identifier."

        if any(term in col_lower for term in cls.ID_TERMS):
            return False, "Column name suggests identifier or technical field."

        non_null_count = col_profile.get("non_null_count")
        if non_null_count is None:
            stats = col_profile.get("stats") or {}
            non_null_count = stats.get("count") or total_rows or 0
        null_pct = col_profile.get("null_percentage", 0.0)
        distinct_count = col_profile.get("distinct_count", 0)

        if total_rows > 0 and (non_null_count / total_rows) < cls.MIN_NON_NULL_RATIO:
            return False, f"Insufficient non-null observations ({non_null_count}/{total_rows})."

        if not semantic_info.get("is_measure"):
            has_numeric_stats = bool(
                col_profile.get("stats") and col_profile.get("stats", {}).get("stddev") is not None
            )
            if not has_numeric_stats:
                if distinct_count > cls.HIGH_CARDINALITY_THRESHOLD and total_rows > 0:
                    cardinality_ratio = distinct_count / max(total_rows, 1)
                    if cardinality_ratio > 0.7:
                        return False, "High-cardinality categorical data encoded as numeric."

        stats = col_profile.get("stats", {})
        stddev = stats.get("stddev")
        if stddev is not None:
            if isinstance(stddev, float) and (math.isnan(stddev) or math.isinf(stddev)):
                return False, "Invalid standard deviation."
            if isinstance(stddev, (int, float)) and stddev < cls.MIN_STDDEV_FOR_LEVER:
                return False, "Near-zero variance; adjustment would have no meaningful effect."

        return True, "Suitable."

    @classmethod
    def generate_domain_presets(
        cls, available_levers: List[Dict[str, Any]], domain: str = "Generic Business"
    ) -> List[Dict[str, Any]]:
        if not available_levers:
            return []

        presets = []
        lever_map = {l["id"]: l for l in available_levers}

        def add_preset(pid, name, description, changes):
            presets.append({
                "id": pid,
                "name": name,
                "description": description,
                "changes": changes,
            })

        numeric_levers = available_levers
        if len(numeric_levers) >= 1:
            first = numeric_levers[0]
            add_preset(
                "single_adjustment",
                f"Adjust {first['label']}",
                f"Simulate a +10% adjustment in {first['label']}.",
                [{"lever_id": first["id"], "change_pct": 10.0}],
            )

        if len(numeric_levers) >= 2:
            add_preset(
                "dual_adjustment",
                f"Combined {numeric_levers[0]['label']} & {numeric_levers[1]['label']}",
                f"Simulate +10% in {numeric_levers[0]['label']} and -5% in {numeric_levers[1]['label']}.",
                [
                    {"lever_id": numeric_levers[0]["id"], "change_pct": 10.0},
                    {"lever_id": numeric_levers[1]["id"], "change_pct": -5.0},
                ],
            )

        if len(numeric_levers) >= 3:
            add_preset(
                "stress_test",
                "Stress Test",
                f"Simulate +15% in {numeric_levers[0]['label']}, -10% in {numeric_levers[1]['label']}, +5% in {numeric_levers[2]['label']}.",
                [
                    {"lever_id": numeric_levers[0]["id"], "change_pct": 15.0},
                    {"lever_id": numeric_levers[1]["id"], "change_pct": -10.0},
                    {"lever_id": numeric_levers[2]["id"], "change_pct": 5.0},
                ],
            )

        return presets

    @classmethod
    def _affected_metrics(
        cls,
        lever_col: str,
        corr_map: Dict[str, List[Dict[str, Any]]],
        columns: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        lever_lower = lever_col.lower()
        related = corr_map.get(lever_lower, [])
        columns_lower = {c.lower(): c for c in columns}
        affected = []
        for rel in related:
            rel_col = rel.get("column")
            if not rel_col or rel_col.lower() == lever_lower:
                continue
            if rel_col not in columns_lower:
                continue
            orig_col = columns_lower[rel_col]
            coef = float(rel.get("coefficient", 0) or 0)
            if abs(coef) >= 0.15:
                affected.append({
                    "column": orig_col,
                    "correlation_coefficient": round(coef, 4),
                    "strength": cls._correlation_strength(coef),
                })
        affected.sort(key=lambda x: -abs(x.get("correlation_coefficient", 0)))
        return affected[:10]

    @staticmethod
    def _correlation_strength(coef: float) -> str:
        abs_c = abs(coef)
        if abs_c >= 0.7:
            return "strong"
        if abs_c >= 0.4:
            return "moderate"
        return "weak"

    @classmethod
    def _lever_confidence(
        cls,
        col_profile: Dict[str, Any],
        total_rows: int,
        affected: List[Dict[str, Any]],
    ) -> float:
        confidence = 0.5
        null_pct = col_profile.get("null_percentage", 0.0)
        if null_pct < 5:
            confidence += 0.15
        elif null_pct < 20:
            confidence += 0.05
        if total_rows > 1000:
            confidence += 0.05
        if total_rows > 10000:
            confidence += 0.05
        if affected:
            confidence += 0.15
        return min(0.95, max(0.5, confidence))

    @staticmethod
    def _safe_current_value(col_profile: Dict[str, Any]) -> Optional[float]:
        stats = col_profile.get("stats", {})
        val = stats.get("mean")
        if val is None:
            val = stats.get("sum")
        if val is None:
            val = stats.get("median")
        if val is None:
            return None
        try:
            v = float(val)
            if math.isnan(v) or math.isinf(v):
                return None
            return v
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _build_correlation_map(
        correlations: List[Dict[str, Any]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        corr_map: Dict[str, List[Dict[str, Any]]] = {}
        for c in correlations:
            a = (c.get("column_a") or "").lower()
            b = (c.get("column_b") or "").lower()
            coef = float(c.get("coefficient", 0) or 0)
            if a:
                corr_map.setdefault(a, []).append({"column": b, "coefficient": coef})
            if b:
                corr_map.setdefault(b, []).append({"column": a, "coefficient": coef})
        return corr_map

    @staticmethod
    def _build_semantic_map(
        classifications: List[Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        semantic_map: Dict[str, Dict[str, Any]] = {}
        for cc in classifications:
            name = cc.get("name", "")
            if not name:
                continue
            semantic_map[name] = {
                "semantic_type": cc.get("semantic_type", ""),
                "business_role": cc.get("business_role", ""),
                "is_measure": cc.get("is_measure", False),
                "is_temporal": cc.get("is_temporal", False),
                "is_identifier": cc.get("is_identifier", False),
                "is_dimension": cc.get("is_dimension", False),
            }
        return semantic_map

    @staticmethod
    def _business_label(col_name: str, semantic_info: Dict[str, Any]) -> str:
        if semantic_info.get("semantic_type"):
            return col_name.replace("_", " ").title()
        return col_name.replace("_", " ").title()

    @classmethod
    def _classify_metric_type(cls, col_name: str, col_profile: Dict[str, Any], semantic_info: Dict[str, Any]) -> str:
        col_lower = col_name.lower()
        semantic_type = semantic_info.get("semantic_type", "")
        if semantic_type in ("currency", "percentage", "ratio"):
            return semantic_type
        if any(k in col_lower for k in ["revenue", "sales", "cost", "price", "amount", "balance", "fee", "tax", "profit", "margin", "income", "expense", "salary", "payout", "premium", "claim", "turnover", "cogs"]):
            return "currency"
        if any(k in col_lower for k in ["percentage", "pct", "rate", "ratio", "discount", "nps", "ctr", "cpc", "cpa", "roas", "efficiency", "utilization", "conversion", "attrition", "churn", "yield", "oee"]):
            return "percentage"
        if any(k in col_lower for k in ["quantity", "qty", "count", "volume", "units", "customers", "orders", "transactions", "items", "throughput"]):
            return "volume"
        if col_profile.get("stats", {}).get("stddev", 0) > 0:
            return "forecastable"
        return "numeric"

    @classmethod
    def _categorize_metrics(cls, columns: Dict[str, Any], semantic_map: Dict[str, Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        categories = {
            "kpis": [],
            "forecastable": [],
            "currency": [],
            "percentage": [],
            "volume": [],
            "numeric": [],
        }
        for col_name, col_profile in columns.items():
            stats = col_profile.get("stats") or {}
            if not stats or stats.get("stddev") is None:
                continue
            metric_type = cls._classify_metric_type(col_name, col_profile, semantic_map.get(col_name, {}))
            base_val = cls._safe_current_value(col_profile)
            entry = {
                "column": col_name,
                "label": cls._business_label(col_name, semantic_map.get(col_name, {})),
                "current_value": base_val,
                "metric_type": metric_type,
                "stddev": stats.get("stddev"),
            }
            categories.get(metric_type, categories["numeric"]).append(entry)
            if metric_type in ("currency", "volume"):
                categories["kpis"].append(entry)
            if metric_type == "forecastable":
                categories["forecastable"].append(entry)
        return categories

    @staticmethod
    def _resolve_lever_column(lever_id: str, columns: Dict[str, Any]) -> Optional[str]:
        lid = lever_id.lower().replace(" ", "_").replace("-", "_")
        for c in columns:
            if c.lower().replace(" ", "_").replace("-", "_") == lid:
                return c
        return None

    @classmethod
    def _estimate_confidence(
        cls,
        applied_changes: List[Dict[str, Any]],
        affected_metrics_map: Dict[str, Dict[str, Any]],
        columns: Dict[str, Any],
    ) -> float:
        if not applied_changes:
            return 0.0
        if not affected_metrics_map:
            return 0.5
        confidence = 0.5
        confidence += min(0.2, 0.05 * len(affected_metrics_map))
        strong = sum(1 for m in affected_metrics_map.values() if abs(m.get("correlation_coefficient", 0)) >= 0.7)
        if strong:
            confidence += min(0.15, 0.05 * strong)
        return min(0.9, max(0.5, confidence))

    @classmethod
    def _build_recommendation(
        cls,
        applied_changes: List[Dict[str, Any]],
        affected_metrics_map: Dict[str, Dict[str, Any]],
        confidence: float,
    ) -> str:
        if not applied_changes:
            return "No adjustments were applied."
        if confidence < 0.4:
            return (
                "Insufficient evidence for a reliable predictive estimate. "
                "The current dataset does not contain enough correlated variables to project downstream impact with confidence. "
                "Gather more historical data or include additional related measures before relying on this estimate."
            )
        if not affected_metrics_map:
            levers = ", ".join(c["column"] for c in applied_changes)
            return (
                f"Based on the observed relationship in the available data, adjusting {levers} is estimated to change the target metric. "
                "This is a model-based estimate, not a causal guarantee. "
                "A controlled rollout of the selected adjustments is recommended in key segments before applying changes across the full dataset."
            )
        metrics = ", ".join(m["column"] for m in list(affected_metrics_map.values())[:3])
        return (
            f"Based on the observed relationship in the available data, the selected adjustment(s) are estimated to impact {metrics}. "
            "This is a model-based estimate, not a causal guarantee. "
            "A controlled rollout of the selected adjustments is recommended in key segments before applying changes across the full dataset."
        )
