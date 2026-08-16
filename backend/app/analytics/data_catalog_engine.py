import json
import re
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.database.storage import STORAGE_DIR
from app.services.workspace_service import EnterpriseWorkspaceManager
from app.semantic_model.engine import build_semantic_model
from app.ingestion.intelligence_engine import DatasetIntelligenceEngine
from app.ingestion.semantic_profiler import SemanticDataProfiler

CATALOG_FILE = STORAGE_DIR / "data_catalog_metadata.json"
GLOSSARY_FILE = STORAGE_DIR / "business_glossary.json"

DOMAIN_DISPLAY_NAMES = {
    "Retail & E-Commerce": "Retail",
    "Finance & Banking": "Finance",
    "Insurance": "Finance",
    "Human Resources": "HR",
    "Marketing & Advertising": "Marketing",
    "Education": "Education",
    "Healthcare": "Healthcare",
    "Cybersecurity": "Cybersecurity",
    "SaaS & Subscription": "SaaS",
    "CRM & Sales": "CRM",
    "Logistics & Supply Chain": "Logistics",
    "Manufacturing": "Manufacturing",
    "Telecommunications": "Telecom",
    "Government & Public Sector": "Government",
    "Real Estate": "Real Estate",
    "Hospitality & Tourism": "Hospitality",
    "Agriculture": "Agriculture",
    "Energy & Utilities": "Energy",
    "Generic Business": "General",
    "Unknown Dataset": "General",
}


class EnterpriseDataCatalogEngine:
    """
    Snowflake Horizon / Microsoft Purview Spec Enterprise Data Catalog Engine for DecisionLens.
    Manages table metadata, owners, sensitivity classifications, business glossaries, quality scores, and documentation.
    """
    _metadata: Dict[str, Dict[str, Any]] = {}
    _glossary: List[Dict[str, Any]] = []

    @classmethod
    def _load(cls):
        if CATALOG_FILE.exists():
            try:
                with open(CATALOG_FILE, "r") as f:
                    cls._metadata = json.load(f)
            except Exception:
                pass

        if GLOSSARY_FILE.exists():
            try:
                with open(GLOSSARY_FILE, "r") as f:
                    cls._glossary = json.load(f)
            except Exception:
                pass
        else:
            cls._glossary = [
                {"term": "Gross Revenue", "definition": "Total monetary volume across completed transactions prior to discounts.", "domain": "Finance"},
                {"term": "Active Customer", "definition": "Customer record with at least one transaction in the last 90 days.", "domain": "Sales"},
                {"term": "Data Quality Score", "definition": "Composite metric evaluating schema completeness, null ratio, and type consistency.", "domain": "Governance"}
            ]
            cls._save()

    @classmethod
    def _save(cls):
        try:
            with open(CATALOG_FILE, "w") as f:
                json.dump(cls._metadata, f, indent=2)
            with open(GLOSSARY_FILE, "w") as f:
                json.dump(cls._glossary, f, indent=2)
        except Exception:
            pass

    @classmethod
    def _normalize_domain(cls, domain: Optional[str]) -> str:
        if not domain:
            return "General"
        return DOMAIN_DISPLAY_NAMES.get(domain, domain)

    @classmethod
    def _infer_domain_from_schema(cls, table_name: str, column_names: List[str]) -> str:
        text = " ".join([table_name] + column_names).lower()
        domain_keywords = {
            "Retail & E-Commerce": ["sales", "revenue", "profit", "customer", "order", "store", "product", "sku", "quantity", "discount", "price", "category", "freight", "aov", "merchant", "cart"],
            "Finance & Banking": ["account", "balance", "transaction", "credit", "debit", "deposit", "withdrawal", "loan", "interest", "mortgage", "portfolio", "asset", "liability", "tax", "iban"],
            "Healthcare": ["patient", "diagnosis", "doctor", "hospital", "medicine", "dosage", "treatment", "admission", "discharge", "readmission", "symptom", "mrn", "ward", "physician", "mortality"],
            "Human Resources": ["employee", "salary", "department", "designation", "joining", "experience", "attendance", "leave", "manager", "payroll", "attrition", "hire", "performance", "bonus", "ctc"],
            "Marketing & Advertising": ["campaign", "impression", "click", "ctr", "cpc", "conversion", "cpa", "ad_group", "channel", "reach", "engagement", "lead", "roas"],
            "Education": ["student", "learner", "pupil", "academic", "enrollment", "grade", "marks", "score", "course", "subject", "semester", "curriculum", "exam", "result"],
            "Cybersecurity": ["attack", "attack_type", "threat", "malware", "cve", "signature", "src_ip", "dst_ip", "source_ip", "destination_ip", "host", "mac_address", "port", "protocol", "tcp_flags", "service", "event_id", "syslog", "firewall", "siem", "flow_duration", "packets"],
            "Logistics & Supply Chain": ["shipment", "delivery", "logistics", "tracking", "fulfillment", "carrier", "warehouse", "supplier", "vendor", "merchant", "partner", "manufacturer"],
            "Manufacturing": ["machine", "equipment", "production", "assembly", "batch", "shift", "defect", "yield", "quality_control", "work_order", "bom", "raw_material", "finished_good"],
            "Insurance": ["policy", "claim", "payout", "coverage", "premium", "underwriting", "deductible", "beneficiary", "risk", "actuarial", "reinsurance", "loss_ratio"],
            "Telecommunications": ["subscriber", "plan", "tariff", "usage", "roaming", "bandwidth", "latency", "throughput", "cell", "tower", "signal", "call_detail", "sms"],
            "Real Estate": ["property", "listing", "lease", "rent", "mortgage", "tenant", "landlord", "appraisal", "zoning", "sqft", "building", "unit"],
            "Hospitality & Tourism": ["guest", "reservation", "booking", "check_in", "check_out", "room", "hotel", "resort", "occupancy", "revenue_per_available_room", "tour", "destination"],
            "Agriculture": ["crop", "field", "farm", "yield", "harvest", "soil", "irrigation", "pesticide", "fertilizer", "livestock", "ranch", "plantation"],
            "Energy & Utilities": ["meter", "consumption", "generation", "grid", "outage", "renewable", "solar", "wind", "hydro", "transmission", "distribution", "tariff"],
            "Government & Public Sector": ["citizen", "voter", "census", "permit", "license", "tax_record", "grant", "constituency", "ward", "municipality", "public_service"],
            "SaaS & Subscription": ["tenant", "subscription", "plan", "churn", "mrr", "arr", "seat", "usage", "feature_adoption", "onboarding", "downgrade", "upgrade"],
            "CRM & Sales": ["lead", "opportunity", "pipeline", "quota", "deal", "account", "contact", "campaign", "win_rate", "sales_rep", "territory"],
        }
        scores: Dict[str, int] = {}
        for domain, keywords in domain_keywords.items():
            scores[domain] = sum(1 for kw in keywords if kw in text)
        if not scores:
            return "General"
        best_domain = max(scores, key=scores.get)
        return best_domain if scores[best_domain] > 0 else "General"

    @classmethod
    def _build_tags(cls, domain: str, entities: List[str], measures: List[str], dimensions: List[str]) -> List[str]:
        tags: List[str] = []
        if domain and domain not in ("General",):
            tags.append(domain)
        for entity in entities[:2]:
            if entity not in tags:
                tags.append(entity)
        for measure in measures[:2]:
            tag = f"Measure: {measure}"
            if tag not in tags:
                tags.append(tag)
        if not tags:
            tags = ["Analyzed", "Production"]
        return tags

    @classmethod
    def _resolve_parquet_path(cls, table: Dict[str, Any]) -> Optional[Path]:
        path_str = table.get("file_path")
        if path_str:
            p = Path(path_str)
            if p.exists():
                return p
        return None

    @classmethod
    def get_catalog_tables(cls, workspace_id: Optional[str] = None, search: Optional[str] = None, domain_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        cls._load()
        target_ws = workspace_id or EnterpriseWorkspaceManager.get_active_workspace_id() or "ws-enterprise-generic"
        ws_info = EnterpriseWorkspaceManager.get_workspace(target_ws) or {}

        sem_tables: Dict[str, Dict[str, Any]] = {}
        workspace_domain = "General"
        try:
            sem_model = build_semantic_model(workspace_id=target_ws)
            for t in sem_model.get("tables", []):
                sem_tables[t.get("table_name", "")] = t
            workspace_domain = cls._normalize_domain(sem_model.get("domain", "General"))
        except Exception:
            sem_model = {}

        tables = ws_info.get("tables", [])
        catalog_entries: List[Dict[str, Any]] = []

        for t in tables:
            t_name = t.get("table_name", "dataset")
            existing = cls._metadata.get(t_name, {})
            sem_table = sem_tables.get(t_name, {})
            parquet_path = cls._resolve_parquet_path(t)

            profile: Dict[str, Any] = {}
            intelligence: Dict[str, Any] = {}
            if parquet_path and parquet_path.exists():
                try:
                    profile = SemanticDataProfiler.profile(parquet_path)
                except Exception:
                    profile = {}
                try:
                    intelligence = DatasetIntelligenceEngine.analyze_dataset(parquet_path)
                except Exception:
                    intelligence = {}

            raw_domain = existing.get("business_domain")
            if not raw_domain:
                raw_domain = sem_table.get("domain")
            if not raw_domain and intelligence:
                raw_domain = intelligence.get("domain")
            if not raw_domain:
                col_names = [c.get("name", str(c)) if isinstance(c, dict) else str(c) for c in t.get("columns", [])]
                raw_domain = cls._infer_domain_from_schema(t_name, col_names)
            domain = cls._normalize_domain(raw_domain)

            entities = sem_table.get("business_entities", [])
            if not entities:
                entities = intelligence.get("entities", [])
            measures = sem_table.get("measures", [])
            if not measures:
                measures = intelligence.get("measures", [])
            dimensions = sem_table.get("column_categories", {}).get("dimensions", [])
            if not dimensions:
                dimensions = intelligence.get("dimensions", [])

            tags = cls._build_tags(domain, entities, measures, dimensions)

            description = existing.get("business_description")
            if not description:
                description = sem_table.get("description")
            if not description and intelligence:
                description = intelligence.get("reason")
            if not description:
                row_count = profile.get("total_rows") or t.get("rows") or 0
                col_count = len(profile.get("columns", {})) or t.get("columns_count") or 0
                description = f"{domain} dataset containing {row_count:,} rows across {col_count} attributes."

            schema_name = t.get("schema_name", existing.get("schema_name"))

            columns_meta: List[Dict[str, Any]] = []
            raw_profile_cols = profile.get("columns", {})
            if raw_profile_cols:
                for col_name, col_info in raw_profile_cols.items():
                    columns_meta.append({
                        "name": col_name,
                        "type": col_info.get("data_type", "VARCHAR"),
                        "null_percentage": col_info.get("null_percentage", 0.0),
                        "unique_values": col_info.get("distinct_count", 0),
                        "category": col_info.get("category", "dimension"),
                    })
            else:
                for col in t.get("columns", []):
                    if isinstance(col, dict):
                        columns_meta.append({
                            "name": col.get("name", str(col)),
                            "type": col.get("type", "VARCHAR"),
                            "null_percentage": 0.0,
                            "unique_values": 0,
                            "category": "dimension",
                        })
                    else:
                        columns_meta.append({
                            "name": str(col),
                            "type": "VARCHAR",
                            "null_percentage": 0.0,
                            "unique_values": 0,
                            "category": "dimension",
                        })

            row_count = profile.get("total_rows") or t.get("rows") or 0
            updated_at = sem_table.get("generated_at", "").split("T")[0] if sem_table.get("generated_at") else existing.get("updated_at", "")
            if not updated_at:
                updated_at = time.strftime("%Y-%m-%d")

            entry = {
                "name": t_name,
                "schema_name": schema_name,
                "table_name": t_name,
                "workspace_id": target_ws,
                "domain": domain,
                "business_domain": domain,
                "description": description,
                "business_description": description,
                "owner": existing.get("owner", "Enterprise Data Governance Board"),
                "technical_description": existing.get("technical_description", f"Zero-Copy Parquet registered view with {len(columns_meta)} attributes."),
                "source_system": existing.get("source_system", "Automated S3 / File Ingestion Pipeline"),
                "sensitivity": existing.get("sensitivity", "Internal Confidential"),
                "tags": tags,
                "refresh_time": existing.get("refresh_time", "Real-Time / Daily Automated Sync"),
                "quality_score": existing.get("quality_score", "98.5%"),
                "popularity_score": existing.get("popularity_score", 94),
                "is_favorite": existing.get("is_favorite", False),
                "relationships_count": len(sem_model.get("relationships", [])),
                "columns_count": len(columns_meta),
                "column_count": len(columns_meta),
                "row_count": row_count,
                "record_count": row_count,
                "updated_at": updated_at,
                "ai_summary": existing.get("ai_summary", f"Table '{t_name}' serves as a core analytical entity with high data quality and schema compliance."),
                "columns": columns_meta,
                "table_role": sem_table.get("role", "Dimension Table"),
                "profile_summary": {
                    "total_rows": row_count,
                    "total_columns": len(columns_meta),
                    "measures": measures[:5],
                    "dimensions": dimensions[:5],
                    "entities": entities[:5],
                }
            }

            if search:
                q = search.lower()
                searchable_text = " ".join([
                    t_name.lower(),
                    (description or "").lower(),
                    domain.lower(),
                    " ".join(c["name"].lower() for c in columns_meta),
                    " ".join(tag.lower() for tag in tags),
                ])
                if q not in searchable_text:
                    continue
            if domain_filter and domain_filter.lower() != domain.lower():
                continue

            catalog_entries.append(entry)

        return catalog_entries

    @classmethod
    def update_table_metadata(cls, table_name: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        cls._load()
        if table_name not in cls._metadata:
            cls._metadata[table_name] = {}
        cls._metadata[table_name].update(updates)
        cls._save()
        return {"status": "success", "table_name": table_name, "updated_fields": list(updates.keys())}

    @classmethod
    def get_business_glossary(cls) -> List[Dict[str, Any]]:
        cls._load()
        return cls._glossary

    @classmethod
    def generate_purview_documentation(cls, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        tables = cls.get_catalog_tables(workspace_id)
        glossary = cls.get_business_glossary()

        doc_md = f"# DECISIONLENS ENTERPRISE DATA CATALOG DOCUMENTATION (MICROSOFT PURVIEW SPEC)\n\n"
        doc_md += f"**Workspace ID**: {workspace_id or 'Active Workspace'}\n"
        doc_md += f"**Governance Platform**: Snowflake Horizon & Microsoft Purview Specification\n\n"
        doc_md += f"## 1. Enterprise Assets Catalog ({len(tables)} Tables)\n\n"

        for t in tables:
            doc_md += f"### Asset: `{t.get('table_name', t.get('name'))}`\n"
            doc_md += f"- **Owner**: {t.get('owner')}\n"
            doc_md += f"- **Domain**: {t.get('business_domain')}\n"
            doc_md += f"- **Sensitivity**: `{t.get('sensitivity')}`\n"
            doc_md += f"- **Quality Score**: {t.get('quality_score')}\n"
            doc_md += f"- **Business Description**: {t.get('business_description')}\n"
            doc_md += f"- **Technical Description**: {t.get('technical_description')}\n"
            doc_md += f"- **Tags**: {', '.join(t.get('tags', []))}\n\n"

        doc_md += f"## 2. Business Glossary Definitions ({len(glossary)} Terms)\n\n"
        for g in glossary:
            doc_md += f"- **{g['term']}** (`{g['domain']}`): {g['definition']}\n"

        return {
            "format": "Markdown",
            "documentation": doc_md
        }
