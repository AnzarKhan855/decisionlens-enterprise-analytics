from typing import Any, Dict, List, Optional

from app.semantic_model.core import SemanticModel


def generate_lineage(
    workspace_id: str,
    tables_meta: List[Dict[str, Any]],
    relationships: List[Dict[str, Any]],
    measures: Optional[List[str]] = None,
    domain: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate full data lineage tracking the complete chain:
    Dataset -> Tables -> Columns -> Relationships -> KPIs -> Reports -> Dashboards
    """
    nodes = []
    edges = []
    node_ids = set()

    # Level 1: Dataset
    dataset_id = f"ds_{workspace_id}"
    nodes.append({
        "id": dataset_id,
        "type": "Dataset",
        "name": f"Workspace Dataset: {workspace_id}",
        "source_system": "Uploaded Dataset / ZIP Archive",
        "owner": "Enterprise Data Governance Board",
        "domain": domain or "Generic Business",
        "level": 1,
    })
    node_ids.add(dataset_id)

    # Level 2: Tables
    table_nodes = {}
    for t in tables_meta:
        t_name = t["table_name"]
        t_id = f"tbl_{t_name}"
        if t_id not in node_ids:
            nodes.append({
                "id": t_id,
                "type": "Table",
                "name": t_name,
                "role": t.get("role", "Unknown"),
                "row_count": t.get("row_count", 0),
                "columns_count": len(t.get("columns", [])),
                "source_system": "Derived from Dataset",
                "owner": "Enterprise Data Governance Board",
                "domain": t.get("domain", "Generic Business"),
                "level": 2,
            })
            node_ids.add(t_id)
            table_nodes[t_name] = t_id
            edges.append({
                "source": dataset_id,
                "target": t_id,
                "relationship": "contains",
                "transformation": "Dataset Ingestion",
            })

    # Level 3: Columns
    column_nodes = {}
    for t in tables_meta:
        t_name = t["table_name"]
        t_id = table_nodes.get(t_name, f"tbl_{t_name}")
        for c in t.get("columns", []):
            c_id = f"col_{t_name}_{c['name']}"
            if c_id not in node_ids:
                nodes.append({
                    "id": c_id,
                    "type": "Column",
                    "name": c["name"],
                    "data_type": c.get("type"),
                    "table": t_name,
                    "role": t.get("role", "Unknown"),
                    "source_system": f"Derived from {t_name}",
                    "category": _categorize_column(c["name"], c.get("type", "")),
                    "level": 3,
                })
                node_ids.add(c_id)
                column_nodes[(t_name, c["name"])] = c_id
                edges.append({
                    "source": t_id,
                    "target": c_id,
                    "relationship": "contains",
                    "transformation": "Schema Ingestion",
                })

    # Level 4: Relationships
    rel_nodes = {}
    for idx, rel in enumerate(relationships):
        rel_key = f"{rel.from_table}_{rel.from_column}_{rel.to_table}_{rel.to_column}"
        rel_id = f"rel_{rel_key}_{idx}"
        if rel_id not in node_ids:
            nodes.append({
                "id": rel_id,
                "type": "Relationship",
                "name": f"{rel.from_table}.{rel.from_column} -> {rel.to_table}.{rel.to_column}",
                "cardinality": str(rel.cardinality.value if hasattr(rel.cardinality, "value") else rel.cardinality),
                "confidence_score": rel.confidence_score,
                "source_system": "Auto-Detected FK Relationship",
                "owner": "Semantic Model Engine",
                "level": 4,
            })
            node_ids.add(rel_id)
            rel_nodes[rel_key] = rel_id

            from_tbl = rel.from_table
            to_tbl = rel.to_table
            from_tid = table_nodes.get(from_tbl, f"tbl_{from_tbl}")
            to_tid = table_nodes.get(to_tbl, f"tbl_{to_tbl}")
            edges.append({
                "source": from_tid,
                "target": rel_id,
                "relationship": "defines",
                "transformation": "Foreign Key Relationship",
            })
            edges.append({
                "source": rel_id,
                "target": to_tid,
                "relationship": "references",
                "transformation": "Referential Integrity",
            })

    # Level 5: KPIs
    kpi_counter = 0
    measure_list = measures or []
    for t in tables_meta:
        for m in t.get("measures", []):
            kpi_id = f"kpi_{m}_{kpi_counter}"
            if kpi_id not in node_ids:
                nodes.append({
                    "id": kpi_id,
                    "type": "KPI",
                    "name": f"{m.replace('_', ' ').title()}",
                    "source_table": t["table_name"],
                    "aggregation": "SUM",
                    "source_system": f"Derived from {t['table_name']}",
                    "owner": "Enterprise Analytics Engine",
                    "level": 5,
                })
                node_ids.add(kpi_id)
                kpi_counter += 1

                col_key = (t["table_name"], m)
                col_id = column_nodes.get(col_key)
                if col_id:
                    edges.append({
                        "source": col_id,
                        "target": kpi_id,
                        "relationship": "measures",
                        "transformation": f"SUM({m})",
                    })

                t_id = table_nodes.get(t["table_name"], f"tbl_{t['table_name']}")
                edges.append({
                    "source": t_id,
                    "target": kpi_id,
                    "relationship": "produces",
                    "transformation": "Aggregation",
                })

    # Level 6: Reports
    report_id = f"rpt_{workspace_id}"
    if report_id not in node_ids:
        nodes.append({
            "id": report_id,
            "type": "Report",
            "name": f"Executive Report: {workspace_id}",
            "source_system": "DecisionLens Report Engine",
            "owner": "Executive Analytics Team",
            "level": 6,
        })
        node_ids.add(report_id)

        for t in tables_meta:
            t_id = table_nodes.get(t["table_name"], f"tbl_{t['table_name']}")
            edges.append({
                "source": t_id,
                "target": report_id,
                "relationship": "feeds",
                "transformation": "Report Data Source",
            })

        for m in measure_list[:10]:
            kpi_id = f"kpi_{m}_0"
            if kpi_id in node_ids:
                edges.append({
                    "source": kpi_id,
                    "target": report_id,
                    "relationship": "visualized_in",
                    "transformation": "Report KPI Section",
                })

    # Level 7: Dashboards
    dashboard_id = f"dash_{workspace_id}"
    if dashboard_id not in node_ids:
        nodes.append({
            "id": dashboard_id,
            "type": "Dashboard",
            "name": f"Executive Dashboard: {workspace_id}",
            "source_system": "DecisionLens Dashboard Engine",
            "owner": "Executive Analytics Team",
            "level": 7,
        })
        node_ids.add(dashboard_id)

        edges.append({
            "source": report_id,
            "target": dashboard_id,
            "relationship": "powers",
            "transformation": "Dashboard Widget Data",
        })

        for t in tables_meta:
            t_id = table_nodes.get(t["table_name"], f"tbl_{t['table_name']}")
            edges.append({
                "source": t_id,
                "target": dashboard_id,
                "relationship": "feeds",
                "transformation": "Real-time Dashboard Feed",
            })

    return {
        "workspace_id": workspace_id,
        "nodes": nodes,
        "edges": edges,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "levels": {
            "1_dataset": 1,
            "2_tables": len(table_nodes),
            "3_columns": len(column_nodes),
            "4_relationships": len(rel_nodes),
            "5_kpis": kpi_counter,
            "6_reports": 1,
            "7_dashboards": 1,
        },
    }


def _categorize_column(col_name: str, col_type: str) -> str:
    col_lower = col_name.lower()
    type_upper = col_type.upper()

    if any(k in type_upper for k in ["DATE", "TIME", "TIMESTAMP"]):
        return "temporal"
    if any(k in col_lower for k in ["id", "key", "uuid", "code"]):
        return "identifier"
    if any(k in type_upper for k in ["INT", "BIGINT", "FLOAT", "DOUBLE", "DECIMAL"]):
        return "measure"
    return "dimension"


def trace_column_lineage(
    workspace_id: str,
    tables_meta: List[Dict[str, Any]],
    target_column: str,
    target_table: str
) -> Dict[str, Any]:
    origin = None
    downstream = []
    kpis = []
    reports = []
    dashboards = []

    for t in tables_meta:
        if t["table_name"] == target_table:
            for c in t.get("columns", []):
                if c["name"] == target_column:
                    origin = {
                        "table": t["table_name"],
                        "column": c["name"],
                        "type": c.get("type"),
                        "role": t.get("role"),
                        "category": _categorize_column(c["name"], c.get("type", "")),
                    }
                    break

    if origin:
        ctype = origin.get("category", "")
        if ctype == "measure":
            kpis.append({
                "type": "KPI",
                "name": f"{target_column.replace('_', ' ').title()}",
                "aggregation": "SUM",
                "reports": [f"Executive Report: {workspace_id}"],
                "dashboards": [f"Executive Dashboard: {workspace_id}"],
            })
            reports.append(f"Executive Report: {workspace_id}")
            dashboards.append(f"Executive Dashboard: {workspace_id}")

    for rel in []:
        pass

    return {
        "target": {"table": target_table, "column": target_column},
        "origin": origin,
        "downstream_transformations": downstream,
        "kpis": kpis,
        "reports": reports,
        "dashboards": dashboards,
        "impact_scope": "column",
    }


def impact_analysis(
    workspace_id: str,
    tables_meta: List[Dict[str, Any]],
    relationships: List[Dict[str, Any]],
    target: str
) -> Dict[str, Any]:
    target_lower = target.lower()
    affected_tables = []
    affected_columns = []
    affected_kpis = []
    affected_reports = []
    affected_dashboards = []

    for t in tables_meta:
        if target_lower in t["table_name"].lower():
            affected_tables.append(t["table_name"])
        for c in t.get("columns", []):
            if target_lower in c["name"].lower():
                affected_columns.append({"table": t["table_name"], "column": c["name"]})
                ctype = _categorize_column(c["name"], c.get("type", ""))
                if ctype == "measure":
                    affected_kpis.append({
                        "name": f"{c['name'].replace('_', ' ').title()}",
                        "table": t["table_name"],
                        "aggregation": "SUM",
                    })

    downstream_tables = set()
    for rel in relationships:
        if target_lower in rel.from_column.lower():
            downstream_tables.add(rel.to_table)
        if target_lower in rel.to_column.lower():
            downstream_tables.add(rel.from_table)

    if affected_tables or affected_columns:
        affected_reports.append(f"Executive Report: {workspace_id}")
        affected_dashboards.append(f"Executive Dashboard: {workspace_id}")

    severity = "High" if (affected_tables or affected_columns or affected_kpis) else "None"

    return {
        "target": target,
        "impact_severity": f"{severity} Impact",
        "affected_tables": affected_tables,
        "affected_columns": affected_columns,
        "affected_kpis": affected_kpis,
        "affected_reports": affected_reports,
        "affected_dashboards": affected_dashboards,
        "downstream_tables": list(downstream_tables),
        "recommendation": (
            f"Modifying '{target}' requires updating dependent semantic model "
            f"view definitions, KPI calculations, reports, and dashboard widgets."
            if severity == "High"
            else f"No direct dependencies found for '{target}'."
        ),
    }