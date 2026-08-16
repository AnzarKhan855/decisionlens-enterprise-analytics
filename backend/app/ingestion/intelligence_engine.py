import re
from typing import Dict, Any, List, Optional
from pathlib import Path
from app.database.duckdb_engine import DuckDBEngine
from app.ingestion.domain_classifier import DatasetDomainClassifier
from app.semantic_model.entity_detector import ENTITY_KEYWORDS, detect_business_entities, detect_entity_confidence


class DatasetIntelligenceEngine:
    """
    DecisionLens v10.0 Universal AI Dataset Understanding Engine.
    Discovers schema structures, entities, domain classification, AI capabilities,
    tailored questions, ML model suitability, and explicit detection rationales.
    """

    _INTELLIGENCE_CACHE: Dict[str, Any] = {}

    @classmethod
    def analyze_dataset(cls, parquet_path: Path, filename: Optional[str] = None) -> Dict[str, Any]:
        try:
            mtime = parquet_path.stat().st_mtime
        except Exception:
            mtime = 0
        cache_key = f"{parquet_path}_{mtime}"
        if cache_key in cls._INTELLIGENCE_CACHE:
            return cls._INTELLIGENCE_CACHE[cache_key]

        path_str = str(parquet_path).replace("\\", "/")
        con = DuckDBEngine.get_connection()
        try:
            schema_rows = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{path_str}')").fetchall()
            total_rows = con.execute(f"SELECT COUNT(*) FROM read_parquet('{path_str}')").fetchone()[0]
            columns_meta = {r[0]: (r[1] if len(r) > 1 else "VARCHAR") for r in schema_rows}
        except Exception as e:
            return {
                "error": f"Failed to analyze parquet dataset: {str(e)}",
                "workspace_exists": False
            }
        finally:
            con.close()

        raw_columns = list(columns_meta.keys())
        norm_columns = [re.sub(r"[^a-z0-9_]", "", c.lower()) for c in raw_columns]

        classification = DatasetDomainClassifier.classify(parquet_path, filename)
        domain = classification["domain"]
        confidence = classification["confidence"]
        reason = classification["reason"]
        matched_cols = classification["matched_columns"]

        entities_found = detect_business_entities(
            filename or parquet_path.stem,
            raw_columns,
            total_rows
        )

        NUMERIC_TYPES = {"BIGINT", "INTEGER", "SMALLINT", "TINYINT", "DOUBLE", "FLOAT", "DECIMAL", "HUGEINT", "REAL"}
        DATE_TYPES = {"DATE", "TIMESTAMP", "TIMESTAMPTZ"}

        measures = []
        dimensions = []
        temporal = []

        for col, dtype in columns_meta.items():
            dtype_up = dtype.upper().split("(")[0]
            col_lower = col.lower()

            if dtype_up in DATE_TYPES or any(k in col_lower for k in ["date", "timestamp", "time", "year", "month"]):
                temporal.append(col)
            elif dtype_up in NUMERIC_TYPES and not any(k in col_lower for k in ["_id", "code", "index", "phone", "zip"]):
                measures.append(col)
            else:
                dimensions.append(col)

        capability_matrix = [
            {
                "capability": "Time-Series Forecasting",
                "available": len(temporal) > 0 and len(measures) > 0,
                "confidence": f"{95 if len(temporal) > 0 else 0}%",
                "reason": f"Detected {len(temporal)} temporal column(s) ({', '.join(temporal[:2])}) and {len(measures)} numeric measure(s)." if len(temporal) > 0 else "No compatible date/timestamp columns found."
            },
            {
                "capability": "Anomaly & Outlier Detection",
                "available": total_rows >= 10,
                "confidence": f"{min(90 + total_rows // 1000, 99)}%",
                "reason": f"Sufficient record depth ({total_rows:,} rows) for statistical z-score and Isolation Forest outlier detection."
            },
            {
                "capability": "Classification & Risk Scoring",
                "available": len(dimensions) > 0,
                "confidence": f"{min(80 + len(dimensions) * 5, 99)}%",
                "reason": f"Identified {len(dimensions)} categorical dimension(s) suitable for target label supervised classification."
            },
            {
                "capability": "Regression Analysis",
                "available": len(measures) >= 2,
                "confidence": f"{min(80 + len(measures) * 5, 99)}%" if len(measures) >= 2 else "0%",
                "reason": f"Found {len(measures)} numeric measure columns for multivariate linear/nonlinear regression modelling." if len(measures) >= 2 else "Requires at least 2 numeric measure variables."
            },
            {
                "capability": "Entity & Cohort Segmentation",
                "available": len(entities_found) > 0 and len(dimensions) > 0,
                "confidence": f"{min(80 + len(entities_found) * 5, 99)}%",
                "reason": f"Detected key business entities ({', '.join(entities_found[:2])}) for k-means cluster profiling."
            },
            {
                "capability": "Pattern & Relationship Matching",
                "available": domain not in ["Generic Business", "Unknown Dataset"],
                "confidence": f"{min(75 + len(entities_found) * 5, 99)}%" if domain not in ["Generic Business", "Unknown Dataset"] else "40%",
                "reason": f"Dataset domain '{domain}' supports domain-specific heuristic rules." if domain not in ["Generic Business", "Unknown Dataset"] else "Limited domain-specific indicators."
            }
        ]

        business_questions = cls._generate_business_questions(domain, entities_found, measures, dimensions)
        ml_recommendations = cls._generate_ml_recommendations(domain, entities_found, measures, dimensions)

        detection_panel = {
            "detected_domain": domain,
            "confidence_pct": confidence,
            "reasoning": reason,
            "matched_columns": matched_cols,
            "detected_entities": entities_found,
            "detected_measures": measures,
            "detected_dimensions": dimensions,
            "detected_temporal": temporal,
            "total_records": total_rows
        }

        res_dict = {
            "workspace_exists": True,
            "domain": domain,
            "confidence": confidence,
            "reason": reason,
            "entities": entities_found,
            "measures": measures,
            "dimensions": dimensions,
            "temporal": temporal,
            "total_rows": total_rows,
            "total_columns": len(raw_columns),
            "capability_matrix": capability_matrix,
            "business_questions": business_questions,
            "ml_recommendations": ml_recommendations,
            "detection_panel": detection_panel
        }
        cls._INTELLIGENCE_CACHE[cache_key] = res_dict
        return res_dict

    @classmethod
    def _generate_business_questions(cls, domain: str, entities: List[str], measures: List[str], dimensions: List[str]) -> List[str]:
        if domain == "Education":
            return [
                "Which students are at highest risk of academic failure?",
                "Which subjects exhibit the highest student failure rate?",
                "How does attendance percentage correlate with final exam marks?",
                "What is the fee collection status across departments and semesters?",
                "Which classes achieve the highest average academic performance?"
            ]
        elif domain == "Healthcare":
            return [
                "Which patient diagnoses account for the highest readmission rate?",
                "What is the average length of stay by clinical department?",
                "Which hospital wards show signs of capacity overload?",
                "How do treatment outcomes vary by patient age cohort?",
                "Which emergency admission types correlate with high mortality risk?"
            ]
        elif domain == "Cybersecurity":
            return [
                "Which source IP addresses generated the highest volume of malicious attacks?",
                "What are the top targeted destination ports and host assets?",
                "Which attack signatures present critical severity threat scores?",
                "How are security event volumes distributed over time?",
                "Which hosts exhibit unusual protocol communication anomalies?"
            ]
        elif domain == "Finance & Banking":
            return [
                "Which account types generate the highest net transaction volume?",
                "What is the portfolio default risk distribution across credit score tiers?",
                "Where are non-performing loan assets concentrated?",
                "What are the monthly cash flow trend projections?",
                "Which transaction types display anomalous fraud indicators?"
            ]
        elif domain == "Human Resources":
            return [
                "Which employee departments show the highest attrition risk?",
                "How does tenure length correlate with performance evaluation ratings?",
                "What is the salary distribution breakdown across job designations?",
                "Which teams experience the highest absenteeism rates?",
                "What is the projected headcount growth over the next quarter?"
            ]

        primary_dim = dimensions[0] if dimensions else "category"
        primary_meas = measures[0] if measures else "value"
        return [
            f"Which {primary_dim} generates the highest overall {primary_meas}?",
            f"What is the distribution of records across {primary_dim} segments?",
            f"How do {primary_meas} trends vary over time?",
            f"Which outliers and statistical anomalies exist in {primary_meas}?",
            "What actionable operational optimizations can be implemented?"
        ]

    @classmethod
    def _generate_ml_recommendations(cls, domain: str, entities: List[str], measures: List[str], dimensions: List[str]) -> List[Dict[str, Any]]:
        if domain == "Education":
            return [
                {"model": "Student Performance Classifier", "algorithm": "XGBoost Classifier", "status": "Applicable", "reason": "Predicts student pass/fail outcome based on attendance and test scores."},
                {"model": "Dropout Risk Assessment", "algorithm": "Random Forest Regressor", "status": "Applicable", "reason": "Identifies early warning indicators for student retention intervention."},
                {"model": "Fee Default Forecaster", "algorithm": "Logistic Regression", "status": "Applicable", "reason": "Forecasts tuition payment default probabilities."}
            ]
        elif domain == "Healthcare":
            return [
                {"model": "Readmission Risk Predictor", "algorithm": "LightGBM Classifier", "status": "Applicable", "reason": "Predicts 30-day clinical patient readmission risk."},
                {"model": "Length of Stay Forecaster", "algorithm": "Gradient Boosting Regressor", "status": "Applicable", "reason": "Forecasts expected inpatient bed occupancy duration."}
            ]
        elif domain == "Cybersecurity":
            return [
                {"model": "SOC Anomaly Detector", "algorithm": "Isolation Forest", "status": "Applicable", "reason": "Detects abnormal network packet flows and zero-day threat patterns."},
                {"model": "Threat Severity Classifier", "algorithm": "Extra Trees Classifier", "status": "Applicable", "reason": "Ranks incoming SIEM log alerts by exploit severity score."}
            ]

        return [
            {"model": "Multivariate Trend Forecaster", "algorithm": "Prophet / ARIMA", "status": "Applicable" if measures else "Limited", "reason": "Forecasts primary metric trajectory over time."},
            {"model": "Cluster Segmentation Engine", "algorithm": "k-Means Clustering", "status": "Applicable" if dimensions else "Limited", "reason": "Groups records into cohesive operational cohorts."}
        ]
