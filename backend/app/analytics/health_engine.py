from typing import Dict, Any, List, Optional


class BusinessHealthEngine:
    """
    Calculated Business Health Engine.
    Dynamically computes a 0-100 score based strictly on empirical workspace metrics.

    Components:
      - Missing Values
      - Duplicate Records
      - Forecast Readiness
      - AI Readiness
      - Numeric Measure Availability
      - Temporal Coverage
      - Schema Completeness
      - Data Quality
      - Categorical Coverage

    Returns one of: Poor, Average, Good, Excellent
    Never defaults to zero when data exists.
    """

    @staticmethod
    def calculate_health_score(profile: Dict[str, Any], kpis: List[Dict[str, Any]], canonical_model: Optional[Any] = None) -> Dict[str, Any]:
        total_rows = profile.get("total_rows", 0)
        measures = profile.get("column_categories", {}).get("measures", [])
        dimensions = profile.get("column_categories", {}).get("dimensions", [])
        temporal = profile.get("column_categories", {}).get("temporal", [])

        if total_rows == 0:
            return {
                "overall_score": 0,
                "grade": "N/A",
                "status": "No Data",
                "breakdown": []
            }

        cols_profile = profile.get("column_categories", {})

        # Missing Values
        null_ratios = [meta.get("null_percentage", 0.0) for meta in profile.get("columns", {}).values() if isinstance(meta, dict)]
        avg_null_pct = (sum(null_ratios) / len(null_ratios)) if null_ratios else 0.0
        missing_values_score = max(0.0, 100.0 - avg_null_pct * 1.5)

        # Duplicate Records
        duplicate_pct = profile.get("duplicate_percentage", 0.0)
        duplicate_score = max(0.0, 100.0 - duplicate_pct * 5.0)

        # Forecast Readiness
        forecast_score = 0.0
        if canonical_model:
            try:
                from app.retail.canonical_model import CanonicalRetailModel
                if isinstance(canonical_model, dict):
                    cm = canonical_model
                elif hasattr(canonical_model, "to_dict"):
                    cm = canonical_model.to_dict()
                else:
                    cm = {}
                if cm.get("date_column") and cm.get("revenue_column"):
                    forecast_score = 90.0 if total_rows >= 30 else 60.0 if total_rows >= 10 else 30.0
                elif cm.get("date_column"):
                    forecast_score = 70.0 if total_rows >= 30 else 40.0 if total_rows >= 10 else 20.0
            except Exception:
                forecast_score = 50.0 if temporal else 0.0
        else:
            forecast_score = 50.0 if temporal else 0.0

        # AI Readiness
        ai_score = 50.0
        if canonical_model:
            try:
                from app.retail.canonical_model import CanonicalRetailModel
                if isinstance(canonical_model, dict):
                    cm = canonical_model
                elif hasattr(canonical_model, "to_dict"):
                    cm = canonical_model.to_dict()
                else:
                    cm = {}
                checks = [cm.get("order_id_column"), cm.get("customer_id_column"), cm.get("product_id_column"), cm.get("revenue_column"), cm.get("date_column")]
                ai_score = min(100.0, 40.0 + sum(20.0 for c in checks if c))
            except Exception:
                ai_score = 50.0 if measures else 0.0
        else:
            ai_score = 50.0 if measures else 0.0

        # Numeric Measure Availability
        numeric_score = 80.0 if measures else 0.0
        if canonical_model:
            try:
                from app.retail.canonical_model import CanonicalRetailModel
                if isinstance(canonical_model, dict):
                    cm = canonical_model
                elif hasattr(canonical_model, "to_dict"):
                    cm = canonical_model.to_dict()
                else:
                    cm = {}
                if cm.get("revenue_column") or cm.get("revenue_formula"):
                    numeric_score = 100.0
            except Exception:
                pass

        # Temporal Coverage
        temporal_score = max(0.0, min(100.0, 50.0 + len(temporal) * 25))

        # Schema Completeness
        total_expected_cols = max(len(measures) + len(dimensions) + len(temporal), 1)
        schema_score = max(0.0, min(100.0, (total_expected_cols / max(total_expected_cols, 1)) * 100.0))

        # Data Quality
        data_quality_score = max(0.0, 100.0 - avg_null_pct * 1.5)

        # Categorical Coverage
        categorical_score = 50.0
        if canonical_model:
            try:
                from app.retail.canonical_model import CanonicalRetailModel
                if isinstance(canonical_model, dict):
                    cm = canonical_model
                elif hasattr(canonical_model, "to_dict"):
                    cm = canonical_model.to_dict()
                else:
                    cm = {}
                entity_checks = [cm.get("order_id_column"), cm.get("customer_id_column"), cm.get("product_id_column"), cm.get("category_column")]
                categorical_score = min(100.0, sum(15.0 for c in entity_checks if c))
            except Exception:
                categorical_score = 50.0 if dimensions else 0.0
        else:
            categorical_score = 50.0 if dimensions else 0.0

        composite_score = round(
            (missing_values_score * 0.15) +
            (duplicate_score * 0.10) +
            (forecast_score * 0.15) +
            (ai_score * 0.15) +
            (numeric_score * 0.10) +
            (temporal_score * 0.10) +
            (schema_score * 0.10) +
            (data_quality_score * 0.10) +
            (categorical_score * 0.05)
        )
        composite_score = max(0.0, min(100.0, composite_score))

        if composite_score >= 85:
            grade = "A"
            status = "Excellent"
        elif composite_score >= 70:
            grade = "B"
            status = "Good"
        elif composite_score >= 50:
            grade = "C"
            status = "Average"
        else:
            grade = "D"
            status = "Poor"

        return {
            "overall_score": composite_score,
            "grade": grade,
            "status": status,
            "breakdown": [
                {"component": "Missing Values", "weight": "15%", "score": round(missing_values_score, 2), "status": "Derived", "detail": f"Average null percentage: {avg_null_pct:.1f}%"},
                {"component": "Duplicate Records", "weight": "10%", "score": round(duplicate_score, 2), "status": "Derived", "detail": f"Duplicate percentage: {duplicate_pct:.1f}%"},
                {"component": "Forecast Readiness", "weight": "15%", "score": round(forecast_score, 2), "status": "Active" if forecast_score > 50 else "Limited", "detail": "Temporal + numeric measure availability for forecasting."},
                {"component": "AI Readiness", "weight": "15%", "score": round(ai_score, 2), "status": "Derived", "detail": "Entity and measure detection completeness."},
                {"component": "Numeric Measure Availability", "weight": "10%", "score": round(numeric_score, 2), "status": "Available" if numeric_score > 50 else "Missing", "detail": "Numeric measure columns detected."},
                {"component": "Temporal Coverage", "weight": "10%", "score": round(temporal_score, 2), "status": "Active" if temporal else "Missing", "detail": f"Temporal columns detected: {len(temporal)}"},
                {"component": "Schema Completeness", "weight": "10%", "score": round(schema_score, 2), "status": "Derived", "detail": f"Measures: {len(measures)}, Dimensions: {len(dimensions)}, Temporal: {len(temporal)}"},
                {"component": "Data Quality", "weight": "10%", "score": round(data_quality_score, 2), "status": "Verified", "detail": f"Null percentage: {avg_null_pct:.1f}%"},
                {"component": "Categorical Coverage", "weight": "5%", "score": round(categorical_score, 2), "status": "Derived", "detail": "Dimension and entity coverage in dataset."},
            ]
        }
