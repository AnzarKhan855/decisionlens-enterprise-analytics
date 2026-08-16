import json
from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path

from app.semantic_model.core import (
    SemanticModel,
    TableMetadata,
    TableRole,
    BusinessDomain,
    DatasetType,
    ColumnSemanticType,
    TimeGrain,
    PredictionTaskType,
    DataQualityDimension,
    AnomalyCategory,
    ColumnClassification,
    TimeIntelligence,
    DataQualityScores,
    PredictionPreparation,
    AnomalyPreparation,
)
from app.semantic_model.cache import SemanticModelCache, get_cache, invalidate_all_caches
from app.semantic_model.detector import classify_table, detect_specialized_table_type
from app.semantic_model.key_detector import detect_primary_keys, detect_foreign_keys_from_relationships, build_pk_lookup
from app.semantic_model.relationship_detector import discover_relationships
from app.semantic_model.hierarchy_detector import detect_hierarchies
from app.semantic_model.domain_detector import classify_domain, classify_dataset_type, BUSINESS_DOMAIN_TO_DATASET_TYPE
from app.semantic_model.entity_detector import detect_business_entities
from app.semantic_model.measure_detector import detect_measures
from app.semantic_model.time_detector import detect_time_columns
from app.semantic_model.diagram import generate_mermaid_diagram, generate_dot_diagram, generate_json_diagram
from app.semantic_model.lineage import generate_lineage, trace_column_lineage, impact_analysis
from app.semantic_model.glossary import generate_business_glossary
from app.semantic_model.optimization import (
    optimize_for_scale,
    get_optimized_table_list,
    estimate_memory_footprint,
)
from app.ingestion.workspace_discovery import WorkspaceDiscoveryEngine, clean_table_name
from app.ingestion.semantic_profiler import SemanticDataProfiler
from app.services.workspace_service import EnterpriseWorkspaceManager
from app.database.storage import STORAGE_DIR
from app.retail.canonical_model import build_canonical_model, CanonicalRetailModel


def _workspace_prefix_for(workspace_id: str) -> str:
    return workspace_id.lower().replace("-", "_")


def _strip_workspace_prefix(stem: str, workspace_id: str) -> str:
    prefix = _workspace_prefix_for(workspace_id) + "__"
    normalized_stem = stem.lower().replace("-", "_")
    if normalized_stem.startswith(prefix):
        return stem[len(prefix):]
    return stem


class SemanticModelEngine:
    """
    Enterprise Semantic Model Engine for DecisionLens.

    Automatically detects:
      - Fact Tables, Dimension Tables, Bridge Tables, Lookup Tables, Reference Tables
      - Primary Keys, Foreign Keys, Relationships
      - Measures, Hierarchies, Business Domains, Business Entities
      - Time Columns, Customer Tables, Revenue Tables, Inventory Tables

    Features:
      - Persistent file-based caching with TTL and LRU eviction
      - Cache invalidation on upload/delete events
      - Relationship diagram generation (Mermaid, DOT, JSON)
      - Column-level and table-level lineage
      - Business glossary generation
      - Enterprise-scale dataset optimizations
    """

    _LINEAGE_DIR = Path("storage/parquet/lineage")
    _GLOSSARY_FILE = Path("storage/parquet/business_glossary.json")
    _MODEL_META_FILE = Path("storage/parquet/semantic_model_versions.json")

    def __init__(self):
        self._cache = get_cache()
        self._ensure_dirs()

    def _ensure_dirs(self):
        self._LINEAGE_DIR.mkdir(parents=True, exist_ok=True)

    def build_semantic_model(
        self,
        workspace_id: Optional[str] = None,
        force_rebuild: bool = False,
        include_lineage: bool = True,
        precomputed_profiles: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        target_ws = workspace_id or EnterpriseWorkspaceManager.get_active_workspace_id() or "workspace-1"
        current_mtime = self._get_workspace_parquet_mtime(target_ws)
        include_lineage_flag = include_lineage

        cached = self._cache.get(target_ws, current_mtime, include_lineage_flag)
        if cached is not None and not force_rebuild:
            return cached

        parquet_files = self._discover_parquet_files(target_ws)

        if not parquet_files:
            empty = {
                "workspace_id": target_ws,
                "status": "NO_TABLES",
                "tables": [],
                "relationships": [],
                "lineage": None,
                "glossary": [],
                "summary": {},
            }
            self._cache.put(target_ws, current_mtime, empty, include_lineage_flag)
            return empty

        con = self._open_duckdb_connection()
        try:
            tables_meta = []
            tables_by_role = {
                "fact_tables": [],
                "dimension_tables": [],
                "lookup_tables": [],
                "reference_tables": [],
                "bridge_tables": [],
                "metadata_tables": [],
            }

            for pfile in parquet_files:
                if pfile.exists() and pfile.stat().st_size == 0:
                    continue
                raw_stem = _strip_workspace_prefix(pfile.stem, target_ws)
                table_name = clean_table_name(raw_stem)

                try:
                    con.execute(
                        f"CREATE OR REPLACE VIEW \"{table_name}\" "
                        f"AS SELECT * FROM read_parquet('{pfile.as_posix()}')"
                    )
                except Exception:
                    continue

                profile_key = str(pfile)
                if precomputed_profiles and profile_key in precomputed_profiles:
                    profile = precomputed_profiles[profile_key]
                else:
                    profile = SemanticDataProfiler.profile(pfile)
                columns = [
                    {"name": c, "type": profile["columns"][c].get("inferred_type", "VARCHAR")}
                    for c in profile["columns"]
                ]
                row_cnt = profile.get("total_rows", 0)
                measures = profile.get("column_categories", {}).get("measures", [])
                col_names = list(profile.get("columns", {}).keys())

                classification = classify_table(table_name, col_names, row_cnt, measures)
                role = classification["role"]
                specialized = detect_specialized_table_type(table_name, col_names, measures, row_cnt)
                pks = detect_primary_keys(table_name, columns, profile)
                time_cols = detect_time_columns(columns)
                biz_entities = detect_business_entities(table_name, col_names, row_cnt)
                hierarchies = detect_hierarchies(table_name, col_names)
                measures_detected = detect_measures(table_name, columns, profile)
                domain_info = classify_domain(table_name, col_names, measures)

                retail_mapping = profile.get("retail_mapping", {})
                canonical_model = None
                try:
                    mapping_input = retail_mapping if retail_mapping else {}
                    if not mapping_input:
                        try:
                            from app.retail.retail_semantic_mapper import RetailSemanticMapper
                            mapping_input = RetailSemanticMapper.map({
                                "columns": profile.get("columns", {}),
                                "total_rows": row_cnt,
                                "column_categories": profile.get("column_categories", {}),
                            })
                        except Exception:
                            mapping_input = {}
                    canonical_model = build_canonical_model(profile, mapping_input)
                except Exception:
                    canonical_model = None

                table_entry = {
                    "table_name": table_name,
                    "file_path": str(pfile),
                    "file_name": pfile.name,
                    "columns": columns,
                    "column_names": col_names,
                    "row_count": row_cnt,
                    "role": role,
                    "is_fact": classification.get("is_fact", False),
                    "is_analytical": classification.get("is_analytical", True),
                    "is_lookup": classification.get("is_lookup", False),
                    "specialized_type": specialized.value if specialized else None,
                    "business_entities": biz_entities,
                    "measures": measures,
                    "measures_detailed": [m.__dict__ for m in measures_detected],
                    "time_columns": [tc.__dict__ for tc in time_cols],
                    "primary_keys": [pk.__dict__ for pk in pks],
                    "hierarchies": [h.__dict__ for h in hierarchies],
                    "description": classification.get("description", ""),
                    "reason": classification.get("reason", ""),
                    "domain": domain_info.get("domain", "Generic Business"),
                    "domain_confidence": domain_info.get("confidence", 50.0),
                    "profile": profile,
                    "column_classifications": self._classify_columns_detailed(profile, table_name),
                    "retail_mapping": retail_mapping,
                    "canonical_model": canonical_model.to_dict() if canonical_model else None,
                }

                tables_meta.append(table_entry)

                if role == "Fact Table":
                    tables_by_role["fact_tables"].append(table_name)
                elif role == "Dimension Table":
                    tables_by_role["dimension_tables"].append(table_name)
                elif role == "Lookup Table":
                    tables_by_role["lookup_tables"].append(table_name)
                elif role == "Reference Table":
                    tables_by_role["reference_tables"].append(table_name)
                elif role == "Bridge Table":
                    tables_by_role["bridge_tables"].append(table_name)
                else:
                    tables_by_role["metadata_tables"].append(table_name)

            fact_tables = [t for t in tables_meta if t["role"] == "Fact Table"]
            fact_tables.sort(key=lambda t: t["row_count"], reverse=True)
            primary_fact = (
                fact_tables[0]["table_name"]
                if fact_tables
                else (tables_meta[0]["table_name"] if tables_meta else None)
            )

            optimized_tables = get_optimized_table_list(tables_meta)
            relationships = discover_relationships(con, optimized_tables)
            detected_fks = detect_foreign_keys_from_relationships(relationships, tables_meta)
            pk_lookup = build_pk_lookup(tables_meta)

            all_measures = []
            for t in tables_meta:
                for m in t.get("measures", []):
                    if m not in all_measures:
                        all_measures.append(m)

            all_time_cols = []
            for t in tables_meta:
                for tc in t.get("time_columns", []):
                    entry = dict(tc)
                    entry["table"] = t["table_name"]
                    if entry not in all_time_cols:
                        all_time_cols.append(entry)

            all_hierarchies = []
            for t in tables_meta:
                for h in t.get("hierarchies", []):
                    h_entry = dict(h)
                    h_entry["table"] = t["table_name"]
                    if h_entry not in all_hierarchies:
                        all_hierarchies.append(h_entry)

            domain_info = {}
            if primary_fact:
                try:
                    pf_meta = next((t for t in tables_meta if t["table_name"] == primary_fact), None)
                    if pf_meta:
                        pf_path = Path(pf_meta["file_path"])
                        domain_info = classify_domain(primary_fact, pf_meta.get("column_names", []), pf_meta.get("measures", []))
                except Exception:
                    domain_info = {"domain": "Generic Business", "confidence": 50.0, "reason": "Fallback classification", "matched_columns": []}

            business_glossary = generate_business_glossary(target_ws, domain_info.get("domain", "Generic Business"), tables_meta, all_measures)
            mermaid_diagram = generate_mermaid_diagram(tables_meta, relationships, primary_fact)
            dot_diagram = generate_dot_diagram(tables_meta, relationships, primary_fact)
            json_diagram = generate_json_diagram(tables_meta, relationships, primary_fact)

            lineage = None
            if include_lineage:
                lineage = generate_lineage(target_ws, tables_meta, relationships, all_measures, domain_info.get("domain"))

            all_business_entities = list(set(
                e for t in tables_meta for e in t.get("business_entities", [])
            ))

            dataset_type_info = self._detect_dataset_type(tables_meta, domain_info)
            column_classifications = self._classify_columns_detailed(profile, table_name)
            time_intelligence = self._detect_time_intelligence(tables_meta)
            data_quality_scores = self._compute_data_quality_scores(tables_meta)
            prediction_preparation = self._detect_prediction_preparation(tables_meta)
            anomaly_preparation = self._prepare_anomaly_detection(tables_meta)
            schema_type_info = self._detect_schema_type(tables_meta, relationships)

            all_column_classifications = []
            for t in tables_meta:
                for cc in t.get("column_classifications", []):
                    if cc not in all_column_classifications:
                        all_column_classifications.append(cc)

            all_kpis = []
            for t in tables_meta:
                for kpi in t.get("kpis", []):
                    if kpi not in all_kpis:
                        all_kpis.append(kpi)

            all_canonical_models = []
            for t in tables_meta:
                cm = t.get("canonical_model")
                if cm:
                    all_canonical_models.append({
                        "table_name": t["table_name"],
                        **cm,
                    })

            result = {
                "workspace_id": target_ws,
                "status": "READY",
                "is_lookup_only": len(fact_tables) == 0,
                "domain": domain_info.get("domain", "Generic Business"),
                "domain_confidence": domain_info.get("confidence", 50.0),
                "domain_reason": domain_info.get("reason", ""),
                "domain_matched_columns": domain_info.get("matched_columns", []),
                "dataset_type": dataset_type_info.get("dataset_type", "Unknown"),
                "dataset_type_confidence": dataset_type_info.get("dataset_type_confidence", 0.0),
                "generated_at": datetime.utcnow().isoformat(),
                "primary_fact_table": primary_fact,
                "tables_count": len(tables_meta),
                "active_joins_count": len(relationships),
                "tables": tables_meta,
                "table_roles": tables_by_role,
                "canonical_models": all_canonical_models,
                "relationships": [r.__dict__ if hasattr(r, "__dict__") else r for r in relationships],
                "primary_keys": {str(k): v.__dict__ if hasattr(v, "__dict__") else v for k, v in pk_lookup.items()},
                "foreign_keys": detected_fks,
                "measures": all_measures,
                "time_columns": all_time_cols,
                "hierarchies": all_hierarchies,
                "business_entities": all_business_entities,
                "specialized_table_types": {
                    t["table_name"]: t.get("specialized_type")
                    for t in tables_meta if t.get("specialized_type")
                },
                "mermaid_diagram": mermaid_diagram,
                "dot_diagram": dot_diagram,
                "json_diagram": json_diagram,
                "lineage": lineage,
                "glossary": business_glossary,
                "optimizations": optimize_for_scale(tables_meta, len(tables_meta)),
                "memory_footprint": estimate_memory_footprint(tables_meta),
                "column_classifications": all_column_classifications,
                "time_intelligence": time_intelligence,
                "kpis": all_kpis,
                "prediction_preparation": prediction_preparation,
                "data_quality_scores": data_quality_scores,
                "anomaly_preparation": anomaly_preparation,
                "schema_type": schema_type_info.get("schema_type", "unknown"),
                "schema_type_confidence": schema_type_info.get("schema_type_confidence", 0.0),
                "dataset_type_details": dataset_type_info,
                "summary": {
                    "fact_tables_count": len(tables_by_role["fact_tables"]),
                    "dimension_tables_count": len(tables_by_role["dimension_tables"]),
                    "lookup_tables_count": len(tables_by_role["lookup_tables"]),
                    "reference_tables_count": len(tables_by_role["reference_tables"]),
                    "bridge_tables_count": len(tables_by_role["bridge_tables"]),
                    "relationships_count": len(relationships),
                    "primary_keys_count": len(pk_lookup),
                    "foreign_keys_count": len(detected_fks),
                    "measures_count": len(all_measures),
                    "time_columns_count": len(all_time_cols),
                    "hierarchies_count": len(all_hierarchies),
                    "canonical_models_count": len(all_canonical_models),
                },
            }

            self._cache.put(target_ws, current_mtime, result, include_lineage_flag)
            self._persist_model(target_ws, result)
            return result
        finally:
            con.close()

    def invalidate_cache(self, workspace_id: Optional[str] = None):
        self._cache.invalidate(workspace_id)

    def get_cached_model(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        return self._cache.get(workspace_id, 0.0, True)

    def trace_column(
        self,
        workspace_id: str,
        target_column: str,
        target_table: str
    ) -> Dict[str, Any]:
        model = self.build_semantic_model(workspace_id, force_rebuild=False)
        if not model or model.get("status") != "READY":
            return {"error": "Semantic model not available"}
        return trace_column_lineage(
            workspace_id,
            model.get("tables", []),
            target_column,
            target_table,
        )

    def analyze_impact(
        self,
        workspace_id: str,
        target: str
    ) -> Dict[str, Any]:
        model = self.build_semantic_model(workspace_id, force_rebuild=False)
        if not model or model.get("status") != "READY":
            return {"error": "Semantic model not available"}
        return impact_analysis(
            workspace_id,
            model.get("tables", []),
            model.get("relationships", []),
            target,
        )

    def export_glossary(self, workspace_id: str) -> List[Dict[str, Any]]:
        model = self.build_semantic_model(workspace_id, force_rebuild=False)
        return model.get("glossary", [])

    def _get_workspace_parquet_mtime(self, workspace_id: str) -> float:
        parquet_dir = STORAGE_DIR
        clean_target = workspace_id.lower().replace("-", "_")

        files = []
        if parquet_dir.exists():
            for p in parquet_dir.glob("*.parquet"):
                if p.name.startswith("unified_") or p.name.startswith("tmp_"):
                    continue
                clean_pname = p.stem.lower().replace("-", "_")
                if clean_target in clean_pname or clean_pname.startswith(clean_target):
                    files.append(p)

        if not files:
            files = list(parquet_dir.glob("*.parquet")) if parquet_dir.exists() else []

        return max((p.stat().st_mtime for p in files), default=0.0)

    def _discover_parquet_files(self, workspace_id: str) -> List[Path]:
        parquet_dir = STORAGE_DIR
        clean_target = _workspace_prefix_for(workspace_id)
        ws_prefix = clean_target + "__"

        parquet_files = []
        if parquet_dir.exists():
            for p in parquet_dir.glob("*.parquet"):
                if p.name.startswith("unified_") or p.name.startswith("tmp_") or p.name.startswith("sample-"):
                    continue
                clean_pname = p.stem.lower().replace("-", "_")
                if clean_target in clean_pname or clean_pname.startswith(clean_target):
                    parquet_files.append(p)

        if not parquet_files:
            try:
                from app.services.workspace_service import EnterpriseWorkspaceManager
                ws = EnterpriseWorkspaceManager.get_workspace(workspace_id)
                if ws and isinstance(ws, dict):
                    tables = ws.get("tables", [])
                    for t in tables:
                        fp = t.get("file_path")
                        if fp:
                            p = Path(fp)
                            if p.exists() and p.is_file():
                                parquet_files.append(p)
            except Exception:
                pass

        return parquet_files

    def _open_duckdb_connection(self):
        import duckdb
        return duckdb.connect(":memory:")

    def _persist_model(self, workspace_id: str, model: Dict[str, Any]):
        try:
            self._LINEAGE_DIR.mkdir(parents=True, exist_ok=True)
            meta_path = self._MODEL_META_FILE
            existing = {}
            if meta_path.exists():
                try:
                    existing = json.loads(meta_path.read_text())
                except Exception:
                    existing = {}
            existing[workspace_id] = {
                "status": model.get("status"),
                "generated_at": model.get("generated_at"),
                "tables_count": model.get("tables_count"),
                "relationships_count": model.get("active_joins_count"),
                "domain": model.get("domain"),
                "primary_fact_table": model.get("primary_fact_table"),
            }
            meta_path.write_text(json.dumps(existing, indent=2))

            lineage_path = self._LINEAGE_DIR / f"lineage_{workspace_id}.json"
            if model.get("lineage"):
                lineage_path.write_text(json.dumps(model["lineage"], indent=2))

            glossary_path = self._GLOSSARY_FILE
            glossary_path.write_text(json.dumps(model.get("glossary", []), indent=2))
        except Exception:
            pass

    def _detect_dataset_type(self, tables_meta: List[Dict[str, Any]], domain_info: Dict[str, Any]) -> Dict[str, Any]:
        domain = domain_info.get("domain", "Generic Business")
        column_names = []
        table_names = []
        for t in tables_meta:
            table_names.append(t.get("table_name", "").lower())
            for c in t.get("column_names", []):
                column_names.append(c.lower())

        try:
            best_domain_enum = next(
                d for d in BusinessDomain if d.value == domain
            )
            dataset_type_enum = BUSINESS_DOMAIN_TO_DATASET_TYPE.get(
                best_domain_enum, DatasetType.UNKNOWN
            )
            return {
                "dataset_type": dataset_type_enum.value,
                "dataset_type_confidence": domain_info.get("domain_confidence", 50.0),
                "dataset_type_matched_keywords": [],
            }
        except StopIteration:
            pass

        return classify_dataset_type(
            table_name=" ".join(table_names),
            columns=column_names,
            measures=[]
        )

    def _classify_columns_detailed(self, profile: Dict[str, Any], table_name: str) -> List[Dict[str, Any]]:
        columns_profile = profile.get("columns", {})
        classifications = []

        for col_name, col_profile in columns_profile.items():
            col_type = col_profile.get("data_type", "VARCHAR").upper()
            category = col_profile.get("category", "dimension")
            col_lower = col_name.lower()

            semantic_type = ColumnSemanticType.DIMENSION.value
            business_role = "dimension"
            unit = ""

            if any(k in col_type for k in ["DATE", "TIME", "TIMESTAMP"]):
                semantic_type = ColumnSemanticType.TEMPORAL.value
                business_role = "temporal"
            elif category == "measure":
                semantic_type = ColumnSemanticType.MEASURE.value
                business_role = "measure"
                if any(k in col_lower for k in ["price", "cost", "salary", "income", "fee", "tax", "amount", "revenue", "balance", "payout", "premium", "claim"]):
                    semantic_type = ColumnSemanticType.CURRENCY.value
                    unit = "currency"
                elif any(k in col_lower for k in ["percentage", "rate", "ratio", "nps", "ctr", "cpc", "cpa", "roas"]):
                    semantic_type = ColumnSemanticType.PERCENTAGE.value
                    unit = "percent"
            elif category == "identifier":
                semantic_type = ColumnSemanticType.IDENTIFIER.value
                business_role = "identifier"
                if "customer" in col_lower:
                    semantic_type = ColumnSemanticType.CUSTOMER_ID.value
                elif "employee" in col_lower or "staff" in col_lower:
                    semantic_type = ColumnSemanticType.EMPLOYEE_ID.value
                elif "user" in col_lower:
                    semantic_type = ColumnSemanticType.USER_ID.value
                elif "product" in col_lower or "item" in col_lower or "sku" in col_lower:
                    semantic_type = ColumnSemanticType.PRODUCT_ID.value
                elif "order" in col_lower or "transaction" in col_lower or "invoice" in col_lower:
                    semantic_type = ColumnSemanticType.TRANSACTION_ID.value
                elif "session" in col_lower:
                    semantic_type = ColumnSemanticType.SESSION_ID.value
            else:
                if any(k in col_lower for k in ["email"]):
                    semantic_type = ColumnSemanticType.EMAIL.value
                elif any(k in col_lower for k in ["phone", "mobile", "telephone"]):
                    semantic_type = ColumnSemanticType.PHONE.value
                elif any(k in col_lower for k in ["ip_address", "src_ip", "dst_ip", "source_ip", "destination_ip"]):
                    semantic_type = ColumnSemanticType.IP_ADDRESS.value
                elif any(k in col_lower for k in ["mac_address", "mac_addr", "mac"]):
                    semantic_type = ColumnSemanticType.MAC_ADDRESS.value
                elif any(k in col_lower for k in ["hostname", "host_name", "server"]):
                    semantic_type = ColumnSemanticType.HOSTNAME.value
                elif any(k in col_lower for k in ["severity", "critical", "high", "medium", "low"]):
                    semantic_type = ColumnSemanticType.SEVERITY.value
                elif any(k in col_lower for k in ["status", "state", "phase"]):
                    semantic_type = ColumnSemanticType.STATUS.value
                elif any(k in col_lower for k in ["threat", "attack", "malicious"]):
                    semantic_type = ColumnSemanticType.THREAT.value
                elif any(k in col_lower for k in ["vulnerability", "cve", "vulnerability_id"]):
                    semantic_type = ColumnSemanticType.VULNERABILITY.value
                elif any(k in col_lower for k in ["asset", "device_id", "equipment"]):
                    semantic_type = ColumnSemanticType.ASSET.value
                elif any(k in col_lower for k in ["device", "sensor", "iot", "gateway"]):
                    semantic_type = ColumnSemanticType.DEVICE.value
                elif any(k in col_lower for k in ["log_type", "event_type", "action"]):
                    semantic_type = ColumnSemanticType.LOG_TYPE.value
                elif any(k in col_lower for k in ["cve_", "cve-", "cve_id"]):
                    semantic_type = ColumnSemanticType.CVE.value
                elif any(k in col_lower for k in ["mitre", "technique", "tactic"]):
                    semantic_type = ColumnSemanticType.MITRE_TECHNIQUE.value
                elif col_type in ("BOOLEAN", "BOOL"):
                    semantic_type = ColumnSemanticType.BOOLEAN.value
                elif category == "dimension" and col_profile.get("distinct_count", 0) > 10:
                    semantic_type = ColumnSemanticType.CATEGORICAL.value

            confidence = SemanticModelEngine._compute_column_confidence(category, col_profile, profile.get("total_rows", 0))

            classifications.append({
                "name": col_name,
                "data_type": col_type,
                "semantic_type": semantic_type,
                "business_role": business_role,
                "unit": unit,
                "is_measure": semantic_type == ColumnSemanticType.MEASURE.value or semantic_type == ColumnSemanticType.CURRENCY.value or semantic_type == ColumnSemanticType.PERCENTAGE.value,
                "is_dimension": semantic_type in (ColumnSemanticType.DIMENSION.value, ColumnSemanticType.CATEGORICAL.value, ColumnSemanticType.FREE_TEXT.value),
                "is_temporal": semantic_type == ColumnSemanticType.TEMPORAL.value,
                "is_identifier": semantic_type == ColumnSemanticType.IDENTIFIER.value or semantic_type in (
                    ColumnSemanticType.USER_ID.value,
                    ColumnSemanticType.EMPLOYEE_ID.value,
                    ColumnSemanticType.CUSTOMER_ID.value,
                    ColumnSemanticType.PRODUCT_ID.value,
                    ColumnSemanticType.TRANSACTION_ID.value,
                    ColumnSemanticType.SESSION_ID.value,
                ),
                "confidence": confidence,
            })

        return classifications

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

    def _detect_time_intelligence(self, tables_meta: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        time_intelligence = []

        for t in tables_meta:
            for tc in t.get("time_columns", []):
                tc_dict = dict(tc)
                tc_dict["table"] = t["table_name"]
                tc_dict["rolling_windows"] = ["7d", "30d", "90d", "1y"]
                tc_dict["seasonality_detected"] = False
                tc_dict["trend_direction"] = "stable"

                col_name = tc.get("column", "").lower()
                if any(k in col_name for k in ["date", "timestamp", "created_at", "updated_at", "order_date", "invoice_date"]):
                    tc_dict["is_primary"] = True

                time_intelligence.append(tc_dict)

        return time_intelligence

    def _compute_data_quality_scores(self, tables_meta: List[Dict[str, Any]]) -> Dict[str, Any]:
        all_columns = []
        for t in tables_meta:
            for col_name, col_profile in t.get("profile", {}).get("columns", {}).items():
                all_columns.append(col_profile)

        if not all_columns:
            return {
                "completeness": 100.0,
                "uniqueness": 100.0,
                "consistency": 100.0,
                "validity": 100.0,
                "accuracy": 100.0,
                "overall_score": 100.0,
                "null_percentage": 0.0,
                "duplicate_percentage": 0.0,
                "outlier_percentage": 0.0,
                "issues": [],
            }

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

        return {
            "completeness": round(completeness, 2),
            "uniqueness": round(uniqueness, 2),
            "consistency": round(consistency, 2),
            "validity": round(validity, 2),
            "accuracy": round(accuracy, 2),
            "overall_score": round(overall, 2),
            "null_percentage": round(null_pct, 2),
            "duplicate_percentage": 0.0,
            "outlier_percentage": 0.0,
            "issues": issues,
        }

    def _detect_prediction_preparation(self, tables_meta: List[Dict[str, Any]]) -> Dict[str, Any]:
        target_variables = []
        prediction_candidates = []
        recommended_task = "none"
        recommended_algorithms = []
        confidence = 0.0
        reasoning = ""

        for t in tables_meta:
            measures = t.get("measures", [])
            dimensions = t.get("dimensions", [])
            col_names = t.get("column_names", [])

            for col_name in measures:
                col_lower = col_name.lower()
                if any(k in col_lower for k in ["churn", "default", "fraud", "attack", "malicious", "benign", "cancelled", "converted", "clicked", "subscribed", "renewed", "returns", "breach", "complaint", "readmission", "attrition", "delinquent"]):
                    target_variables.append({
                        "column": col_name,
                        "table": t["table_name"],
                        "variable_type": "binary_classification",
                        "confidence": 0.85,
                        "reason": f"Column '{col_name}' matches binary outcome patterns.",
                        "is_prediction_target": True,
                    })
                    recommended_task = "binary_classification"
                    recommended_algorithms = ["Logistic Regression", "Random Forest", "XGBoost", "LightGBM"]
                    confidence = 0.85
                    reasoning = f"Target variable '{col_name}' detected with binary classification suitability."

            for col_name in col_names:
                col_lower = col_name.lower()
                if any(k in col_lower for k in ["score", "grade", "amount", "revenue", "sales", "cost", "profit", "quantity", "value", "duration", "probability", "risk", "likelihood", "margin", "discount"]):
                    if col_name not in [v["column"] for v in target_variables]:
                        prediction_candidates.append({
                            "column": col_name,
                            "table": t["table_name"],
                            "candidate_type": "regression",
                            "confidence": 0.75,
                            "reason": f"Column '{col_name}' is numeric with sufficient variance for regression.",
                            "suitable_algorithms": ["Linear Regression", "Random Forest", "XGBoost", "LightGBM"],
                        })

        if not recommended_task and prediction_candidates:
            recommended_task = "regression"
            recommended_algorithms = ["Linear Regression", "Random Forest", "XGBoost"]
            confidence = 0.7
            reasoning = "Numeric measures detected suitable for regression analysis."

        if not recommended_task and dimensions:
            recommended_task = "clustering"
            recommended_algorithms = ["k-Means", "DBSCAN", "Hierarchical"]
            confidence = 0.6
            reasoning = "Categorical dimensions detected suitable for clustering."

        return {
            "target_variables": target_variables,
            "prediction_candidates": prediction_candidates,
            "recommended_task_type": recommended_task,
            "recommended_algorithms": recommended_algorithms,
            "confidence": confidence,
            "reasoning": reasoning,
        }

    def _prepare_anomaly_detection(self, tables_meta: List[Dict[str, Any]]) -> Dict[str, Any]:
        statistical_outliers = []
        business_outliers = []
        unexpected_trends = []
        rare_events = []
        preparation_notes = []

        for t in tables_meta:
            measures = t.get("measures", [])
            time_cols = t.get("time_columns", [])
            profile = t.get("profile", {})

            if not measures:
                continue

            for m in measures[:3]:
                col_profile = profile.get("columns", {}).get(m, {})
                stats = col_profile.get("stats", {})

                if stats.get("stddev") and stats.get("stddev") > 0:
                    mean_val = stats.get("mean", 0)
                    std_val = stats.get("stddev", 0)
                    if std_val > 0:
                        z_threshold = 2.0
                        upper = mean_val + (z_threshold * std_val)
                        lower = mean_val - (z_threshold * std_val)
                        statistical_outliers.append({
                            "column": m,
                            "table": t["table_name"],
                            "method": "z_score",
                            "threshold": z_threshold,
                            "upper_bound": upper,
                            "lower_bound": lower,
                            "mean": mean_val,
                            "stddev": std_val,
                        })

                if time_cols:
                    unexpected_trends.append({
                        "column": m,
                        "table": t["table_name"],
                        "time_column": time_cols[0].get("column"),
                        "detection_method": "time_series_deviation",
                        "status": "pending_execution",
                    })

                preparation_notes.append(f"Column '{m}' in table '{t['table_name']}' prepared for anomaly detection.")

        overall_risk = "LOW"
        if len(statistical_outliers) > 5:
            overall_risk = "MEDIUM"
        if len(statistical_outliers) > 10:
            overall_risk = "HIGH"

        return {
            "statistical_outliers": statistical_outliers,
            "business_outliers": business_outliers,
            "unexpected_trends": unexpected_trends,
            "rare_events": rare_events,
            "overall_risk_level": overall_risk,
            "preparation_notes": preparation_notes,
        }

    def _detect_schema_type(self, tables_meta: List[Dict[str, Any]], relationships: List[Dict[str, Any]]) -> Dict[str, Any]:
        fact_tables = [t for t in tables_meta if t.get("role") == "Fact Table"]
        dim_tables = [t for t in tables_meta if t.get("role") == "Dimension Table"]

        if not fact_tables or not dim_tables:
            return {"schema_type": "unknown", "confidence": 0.0}

        fact_count = len(fact_tables)
        dim_count = len(dim_tables)

        if fact_count == 1 and dim_count >= 1:
            schema_type = "star"
            confidence = 90.0
        elif fact_count > 1 and dim_count >= 1:
            schema_type = "snowflake"
            confidence = 85.0
        else:
            schema_type = "unknown"
            confidence = 50.0

        return {
            "schema_type": schema_type,
            "schema_type_confidence": confidence,
        }


_engine_instance: Optional[SemanticModelEngine] = None


def get_semantic_model_engine() -> SemanticModelEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = SemanticModelEngine()
    return _engine_instance


def build_semantic_model(
    workspace_id: Optional[str] = None,
    force_rebuild: bool = False,
    include_lineage: bool = True,
    precomputed_profiles: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    return get_semantic_model_engine().build_semantic_model(
        workspace_id=workspace_id,
        force_rebuild=force_rebuild,
        include_lineage=include_lineage,
        precomputed_profiles=precomputed_profiles,
    )


def invalidate_semantic_model_cache(workspace_id: Optional[str] = None):
    get_semantic_model_engine().invalidate_cache(workspace_id)


def get_semantic_model(workspace_id: str) -> Optional[Dict[str, Any]]:
    return get_semantic_model_engine().get_cached_model(workspace_id)


def trace_column_lineage_api(workspace_id: str, target_column: str, target_table: str) -> Dict[str, Any]:
    return get_semantic_model_engine().trace_column(workspace_id, target_column, target_table)


def analyze_impact_api(workspace_id: str, target: str) -> Dict[str, Any]:
    return get_semantic_model_engine().analyze_impact(workspace_id, target)


def export_glossary_api(workspace_id: str) -> List[Dict[str, Any]]:
    return get_semantic_model_engine().export_glossary(workspace_id)


def get_canonical_models(workspace_id: str) -> List[Dict[str, Any]]:
    model = get_semantic_model(workspace_id)
    if not model:
        return []
    return model.get("canonical_models", [])


def get_primary_canonical_model(workspace_id: str) -> Optional[Dict[str, Any]]:
    models = get_canonical_models(workspace_id)
    if not models:
        return None
    primary_fact = get_semantic_model(workspace_id).get("primary_fact_table")
    if primary_fact:
        for m in models:
            if m.get("table_name") == primary_fact:
                return m
    return models[0]


def get_revenue_formula_for_workspace(workspace_id: str) -> Optional[str]:
    from app.retail.canonical_model import get_revenue_formula
    primary_cm = get_primary_canonical_model(workspace_id)
    if not primary_cm:
        return None
    try:
        canonical_model = CanonicalRetailModel(
            revenue_column=primary_cm.get("revenue_column"),
            revenue_formula=primary_cm.get("revenue_formula"),
            quantity_column=primary_cm.get("quantity_column"),
            price_column=primary_cm.get("price_column"),
        )
        return get_revenue_formula(canonical_model)
    except Exception:
        return None


def get_available_kpis_for_workspace(workspace_id: str) -> List[str]:
    from app.retail.canonical_model import detect_available_kpis
    primary_cm = get_primary_canonical_model(workspace_id)
    if not primary_cm:
        return []
    try:
        canonical_model = CanonicalRetailModel(
            revenue_column=primary_cm.get("revenue_column"),
            revenue_formula=primary_cm.get("revenue_formula"),
            quantity_column=primary_cm.get("quantity_column"),
            price_column=primary_cm.get("price_column"),
            date_column=primary_cm.get("date_column"),
            order_id_column=primary_cm.get("order_id_column"),
            customer_id_column=primary_cm.get("customer_id_column"),
            product_id_column=primary_cm.get("product_id_column"),
            product_description_column=primary_cm.get("product_description_column"),
            freight_column=primary_cm.get("freight_column"),
            discount_column=primary_cm.get("discount_column"),
            profit_column=primary_cm.get("profit_column"),
            cost_column=primary_cm.get("cost_column"),
            category_column=primary_cm.get("category_column"),
            country_column=primary_cm.get("country_column"),
            store_column=primary_cm.get("store_column"),
            review_column=primary_cm.get("review_column"),
            has_revenue=primary_cm.get("has_revenue", False),
            has_date=primary_cm.get("has_date", False),
            has_order=primary_cm.get("has_order", False),
        )
        return detect_available_kpis(canonical_model)
    except Exception:
        return []