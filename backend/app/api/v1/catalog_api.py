from fastapi import APIRouter, Query, Body, HTTPException
from typing import Optional, Dict, Any
from app.analytics.data_catalog_engine import EnterpriseDataCatalogEngine

router = APIRouter(prefix="/catalog", tags=["Enterprise Data Catalog & Governance (Purview Spec)"])


@router.get("/tables")
def get_catalog_tables(
    workspace_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    domain: Optional[str] = Query(None)
):
    return {
        "workspace_id": workspace_id or "active",
        "tables": EnterpriseDataCatalogEngine.get_catalog_tables(workspace_id=workspace_id, search=search, domain_filter=domain)
    }


@router.post("/table/update")
def update_catalog_table(body: Dict[str, Any] = Body(...)):
    table_name = body.get("table_name")
    updates = body.get("updates", {})
    if not table_name:
        raise HTTPException(status_code=400, detail="table_name is required")
    return EnterpriseDataCatalogEngine.update_table_metadata(table_name, updates)


@router.get("/glossary")
def get_business_glossary():
    return {
        "glossary_count": len(EnterpriseDataCatalogEngine.get_business_glossary()),
        "terms": EnterpriseDataCatalogEngine.get_business_glossary()
    }


@router.get("/documentation")
def get_catalog_documentation(workspace_id: Optional[str] = Query(None)):
    return EnterpriseDataCatalogEngine.generate_purview_documentation(workspace_id)
