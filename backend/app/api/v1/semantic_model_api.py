from fastapi import APIRouter, Query, Body, HTTPException, Depends
from typing import Optional, Dict, Any, List
from app.core.rbac import get_current_user_from_token

from app.semantic_model.engine import (
    build_semantic_model,
    invalidate_semantic_model_cache,
    get_semantic_model,
    trace_column_lineage_api,
    analyze_impact_api,
    export_glossary_api,
)

router = APIRouter(
    prefix="/semantic-model",
    tags=["Enterprise Semantic Model"],
    dependencies=[Depends(get_current_user_from_token)]
)


@router.get("/workspace/{workspace_id}")
def get_semantic_model(workspace_id: str, force_rebuild: bool = Query(False, description="Force rebuild of semantic model")):
    result = build_semantic_model(workspace_id=workspace_id, force_rebuild=force_rebuild)
    return result


@router.post("/workspace/{workspace_id}/rebuild")
def rebuild_semantic_model(workspace_id: str, body: Dict[str, Any] = Body(default={})):
    force_rebuild = body.get("force_rebuild", True)
    include_lineage = body.get("include_lineage", True)
    result = build_semantic_model(workspace_id=workspace_id, force_rebuild=force_rebuild, include_lineage=include_lineage)
    return result


@router.post("/workspace/{workspace_id}/invalidate-cache")
def invalidate_semantic_cache(workspace_id: str):
    invalidate_semantic_model_cache(workspace_id)
    return {"status": "success", "message": f"Semantic model cache invalidated for workspace '{workspace_id}'"}


@router.get("/workspace/{workspace_id}/diagram/mermaid")
def get_mermaid_diagram(workspace_id: str, force_rebuild: bool = Query(False, description="Force rebuild")):
    result = build_semantic_model(workspace_id=workspace_id, force_rebuild=force_rebuild)
    return {"mermaid_diagram": result.get("mermaid_diagram", "")}


@router.get("/workspace/{workspace_id}/diagram/dot")
def get_dot_diagram(workspace_id: str, force_rebuild: bool = Query(False, description="Force rebuild")):
    result = build_semantic_model(workspace_id=workspace_id, force_rebuild=force_rebuild)
    return {"dot_diagram": result.get("dot_diagram", "")}


@router.get("/workspace/{workspace_id}/diagram/json")
def get_json_diagram(workspace_id: str, force_rebuild: bool = Query(False, description="Force rebuild")):
    result = build_semantic_model(workspace_id=workspace_id, force_rebuild=force_rebuild)
    return {"json_diagram": result.get("json_diagram", {})}


@router.get("/workspace/{workspace_id}/lineage")
def get_lineage(workspace_id: str, force_rebuild: bool = Query(False, description="Force rebuild")):
    result = build_semantic_model(workspace_id=workspace_id, force_rebuild=force_rebuild, include_lineage=True)
    return result.get("lineage", {})


@router.get("/workspace/{workspace_id}/lineage/column")
def trace_column_lineage(
    workspace_id: str,
    column: str = Query(..., description="Target column name"),
    table: str = Query(..., description="Target table name"),
):
    return trace_column_lineage_api(workspace_id, column, table)


@router.get("/workspace/{workspace_id}/lineage/impact")
def get_impact_analysis(
    workspace_id: str,
    target: str = Query(..., description="Table or column name to analyze impact for"),
):
    return analyze_impact_api(workspace_id, target)


@router.get("/workspace/{workspace_id}/glossary")
def get_business_glossary(workspace_id: str, force_rebuild: bool = Query(False, description="Force rebuild")):
    result = build_semantic_model(workspace_id=workspace_id, force_rebuild=force_rebuild)
    return {"glossary": result.get("glossary", [])}


@router.get("/workspace/{workspace_id}/glossary/export")
def export_glossary(workspace_id: str, force_rebuild: bool = Query(False, description="Force rebuild")):
    glossary = export_glossary_api(workspace_id)
    return {"glossary_count": len(glossary), "terms": glossary}


@router.get("/workspace/{workspace_id}/summary")
def get_semantic_summary(workspace_id: str, force_rebuild: bool = Query(False, description="Force rebuild")):
    result = build_semantic_model(workspace_id=workspace_id, force_rebuild=force_rebuild)
    return {
        "workspace_id": result.get("workspace_id"),
        "status": result.get("status"),
        "domain": result.get("domain"),
        "domain_confidence": result.get("domain_confidence"),
        "primary_fact_table": result.get("primary_fact_table"),
        "summary": result.get("summary", {}),
        "optimizations": result.get("optimizations", {}),
        "memory_footprint": result.get("memory_footprint", {}),
    }


@router.get("/workspace/{workspace_id}/tables")
def get_semantic_tables(workspace_id: str, force_rebuild: bool = Query(False, description="Force rebuild")):
    result = build_semantic_model(workspace_id=workspace_id, force_rebuild=force_rebuild)
    return {"tables": result.get("tables", []), "table_roles": result.get("table_roles", {})}


@router.get("/workspace/{workspace_id}/relationships")
def get_semantic_relationships(workspace_id: str, force_rebuild: bool = Query(False, description="Force rebuild")):
    result = build_semantic_model(workspace_id=workspace_id, force_rebuild=force_rebuild)
    return {"relationships": result.get("relationships", [])}


@router.get("/workspace/{workspace_id}/measures")
def get_semantic_measures(workspace_id: str, force_rebuild: bool = Query(False, description="Force rebuild")):
    result = build_semantic_model(workspace_id=workspace_id, force_rebuild=force_rebuild)
    return {"measures": result.get("measures", [])}


@router.get("/workspace/{workspace_id}/hierarchies")
def get_semantic_hierarchies(workspace_id: str, force_rebuild: bool = Query(False, description="Force rebuild")):
    result = build_semantic_model(workspace_id=workspace_id, force_rebuild=force_rebuild)
    return {"hierarchies": result.get("hierarchies", [])}


@router.get("/workspace/{workspace_id}/business-entities")
def get_semantic_entities(workspace_id: str, force_rebuild: bool = Query(False, description="Force rebuild")):
    result = build_semantic_model(workspace_id=workspace_id, force_rebuild=force_rebuild)
    return {"business_entities": result.get("business_entities", [])}


@router.get("/workspace/{workspace_id}/specialized-tables")
def get_specialized_tables(workspace_id: str, force_rebuild: bool = Query(False, description="Force rebuild")):
    result = build_semantic_model(workspace_id=workspace_id, force_rebuild=force_rebuild)
    return {
        "specialized_table_types": result.get("specialized_table_types", {}),
    }