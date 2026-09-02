from fastapi import APIRouter, Query, Body, HTTPException, Depends
from typing import Optional, Dict, Any
from app.analytics.data_catalog_engine import EnterpriseDataCatalogEngine
from app.core.rbac import get_current_user_from_token, require_role, SUPER_ADMIN, ORGANIZATION_ADMIN

router = APIRouter(
    prefix="/catalog",
    tags=["Enterprise Data Catalog & Governance (Purview Spec)"],
    dependencies=[Depends(get_current_user_from_token)]
)


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
def update_catalog_table(
    body: Dict[str, Any] = Body(...),
    user: Dict[str, Any] = Depends(require_role([SUPER_ADMIN, ORGANIZATION_ADMIN]))
):
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
