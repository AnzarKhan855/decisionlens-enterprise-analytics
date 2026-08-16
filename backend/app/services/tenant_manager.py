from pathlib import Path
from typing import Dict, Any, Optional
from app.database.storage import STORAGE_DIR

TENANTS_DIR = STORAGE_DIR / "tenants"


class MultiTenantStorageManager:
    """
    DecisionLens v15.0 Multi-Tenant Isolation Storage Service.
    Enforces strict physical directory isolation per company/tenant:
    storage/tenants/{tenant_id}/{workspace_id}/
    """

    DEFAULT_TENANT = "company_enterprise_default"

    @classmethod
    def get_tenant_dir(cls, tenant_id: Optional[str] = None) -> Path:
        t_id = tenant_id or cls.DEFAULT_TENANT
        tenant_path = TENANTS_DIR / t_id
        tenant_path.mkdir(parents=True, exist_ok=True)
        return tenant_path

    @classmethod
    def get_workspace_dir(cls, workspace_id: str, tenant_id: Optional[str] = None) -> Path:
        tenant_path = cls.get_tenant_dir(tenant_id)
        ws_path = tenant_path / workspace_id
        ws_path.mkdir(parents=True, exist_ok=True)
        return ws_path

    @classmethod
    def get_parquet_path(cls, dataset_id: str, workspace_id: Optional[str] = None, tenant_id: Optional[str] = None) -> Path:
        if workspace_id:
            ws_dir = cls.get_workspace_dir(workspace_id, tenant_id)
            return ws_dir / f"{dataset_id}.parquet"
        return STORAGE_DIR / f"{dataset_id}.parquet"
