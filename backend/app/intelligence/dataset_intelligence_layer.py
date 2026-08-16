from __future__ import annotations

from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import UTC, datetime

from app.intelligence.schemas import (
    ColumnIntelligence,
    DataQualityIntelligence,
    DatasetIntelligenceProfile,
    DatasetIntelligenceResult,
    CapabilityMatrix,
    MLRecommendation,
)
from app.ingestion.semantic_profiler import SemanticDataProfiler
from app.semantic_model.engine import SemanticModelEngine, build_semantic_model
from app.semantic_model.cache import get_cache
from app.database.mongodb import workspaces as mongo_workspaces
from app.logging.logger import get_logger

logger = get_logger(__name__)


class DatasetIntelligenceLayer:
    """
    DecisionLens Dataset Intelligence Layer.

    This is the SINGLE entry point for understanding any uploaded dataset.
    It profiles the dataset ONCE, builds the semantic model, generates
    the intelligence profile, stores it in MongoDB, and caches it.

    Every downstream feature (Analytics, Dashboard, Reports, Copilot,
    Forecasting, Recommendations) MUST consume this layer's output.
    No feature should inspect raw CSV/Parquet directly.
    """

    _instance: Optional[DatasetIntelligenceLayer] = None

    def __init__(self):
        self._engine = SemanticModelEngine()
        self._cache = get_cache()

    @classmethod
    def get_instance(cls) -> DatasetIntelligenceLayer:
        if cls._instance is None:
            cls._instance = DatasetIntelligenceLayer()
        return cls._instance

    @classmethod
    def analyze(
        cls,
        workspace_id: str,
        parquet_path: Path,
        force_rebuild: bool = False,
    ) -> DatasetIntelligenceResult:
        instance = cls.get_instance()
        return instance._analyze(workspace_id, parquet_path, force_rebuild)

    def _analyze(
        self,
        workspace_id: str,
        parquet_path: Path,
        force_rebuild: bool = False,
    ) -> DatasetIntelligenceResult:
        path_str = str(parquet_path)
        mtime = 0.0
        try:
            mtime = parquet_path.stat().st_mtime
        except Exception:
            pass

        cache_key = f"intelligence:{workspace_id}:{mtime}"
        if not force_rebuild:
            cached = self._cache.get(workspace_id, mtime, include_lineage=False)
            if cached is not None:
                intelligence_data = cached.get("_intelligence")
                if intelligence_data is not None:
                    return self._dict_to_result(workspace_id, intelligence_data)

        try:
            profile = SemanticDataProfiler.profile(parquet_path)
        except Exception as e:
            logger.error("[DatasetIntelligence] Profiling failed: %s", e)
            return DatasetIntelligenceResult(
                workspace_id=workspace_id,
                status="ERROR",
                error=f"Profiling failed: {str(e)}",
            )

        columns = self._build_column_intelligence(profile)
        data_quality = self._build_data_quality(profile)
        intelligence_profile = self._build_intelligence_profile(workspace_id, parquet_path, profile)

        try:
            semantic_model = build_semantic_model(
                workspace_id=workspace_id,
                force_rebuild=force_rebuild,
                include_lineage=False,
                precomputed_profiles={str(parquet_path): profile},
            )
        except Exception as e:
            logger.warning("[DatasetIntelligence] Semantic model build failed: %s", e)
            semantic_model = {}

        domain = semantic_model.get("domain") or intelligence_profile.detected_domain or "Generic Business"
        domain_confidence = semantic_model.get("domain_confidence") or intelligence_profile.confidence_pct or 50.0
        domain_reason = semantic_model.get("domain_reason") or intelligence_profile.reasoning or ""
        dataset_type = semantic_model.get("dataset_type", "Unknown")

        result = DatasetIntelligenceResult(
            workspace_id=workspace_id,
            status="READY",
            domain=domain,
            domain_confidence=domain_confidence,
            domain_reason=domain_reason,
            dataset_type=dataset_type,
            generated_at=datetime.now(UTC).isoformat(),
            columns=columns,
            data_quality=data_quality,
            profile=intelligence_profile,
            semantic_model=semantic_model,
        )

        try:
            self._persist_to_mongodb(workspace_id, result)
        except Exception as e:
            logger.warning("[DatasetIntelligence] MongoDB persist failed: %s", e)

        try:
            self._cache_intelligence(workspace_id, mtime, result)
        except Exception as e:
            logger.warning("[DatasetIntelligence] Cache write failed: %s", e)

        return result

    def _build_column_intelligence(self, profile: Dict[str, Any]) -> List[ColumnIntelligence]:
        columns: List[ColumnIntelligence] = []
        total_rows = profile.get("total_rows", 0)
        for col_name, col_profile in profile.get("columns", {}).items():
            data_type = col_profile.get("data_type", "VARCHAR")
            category = col_profile.get("category", "dimension")
            col_lower = col_name.lower()

            semantic_type = "dimension"
            business_role = "dimension"
            unit = ""
            is_measure = category == "measure"
            is_dimension = category == "dimension"
            is_temporal = category == "temporal"
            is_identifier = category == "identifier"

            if is_temporal:
                semantic_type = "temporal"
                business_role = "temporal"
            elif is_measure:
                semantic_type = "measure"
                business_role = "measure"
                if any(k in col_lower for k in ["price", "cost", "salary", "income", "fee", "tax", "amount", "revenue", "balance", "payout", "premium", "claim"]):
                    semantic_type = "currency"
                    unit = "currency"
                elif any(k in col_lower for k in ["percentage", "rate", "ratio", "nps", "ctr", "cpc", "cpa", "roas"]):
                    semantic_type = "percentage"
                    unit = "percent"
            elif is_identifier:
                semantic_type = "identifier"
                business_role = "identifier"
                if "customer" in col_lower:
                    semantic_type = "customer_id"
                elif "employee" in col_lower or "staff" in col_lower:
                    semantic_type = "employee_id"
                elif "user" in col_lower:
                    semantic_type = "user_id"
                elif "product" in col_lower or "item" in col_lower or "sku" in col_lower:
                    semantic_type = "product_id"
                elif "order" in col_lower or "transaction" in col_lower or "invoice" in col_lower:
                    semantic_type = "transaction_id"
                elif "session" in col_lower:
                    semantic_type = "session_id"
            else:
                if any(k in col_lower for k in ["email"]):
                    semantic_type = "email"
                elif any(k in col_lower for k in ["phone", "mobile", "telephone"]):
                    semantic_type = "phone"
                elif any(k in col_lower for k in ["ip_address", "src_ip", "dst_ip", "source_ip", "destination_ip"]):
                    semantic_type = "ip_address"
                elif any(k in col_lower for k in ["mac_address", "mac_addr", "mac"]):
                    semantic_type = "mac_address"
                elif any(k in col_lower for k in ["hostname", "host_name", "server"]):
                    semantic_type = "hostname"
                elif any(k in col_lower for k in ["severity", "critical", "high", "medium", "low"]):
                    semantic_type = "severity"
                elif any(k in col_lower for k in ["status", "state", "phase"]):
                    semantic_type = "status"
                elif any(k in col_lower for k in ["threat", "attack", "malicious"]):
                    semantic_type = "threat"
                elif any(k in col_lower for k in ["vulnerability", "cve", "vulnerability_id"]):
                    semantic_type = "vulnerability"
                elif any(k in col_lower for k in ["asset", "device_id", "equipment"]):
                    semantic_type = "asset"
                elif any(k in col_lower for k in ["device", "sensor", "iot", "gateway"]):
                    semantic_type = "device"
                elif any(k in col_lower for k in ["log_type", "event_type", "action"]):
                    semantic_type = "log_type"
                elif any(k in col_lower for k in ["cve_", "cve-", "cve_id"]):
                    semantic_type = "cve"
                elif any(k in col_lower for k in ["mitre", "technique", "tactic"]):
                    semantic_type = "mitre_technique"
                elif data_type.upper() in ("BOOLEAN", "BOOL"):
                    semantic_type = "boolean"
                elif is_dimension and col_profile.get("distinct_count", 0) > 10:
                    semantic_type = "categorical"

            confidence = self._compute_column_confidence(category, col_profile, total_rows)

            columns.append(ColumnIntelligence(
                name=col_name,
                data_type=data_type,
                semantic_type=semantic_type,
                business_role=business_role,
                unit=unit,
                is_measure=is_measure or semantic_type in ("currency", "percentage"),
                is_dimension=is_dimension or semantic_type in ("categorical", "free_text"),
                is_temporal=is_temporal,
                is_identifier=is_identifier,
                confidence=confidence,
                null_percentage=col_profile.get("null_percentage", 0.0),
                distinct_count=col_profile.get("distinct_count", 0),
            ))

        return columns

    @staticmethod
    def _compute_column_confidence(category: str, col_profile: Dict[str, Any], total_rows: int) -> float:
        null_pct = col_profile.get("null_percentage", 0.0)
        distinct_count = col_profile.get("distinct_count", 0)

        base = 0.7
        if category == "measure":
            base = 0.85
        elif category == "identifier":
            base = 0.80
        elif category == "temporal":
            base = 0.85

        if total_rows > 0 and null_pct > 20:
            base -= 0.15
        elif total_rows > 0 and null_pct > 10:
            base -= 0.10

        if category == "identifier" and distinct_count > 0:
            uniqueness_ratio = distinct_count / max(total_rows, 1)
            if uniqueness_ratio < 0.5:
                base -= 0.10

        return max(0.5, min(0.95, base))

    def _build_data_quality(self, profile: Dict[str, Any]) -> DataQualityIntelligence:
        all_columns = list(profile.get("columns", {}).values())
        if not all_columns:
            return DataQualityIntelligence()

        total_cells = sum(c.get("distinct_count", 0) + c.get("null_count", 0) for c in all_columns)
        total_nulls = sum(c.get("null_count", 0) for c in all_columns)
        null_pct = (total_nulls / max(total_cells, 1)) * 100

        completeness = max(0.0, 100.0 - null_pct)

        uniqueness_scores = []
        for c in all_columns:
            total = c.get("distinct_count", 0) + c.get("null_count", 0)
            if total > 0:
                uniqueness_scores.append((c.get("distinct_count", 0) / total) * 100)
        uniqueness = sum(uniqueness_scores) / len(uniqueness_scores) if uniqueness_scores else 100.0

        consistency = max(0.0, min(100.0, 100.0 - (null_pct * 0.5)))
        validity = max(0.0, min(100.0, 100.0 - (null_pct * 0.3)))
        accuracy = max(0.0, min(100.0, completeness * 0.9 + uniqueness * 0.1))

        issues = []
        if null_pct > 10:
            issues.append(f"High null percentage detected: {null_pct:.1f}%")
        if uniqueness < 50:
            issues.append(f"Low uniqueness detected: {uniqueness:.1f}%")

        overall = (completeness * 0.35 + uniqueness * 0.25 + consistency * 0.2 + validity * 0.1 + accuracy * 0.1)
        overall = max(0.0, min(100.0, overall))

        return DataQualityIntelligence(
            overall_score=round(overall, 2),
            completeness=round(completeness, 2),
            uniqueness=round(uniqueness, 2),
            consistency=round(consistency, 2),
            validity=round(validity, 2),
            accuracy=round(accuracy, 2),
            null_percentage=round(null_pct, 2),
            duplicate_percentage=0.0,
            outlier_percentage=0.0,
            issues=issues,
        )

    def _build_intelligence_profile(
        self,
        workspace_id: str,
        parquet_path: Path,
        profile: Dict[str, Any],
    ) -> DatasetIntelligenceProfile:
        try:
            from app.ingestion.intelligence_engine import DatasetIntelligenceEngine
            raw = DatasetIntelligenceEngine.analyze_dataset(parquet_path)
            if raw.get("workspace_exists"):
                capability_matrix = []
                for cap in raw.get("capability_matrix", []):
                    capability_matrix.append(CapabilityMatrix(
                        capability=cap.get("capability", ""),
                        available=cap.get("available", False),
                        confidence=str(cap.get("confidence", "0%")),
                        reason=cap.get("reason", ""),
                    ))

                ml_recommendations = []
                for rec in raw.get("ml_recommendations", []):
                    ml_recommendations.append(MLRecommendation(
                        model=rec.get("model", ""),
                        algorithm=rec.get("algorithm", ""),
                        status=rec.get("status", "Applicable"),
                        reason=rec.get("reason", ""),
                    ))

                return DatasetIntelligenceProfile(
                    detected_domain=raw.get("domain", "Generic Business"),
                    confidence_pct=raw.get("confidence", 0.0),
                    reasoning=raw.get("reason", ""),
                    matched_columns=raw.get("matched_columns", []),
                    detected_entities=raw.get("entities", []),
                    detected_measures=raw.get("measures", []),
                    detected_dimensions=raw.get("dimensions", []),
                    detected_temporal=raw.get("temporal", []),
                    total_records=raw.get("total_rows", 0),
                    total_columns=raw.get("total_columns", 0),
                    capability_matrix=capability_matrix,
                    business_questions=raw.get("business_questions", []),
                    ml_recommendations=ml_recommendations,
                )
        except Exception as e:
            logger.warning("[DatasetIntelligence] Profile build failed: %s", e)

        column_categories = profile.get("column_categories", {})
        return DatasetIntelligenceProfile(
            detected_domain="Generic Business",
            confidence_pct=50.0,
            reasoning="Fallback classification from profiler",
            matched_columns=[],
            detected_entities=[],
            detected_measures=column_categories.get("measures", []),
            detected_dimensions=column_categories.get("dimensions", []),
            detected_temporal=column_categories.get("temporal", []),
            total_records=profile.get("total_rows", 0),
            total_columns=profile.get("total_columns", 0),
        )

    def _persist_to_mongodb(self, workspace_id: str, result: DatasetIntelligenceResult):
        try:
            update_doc = {
                "$set": {
                    "workspace_id": workspace_id,
                    "intelligence_status": result.status,
                    "intelligence_domain": result.domain,
                    "intelligence_domain_confidence": result.domain_confidence,
                    "intelligence_domain_reason": result.domain_reason,
                    "intelligence_dataset_type": result.dataset_type,
                    "intelligence_generated_at": result.generated_at,
                    "intelligence_columns": [c.__dict__ for c in result.columns],
                    "intelligence_data_quality": result.data_quality.__dict__,
                    "intelligence_profile": result.profile.to_dict(),
                    "intelligence_semantic_model": result.semantic_model,
                }
            }
            mongo_workspaces.update_one(
                {"workspace_id": workspace_id},
                update_doc,
                upsert=True,
            )
        except Exception as e:
            logger.warning("[DatasetIntelligence] MongoDB persist failed: %s", e)

    def _cache_intelligence(self, workspace_id: str, mtime: float, result: DatasetIntelligenceResult):
        try:
            cached_model = self._cache.get(workspace_id, mtime, include_lineage=False)
            if cached_model is not None:
                cached_model["_intelligence"] = result.to_dict()
                self._cache.put(workspace_id, mtime, cached_model, include_lineage=False)
        except Exception as e:
            logger.warning("[DatasetIntelligence] Cache update failed: %s", e)

    @staticmethod
    def _dict_to_result(workspace_id: str, data: Dict[str, Any]) -> DatasetIntelligenceResult:
        try:
            columns = [
                ColumnIntelligence(
                    name=c.get("name", ""),
                    data_type=c.get("data_type", "VARCHAR"),
                    semantic_type=c.get("semantic_type", "dimension"),
                    business_role=c.get("business_role", "dimension"),
                    unit=c.get("unit", ""),
                    is_measure=c.get("is_measure", False),
                    is_dimension=c.get("is_dimension", False),
                    is_temporal=c.get("is_temporal", False),
                    is_identifier=c.get("is_identifier", False),
                    confidence=c.get("confidence", 0.0),
                    null_percentage=c.get("null_percentage", 0.0),
                    distinct_count=c.get("distinct_count", 0),
                )
                for c in data.get("columns", [])
            ]

            dq_data = data.get("data_quality", {})
            data_quality = DataQualityIntelligence(
                overall_score=dq_data.get("overall_score", 100.0),
                completeness=dq_data.get("completeness", 100.0),
                uniqueness=dq_data.get("uniqueness", 100.0),
                consistency=dq_data.get("consistency", 100.0),
                validity=dq_data.get("validity", 100.0),
                accuracy=dq_data.get("accuracy", 100.0),
                null_percentage=dq_data.get("null_percentage", 0.0),
                duplicate_percentage=dq_data.get("duplicate_percentage", 0.0),
                outlier_percentage=dq_data.get("outlier_percentage", 0.0),
                issues=dq_data.get("issues", []),
            )

            profile_data = data.get("profile", {})
            capability_matrix = [
                CapabilityMatrix(
                    capability=c.get("capability", ""),
                    available=c.get("available", False),
                    confidence=str(c.get("confidence", "0%")),
                    reason=c.get("reason", ""),
                )
                for c in profile_data.get("capability_matrix", [])
            ]
            ml_recommendations = [
                MLRecommendation(
                    model=m.get("model", ""),
                    algorithm=m.get("algorithm", ""),
                    status=m.get("status", "Applicable"),
                    reason=m.get("reason", ""),
                )
                for m in profile_data.get("ml_recommendations", [])
            ]

            profile = DatasetIntelligenceProfile(
                detected_domain=profile_data.get("detected_domain", "Generic Business"),
                confidence_pct=profile_data.get("confidence_pct", 0.0),
                reasoning=profile_data.get("reasoning", ""),
                matched_columns=profile_data.get("matched_columns", []),
                detected_entities=profile_data.get("detected_entities", []),
                detected_measures=profile_data.get("detected_measures", []),
                detected_dimensions=profile_data.get("detected_dimensions", []),
                detected_temporal=profile_data.get("detected_temporal", []),
                total_records=profile_data.get("total_records", 0),
                total_columns=profile_data.get("total_columns", 0),
                capability_matrix=capability_matrix,
                business_questions=profile_data.get("business_questions", []),
                ml_recommendations=ml_recommendations,
            )

            return DatasetIntelligenceResult(
                workspace_id=workspace_id,
                status=data.get("status", "READY"),
                domain=data.get("domain", "Generic Business"),
                domain_confidence=data.get("domain_confidence", 50.0),
                domain_reason=data.get("domain_reason", ""),
                dataset_type=data.get("dataset_type", "Unknown"),
                generated_at=data.get("generated_at", ""),
                columns=columns,
                data_quality=data_quality,
                profile=profile,
                semantic_model=data.get("semantic_model", {}),
                error=data.get("error"),
            )
        except Exception as e:
            logger.error("[DatasetIntelligence] Failed to deserialize cached result: %s", e)
            return DatasetIntelligenceResult(
                workspace_id=workspace_id,
                status="ERROR",
                error=f"Failed to deserialize cached result: {str(e)}",
            )

    @classmethod
    def get_cached(cls, workspace_id: str) -> Optional[DatasetIntelligenceResult]:
        instance = cls.get_instance()
        try:
            from app.database.storage import STORAGE_DIR
            from app.semantic_model.engine import _workspace_prefix_for

            clean_target = _workspace_prefix_for(workspace_id)
            parquet_dir = STORAGE_DIR
            files = []
            if parquet_dir.exists():
                for p in parquet_dir.glob("*.parquet"):
                    if p.name.startswith("unified_") or p.name.startswith("tmp_"):
                        continue
                    clean_pname = p.stem.lower().replace("-", "_")
                    if clean_target in clean_pname or clean_pname.startswith(clean_target):
                        files.append(p)

            if not files:
                return None

            mtime = max((p.stat().st_mtime for p in files), default=0.0)
            cached = instance._cache.get(workspace_id, mtime, include_lineage=False)
            if cached is not None:
                intelligence_data = cached.get("_intelligence")
                if intelligence_data is not None:
                    return instance._dict_to_result(workspace_id, intelligence_data)
        except Exception as e:
            logger.warning("[DatasetIntelligence] Cache retrieval failed: %s", e)
        return None

    @classmethod
    def invalidate_cache(cls, workspace_id: Optional[str] = None):
        instance = cls.get_instance()
        instance._cache.invalidate(workspace_id)
