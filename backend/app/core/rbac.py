from typing import Dict, Any, List, Optional
from fastapi import HTTPException, Header, Depends
from app.core.security import SecurityManager
from app.core.config import settings

# Primary Supported Roles
SUPER_ADMIN = "SUPER_ADMIN"
ORGANIZATION_ADMIN = "ORGANIZATION_ADMIN"
EMPLOYEE = "EMPLOYEE"

ROLES = [
    SUPER_ADMIN,
    ORGANIZATION_ADMIN,
    EMPLOYEE,
]


def normalize_role(role_str: Optional[str]) -> str:
    """
    Normalizes any role string into one of the 3 supported system roles:
    SUPER_ADMIN, ORGANIZATION_ADMIN, or EMPLOYEE.
    Supports backward compatibility with legacy role strings.
    """
    if not role_str:
        return EMPLOYEE

    r = str(role_str).strip().upper().replace(" ", "_")
    if r in (SUPER_ADMIN, "SUPER_ADMIN", "ADMINISTRATOR", "ADMIN", "SUPERADMIN"):
        return SUPER_ADMIN
    if r in (ORGANIZATION_ADMIN, "ORGANIZATION_ADMIN", "ORG_ADMIN", "ORGANIZATIONADMIN", "WORKSPACE_ADMIN"):
        return ORGANIZATION_ADMIN
    return EMPLOYEE


# Fine-grained Permissions
PERMISSIONS = [
    "system_settings",
    "manage_organizations",
    "manage_all_workspaces",
    "view_all_audit_logs",
    "view_audit_logs",
    "manage_users",
    "manage_own_organization",
    "invite_employees",
    "manage_org_datasets",
    "view_dashboards",
    "view_reports",
    "export_reports",
    "use_copilot",
    "view_allowed_datasets",
    "upload_dataset",
    "execute_ai",
    "execute_sql",
]

# Role to Permissions Mapping
ROLE_PERMISSIONS: Dict[str, List[str]] = {
    SUPER_ADMIN: PERMISSIONS.copy(),
    ORGANIZATION_ADMIN: [
        "manage_own_organization",
        "invite_employees",
        "manage_org_datasets",
        "view_dashboards",
        "view_reports",
        "export_reports",
        "use_copilot",
        "view_allowed_datasets",
        "upload_dataset",
        "execute_ai",
        "execute_sql",
        "view_audit_logs",
        "view_all_audit_logs",
    ],
    EMPLOYEE: [
        "view_dashboards",
        "view_reports",
        "export_reports",
        "use_copilot",
        "view_allowed_datasets",
        "view_audit_logs",
        "view_all_audit_logs",
    ],
}

# Alias mappings for legacy role strings in permissions matrix
ROLE_PERMISSIONS["Super Admin"] = ROLE_PERMISSIONS[SUPER_ADMIN]
ROLE_PERMISSIONS["Administrator"] = ROLE_PERMISSIONS[SUPER_ADMIN]
ROLE_PERMISSIONS["Organization Admin"] = ROLE_PERMISSIONS[ORGANIZATION_ADMIN]
ROLE_PERMISSIONS["Analyst"] = ROLE_PERMISSIONS[EMPLOYEE]
ROLE_PERMISSIONS["Viewer"] = ROLE_PERMISSIONS[EMPLOYEE]


def get_current_user_from_token(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.replace("Bearer ", "").strip()
    payload = SecurityManager.decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    email = payload.get("sub", "")
    role = normalize_role(payload.get("role"))

    if email and email.lower() == settings.SUPER_ADMIN_EMAIL.lower():
        role = SUPER_ADMIN

    return {
        "email": email,
        "full_name": payload.get("full_name", email.split("@")[0].title() if email else "User"),
        "role": role,
        "tenant_id": payload.get("tenant_id", "company_enterprise_default")
    }


def require_role(allowed_roles: List[str]):
    def dependency(user: Dict[str, Any] = Depends(get_current_user_from_token)):
        normalized_allowed = [normalize_role(r) for r in allowed_roles]
        user_role = normalize_role(user.get("role"))
        if user_role not in normalized_allowed:
            raise HTTPException(
                status_code=403,
                detail=f"Access Denied: Required role in {allowed_roles}. User role '{user_role}' is not authorized."
            )
        return user
    return dependency


def require_permission(permission: str):
    def dependency(user: Dict[str, Any] = Depends(get_current_user_from_token)):
        role = normalize_role(user.get("role"))
        allowed = ROLE_PERMISSIONS.get(role, [])
        if permission not in allowed:
            raise HTTPException(
                status_code=403,
                detail=f"Permission Denied: Access requires '{permission}' permission. User role '{role}' is not authorized."
            )
        return user
    return dependency


def can_delete_workspace(user: Dict[str, Any], workspace_id: str) -> Dict[str, Any]:
    role = normalize_role(user.get("role"))
    if role in (SUPER_ADMIN, ORGANIZATION_ADMIN):
        return user

    from app.database.mongodb import workspaces as mongo_workspaces
    created_by = ""
    try:
        ws_doc = mongo_workspaces.find_one({"workspace_id": workspace_id}, {"created_by": 1})
        if ws_doc:
            created_by = ws_doc.get("created_by", "") or ""
    except Exception:
        pass

    if not created_by:
        try:
            from app.services.workspace_service import EnterpriseWorkspaceManager
            ws_mem = EnterpriseWorkspaceManager.get_workspace(workspace_id)
            if ws_mem:
                created_by = ws_mem.get("created_by", "") or ""
            elif workspace_id in EnterpriseWorkspaceManager._deleted_workspaces:
                return user
        except Exception:
            pass

    if created_by and user.get("email", "").lower() == created_by.lower():
        return user

    raise HTTPException(
        status_code=403,
        detail="Permission Denied: You are not authorized to delete this workspace. Contact your workspace admin.",
    )
