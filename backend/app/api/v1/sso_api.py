from fastapi import APIRouter, Query, Body, HTTPException, Depends
from typing import Optional, Dict, Any
from app.core.enterprise_sso_engine import EnterpriseSSOEngine
from app.core.rbac import get_current_user_from_token, require_role, SUPER_ADMIN, ORGANIZATION_ADMIN

router = APIRouter(prefix="/sso", tags=["Enterprise SSO & SCIM Platform (Entra / Okta Spec)"])


@router.get("/providers")
def get_supported_sso_providers(user: Dict[str, Any] = Depends(get_current_user_from_token)):
    return {
        "providers_count": len(EnterpriseSSOEngine.get_supported_providers()),
        "providers": EnterpriseSSOEngine.get_supported_providers()
    }


@router.post("/idp/config", dependencies=[Depends(require_role([SUPER_ADMIN]))])
def configure_idp_provider(body: Dict[str, Any] = Body(...)):
    tenant_id = body.get("tenant_id")
    provider_id = body.get("provider_id")
    client_id = body.get("client_id")
    client_secret = body.get("client_secret")
    metadata_url = body.get("metadata_url")

    missing = []
    if not tenant_id:
        missing.append("tenant_id")
    if not provider_id:
        missing.append("provider_id")
    if not client_id:
        missing.append("client_id")
    if not client_secret:
        missing.append("client_secret")

    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required fields: {', '.join(missing)}")

    return EnterpriseSSOEngine.configure_idp(
        tenant_id=tenant_id,
        provider_id=provider_id,
        client_id=client_id,
        client_secret=client_secret,
        metadata_url=metadata_url
    )


@router.get("/idp/config/{tenant_id}", dependencies=[Depends(require_role([SUPER_ADMIN, ORGANIZATION_ADMIN]))])
def get_idp_configuration(tenant_id: str):
    return EnterpriseSSOEngine.get_idp_config(tenant_id)


@router.post("/login/{provider}")
def sso_login_jit(provider: str, body: Dict[str, Any] = Body(...)):
    claims = body.get("id_token_claims")
    tenant_id = body.get("tenant_id")

    if not claims:
        raise HTTPException(status_code=400, detail="Missing required field: id_token_claims")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Missing required field: tenant_id")

    return EnterpriseSSOEngine.sso_authenticate_jit(provider_id=provider, id_token_claims=claims, tenant_id=tenant_id)


@router.post("/scim/v2/Users", dependencies=[Depends(require_role([SUPER_ADMIN]))])
def scim_provision_user(body: Dict[str, Any] = Body(...)):
    return EnterpriseSSOEngine.scim_provision_user(body)


@router.post("/conditional-access/evaluate", dependencies=[Depends(get_current_user_from_token)])
def evaluate_conditional_access(body: Dict[str, Any] = Body(...)):
    ip = body.get("client_ip", "127.0.0.1")
    trusted = body.get("device_trusted", True)
    country = body.get("country", "United States")
    return EnterpriseSSOEngine.evaluate_conditional_access(client_ip=ip, device_trusted=trusted, location_country=country)
