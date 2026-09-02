from fastapi import APIRouter, Query, Response, Depends
from typing import Optional, Dict, Any
from app.analytics.data_lineage_engine import DataLineageEngine
from app.core.rbac import get_current_user_from_token

router = APIRouter(
    prefix="/lineage",
    tags=["Data Lineage & Provenance (Microsoft Fabric Spec)"],
    dependencies=[Depends(get_current_user_from_token)]
)


@router.get("/graph/{workspace_id}")
def get_lineage_graph(workspace_id: str):
    return DataLineageEngine.generate_lineage_graph(workspace_id)


@router.get("/mermaid/{workspace_id}")
def export_lineage_mermaid(workspace_id: str):
    mermaid_code = DataLineageEngine.export_mermaid(workspace_id)
    return Response(content=mermaid_code, media_type="text/plain")


@router.get("/trace/kpi")
def trace_kpi_origin(kpi_name: str = Query(..., description="KPI name to trace origin for"), workspace_id: Optional[str] = Query(None)):
    return DataLineageEngine.trace_kpi_origin(kpi_name, workspace_id)


@router.get("/impact-analysis")
def perform_impact_analysis(target: str = Query(..., description="Table or column name to analyze impact for"), workspace_id: Optional[str] = Query(None)):
    return DataLineageEngine.impact_analysis(target, workspace_id)
