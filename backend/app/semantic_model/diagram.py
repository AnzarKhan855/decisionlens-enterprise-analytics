from typing import Any, Dict, List

from app.semantic_model.core import SemanticModel


def generate_mermaid_diagram(
    tables_meta: List[Dict[str, Any]],
    relationships: List[Dict[str, Any]],
    primary_fact: str
) -> str:
    lines = ["graph TD", "    %% DecisionLens Enterprise Semantic Model Diagram"]

    lines.append("    classDef fact fill:#4f46e5,color:#fff,stroke:#312e81,stroke-width:2px")
    lines.append("    classDef dimension fill:#10b981,color:#fff,stroke:#065f46,stroke-width:2px")
    lines.append("    classDef lookup fill:#f59e0b,color:#fff,stroke:#92400e,stroke-width:1px")
    lines.append("    classDef reference fill:#6366f1,color:#fff,stroke:#3730a3,stroke-width:1px")
    lines.append("    classDef bridge fill:#8b5cf6,color:#fff,stroke:#5b21b6,stroke-width:1px")
    lines.append("    classDef metadata fill:#94a3b8,color:#fff,stroke:#475569,stroke-width:1px")

    for t in tables_meta:
        tid = t["table_name"].replace("-", "_").replace(".", "_")
        role = t.get("role", "Dimension Table")
        cls_name = role.lower().replace(" table", "").replace(" ", "_")
        if cls_name not in ("fact", "dimension", "lookup", "reference", "bridge", "metadata"):
            cls_name = "dimension"
        lines.append(f'    {tid}["{t["table_name"]} ({role})"]')
        lines.append(f"    class {tid} {cls_name}")

    for rel in relationships:
        sid = rel.from_table.replace("-", "_").replace(".", "_")
        tid = rel.to_table.replace("-", "_").replace(".", "_")
        card_str = str(rel.cardinality.value if hasattr(rel.cardinality, "value") else rel.cardinality)
        conf = rel.confidence_score
        lines.append(f'    {sid} -->|"{rel.from_column} {card_str} {rel.to_column} ({conf}%)| {tid}')

    return "\n".join(lines)


def generate_dot_diagram(
    tables_meta: List[Dict[str, Any]],
    relationships: List[Dict[str, Any]],
    primary_fact: str
) -> str:
    lines = ["digraph SemanticModel {"]
    lines.append('    rankdir=LR;')
    lines.append('    node [shape=box, style=filled, fontname="Arial"];')

    color_map = {
        "Fact Table": "#4f46e5",
        "Dimension Table": "#10b981",
        "Lookup Table": "#f59e0b",
        "Reference Table": "#6366f1",
        "Bridge Table": "#8b5cf6",
        "Metadata Table": "#94a3b8",
    }

    for t in tables_meta:
        tid = t["table_name"].replace("-", "_").replace(".", "_")
        role = t.get("role", "Dimension Table")
        color = color_map.get(role, "#10b981")
        lines.append(f'    {tid} [label="{t["table_name"]}\\n({role})", fillcolor="{color}", fontcolor="white"];')

    for rel in relationships:
        sid = rel.from_table.replace("-", "_").replace(".", "_")
        tid = rel.to_table.replace("-", "_").replace(".", "_")
        card_str = str(rel.cardinality.value if hasattr(rel.cardinality, "value") else rel.cardinality)
        lines.append(f'    {sid} -> {tid} [label="{rel.from_column} ({card_str})", color="#64748b"];')

    lines.append("}")
    return "\n".join(lines)


def generate_json_diagram(
    tables_meta: List[Dict[str, Any]],
    relationships: List[Dict[str, Any]],
    primary_fact: str
) -> Dict[str, Any]:
    nodes = []
    edges = []

    for t in tables_meta:
        role = t.get("role", "Dimension Table")
        nodes.append({
            "id": t["table_name"],
            "label": f"{t['table_name']} ({role})",
            "type": role,
            "rowCount": t.get("row_count", 0),
            "columnCount": len(t.get("columns", [])),
            "measures": t.get("measures", []),
            "isFact": t.get("is_fact", False),
        })

    for rel in relationships:
        edges.append({
            "source": rel.from_table,
            "target": rel.to_table,
            "sourceColumn": rel.from_column,
            "targetColumn": rel.to_column,
            "cardinality": str(rel.cardinality.value if hasattr(rel.cardinality, "value") else rel.cardinality),
            "confidence": rel.confidence_score,
        })

    return {
        "nodes": nodes,
        "edges": edges,
        "primaryFactTable": primary_fact,
    }