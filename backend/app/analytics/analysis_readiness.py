from pathlib import Path
from typing import Dict, Any, List, Optional
from app.ingestion.semantic_profiler import SemanticDataProfiler

class AnalysisReadinessEngine:
    """
    Evaluates dataset readiness for business analytics.
    Calculates 0-100% Analysis Readiness Score and identifies available vs missing capabilities.
    """

    @classmethod
    def evaluate_readiness(
        cls,
        parquet_path: Path,
        semantic_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if not semantic_profile:
            semantic_profile = SemanticDataProfiler.profile(parquet_path)

        measures = semantic_profile["column_categories"].get("measures", [])
        dimensions = semantic_profile["column_categories"].get("dimensions", [])
        temporal = semantic_profile["column_categories"].get("temporal", [])
        columns = [c.lower() for c in semantic_profile.get("columns", {}).keys()]

        has_financial = any(k in c for c in measures for k in ["revenue", "sales", "profit", "cost", "amount", "price"])
        has_time_series = len(temporal) > 0
        has_entity = any(k in c for c in columns for k in ["id", "code", "key", "identifier"])
        has_location = any(k in c for c in columns for k in ["country", "state", "city", "region", "zip", "location"])
        has_category = any(k in c for c in columns for k in ["category", "type", "group", "segment", "class", "tier"])

        readiness_score = 0
        checks = []

        if has_financial:
            readiness_score += 35
            checks.append({"capability": "Financial & Operational Metrics", "available": True, "details": f"Found measures: {', '.join(measures[:3])}"})
        else:
            checks.append({"capability": "Financial & Operational Metrics", "available": False, "details": "No numeric measure columns detected."})

        if has_time_series:
            readiness_score += 25
            checks.append({"capability": "Time-Series Forecasting", "available": True, "details": f"Found date column: {temporal[0]}"})
        else:
            checks.append({"capability": "Time-Series Forecasting", "available": False, "details": "No timestamp column detected for predictive trends."})

        if has_entity:
            readiness_score += 15
            checks.append({"capability": "Entity & Cohort Analysis", "available": True, "details": "Found entity identifier columns."})
        else:
            checks.append({"capability": "Entity & Cohort Analysis", "available": False, "details": "No entity identifier columns present."})

        if has_location:
            readiness_score += 15
            checks.append({"capability": "Geographic Regional Analytics", "available": True, "details": "Found spatial/location fields."})
        else:
            checks.append({"capability": "Geographic Regional Analytics", "available": False, "details": "No geographic columns detected."})

        if has_category:
            readiness_score += 10
            checks.append({"capability": "Category Segmentation", "available": True, "details": "Found category/segment fields."})
        else:
            checks.append({"capability": "Category Segmentation", "available": False, "details": "No category or segment columns detected."})

        can_calculate_health = has_financial and (has_time_series or len(dimensions) > 0)

        return {
            "readiness_score": readiness_score,
            "readiness_level": "OPTIMAL" if readiness_score >= 70 else "MODERATE" if readiness_score >= 40 else "LIMITED",
            "can_calculate_health_score": can_calculate_health,
            "health_score_unavailable_reason": None if can_calculate_health else "Dataset lacks numeric measures or time-series columns required for Health Score.",
            "capabilities": checks
        }
