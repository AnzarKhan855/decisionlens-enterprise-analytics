"""
End-to-end test suite for workspace deletion.

Tests:
  1. Unauthenticated request returns 401
  2. Super admin can delete any workspace
  3. Workspace creator (owner) can delete their own workspace
  4. Non-owner, non-admin gets 403
  5. Org admin can delete any workspace
  6. Deleted workspace is removed from list; other workspaces untouched
  7. MongoDB workspace-scoped collections cleaned
  8. SQLite dataset records cleaned via file_path matching
  9. Other workspace's data remains untouched
  10. Double-delete returns 404
"""

import sys
import os
import time
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient

from app.main import app

from app.core.security import SecurityManager
from app.core.rbac import SUPER_ADMIN, ORGANIZATION_ADMIN, EMPLOYEE
from app.services.workspace_service import EnterpriseWorkspaceManager, DELETED_WORKSPACES_FILE, WORKSPACES_FILE
from app.database.mongodb import workspaces as mongo_workspaces, datasets as mongo_datasets
from app.database.connection import SessionLocal
from app.database.models import Dataset
from app.api.v1.auth import RATE_LIMIT_STORE
from app.core.config import settings


client = TestClient(app)

SUPER_ADMIN_EMAIL = settings.SUPER_ADMIN_EMAIL.lower()
SUPER_ADMIN_PASSWORD = settings.SUPER_ADMIN_PASSWORD


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _clear_workspace_state():
    EnterpriseWorkspaceManager._workspaces.clear()
    EnterpriseWorkspaceManager._deleted_workspaces.clear()
    EnterpriseWorkspaceManager._active_workspace_id = None
    EnterpriseWorkspaceManager._loaded = False
    for f in [WORKSPACES_FILE, DELETED_WORKSPACES_FILE]:
        if f.exists():
            f.unlink()


def _make_workspace(ws_id: str, created_by: str = "") -> dict:
    ws = EnterpriseWorkspaceManager.create_or_get_workspace(ws_id, f"Test {ws_id}", created_by=created_by)
    EnterpriseWorkspaceManager.register_table(
        ws_id, "sales",
        [{"name": "amount", "type": "FLOAT"}],
        100, f"/tmp/storage/parquet/{ws_id}__sales.parquet"
    )
    EnterpriseWorkspaceManager.set_active_workspace(ws_id)
    return ws


def _login_super_admin() -> str:
    RATE_LIMIT_STORE.clear()
    from app.database.connection import SessionLocal as _SL
    from app.database.crud import invalidate_otp_tokens as _invalidate
    from app.core.security import SecurityManager as _SM
    import hashlib as _hashlib
    raw_otp = "000000"
    hashed_otp = _hashlib.sha256(raw_otp.encode()).hexdigest()
    db = _SL()
    try:
        _invalidate(db, SUPER_ADMIN_EMAIL)
        from app.database.crud import create_otp_token
        from datetime import UTC, datetime, timedelta
        from app.database.models import OTPToken
        otp = OTPToken(
            email=SUPER_ADMIN_EMAIL,
            hashed_otp=hashed_otp,
            expiry=datetime.now(UTC) + timedelta(seconds=300),
            attempts=0,
        )
        db.add(otp)
        db.commit()
    finally:
        db.close()

    res = client.post("/api/v1/auth/verify-otp", json={"email": SUPER_ADMIN_EMAIL, "otp_code": raw_otp})
    assert res.status_code == 200, f"OTP verify failed: {res.text}"
    return res.json()["access_token"]


def _register_and_login(email: str, password: str, role: str) -> str:
    client.post("/api/v1/auth/register", json={"email": email, "password": password, "full_name": "Test User", "role": role})
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_unauthenticated_delete_returns_401():
    _clear_workspace_state()
    ws_id = f"ws-unauth-{uuid.uuid4().hex[:6]}"
    _make_workspace(ws_id)

    res = client.delete(f"/api/v1/workspaces/{ws_id}")
    assert res.status_code == 401, f"Expected 401, got {res.status_code}: {res.text}"
    print("[PASS] test_unauthenticated_delete_returns_401")


def test_super_admin_can_delete_workspace():
    _clear_workspace_state()
    ws_id = f"ws-sa-{uuid.uuid4().hex[:6]}"
    _make_workspace(ws_id)

    token = _login_super_admin()
    res = client.delete(f"/api/v1/workspaces/{ws_id}", headers=_auth_headers(token))
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    body = res.json()
    assert body["status"] == "success"
    assert body["workspace_id"] == ws_id
    assert EnterpriseWorkspaceManager.get_workspace(ws_id) is None
    print("[PASS] test_super_admin_can_delete_workspace")


def test_workspace_creator_can_delete_own_workspace():
    _clear_workspace_state()
    ws_id = f"ws-owner-{uuid.uuid4().hex[:6]}"
    owner_email = f"owner-{uuid.uuid4().hex[:6]}@test.com"
    _make_workspace(ws_id, created_by=owner_email)

    owner_token = _register_and_login(owner_email, "OwnerPass123!", EMPLOYEE)
    res = client.delete(f"/api/v1/workspaces/{ws_id}", headers=_auth_headers(owner_token))
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    assert EnterpriseWorkspaceManager.get_workspace(ws_id) is None
    print("[PASS] test_workspace_creator_can_delete_own_workspace")


def test_non_owner_non_admin_gets_403():
    _clear_workspace_state()
    ws_id = f"ws-nonowner-{uuid.uuid4().hex[:6]}"
    owner_email = f"owner2-{uuid.uuid4().hex[:6]}@test.com"
    intruder_email = f"intruder-{uuid.uuid4().hex[:6]}@test.com"
    _make_workspace(ws_id, created_by=owner_email)

    intruder_token = _register_and_login(intruder_email, "IntruderPass123!", EMPLOYEE)
    res = client.delete(f"/api/v1/workspaces/{ws_id}", headers=_auth_headers(intruder_token))
    assert res.status_code == 403, f"Expected 403, got {res.status_code}: {res.text}"
    assert EnterpriseWorkspaceManager.get_workspace(ws_id) is not None
    print("[PASS] test_non_owner_non_admin_gets_403")


def test_org_admin_can_delete_any_workspace():
    _clear_workspace_state()
    ws_id = f"ws-orgadmin-{uuid.uuid4().hex[:6]}"
    admin_email = f"orgadmin-{uuid.uuid4().hex[:6]}@test.com"
    _make_workspace(ws_id, created_by="someone-else@test.com")

    admin_token = _register_and_login(admin_email, "OrgAdminPass123!", ORGANIZATION_ADMIN)
    res = client.delete(f"/api/v1/workspaces/{ws_id}", headers=_auth_headers(admin_token))
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    assert EnterpriseWorkspaceManager.get_workspace(ws_id) is None
    print("[PASS] test_org_admin_can_delete_any_workspace")


def test_deleted_workspace_removed_from_list():
    _clear_workspace_state()
    ws_to_delete = f"ws-listdel-{uuid.uuid4().hex[:6]}"
    ws_to_keep = f"ws-listkeep-{uuid.uuid4().hex[:6]}"
    _make_workspace(ws_to_delete)
    _make_workspace(ws_to_keep)

    token = _login_super_admin()
    res = client.delete(f"/api/v1/workspaces/{ws_to_delete}", headers=_auth_headers(token))
    assert res.status_code == 200

    all_ws = EnterpriseWorkspaceManager.get_all_workspaces()
    ids = [w["workspace_id"] for w in all_ws]
    assert ws_to_delete not in ids, "Deleted workspace still appears in list"
    assert ws_to_keep in ids, "Unrelated workspace was removed"
    print("[PASS] test_deleted_workspace_removed_from_list")


def test_workspace_scoped_mongo_collections_cleaned():
    _clear_workspace_state()
    ws_id = f"ws-mongo-{uuid.uuid4().hex[:6]}"
    _make_workspace(ws_id)
    mongo_workspaces.insert_one({"workspace_id": ws_id, "test": True})
    mongo_datasets.insert_one({"workspace_id": ws_id, "filename": "test.csv", "file_path": f"/tmp/{ws_id}__test.parquet"})

    token = _login_super_admin()
    res = client.delete(f"/api/v1/workspaces/{ws_id}", headers=_auth_headers(token))
    assert res.status_code == 200

    assert mongo_workspaces.count_documents({"workspace_id": ws_id}) == 0
    assert mongo_datasets.count_documents({"workspace_id": ws_id}) == 0
    print("[PASS] test_workspace_scoped_mongo_collections_cleaned")


def test_sqlite_datasets_cleaned_on_workspace_delete():
    _clear_workspace_state()
    ws_id = f"ws-sqlite-{uuid.uuid4().hex[:6]}"
    _make_workspace(ws_id)

    db = SessionLocal()
    try:
        ds = Dataset(
            filename=f"{ws_id}__sales.parquet",
            file_path=f"/tmp/storage/parquet/{ws_id}__sales.parquet",
            dataset_type="test", rows=10, columns=2, file_type="parquet"
        )
        db.add(ds)
        db.commit()
        ds_id = ds.id
    finally:
        db.close()

    token = _login_super_admin()
    res = client.delete(f"/api/v1/workspaces/{ws_id}", headers=_auth_headers(token))
    assert res.status_code == 200

    db = SessionLocal()
    try:
        remaining = db.query(Dataset).filter(Dataset.id == ds_id).first()
        assert remaining is None, "SQLite dataset record was not deleted"
    finally:
        db.close()
    print("[PASS] test_sqlite_datasets_cleaned_on_workspace_delete")


def test_other_workspace_data_untouched():
    _clear_workspace_state()
    ws_to_delete = f"ws-otherdel-{uuid.uuid4().hex[:6]}"
    ws_to_keep = f"ws-otherkeep-{uuid.uuid4().hex[:6]}"
    _make_workspace(ws_to_delete)
    _make_workspace(ws_to_keep)
    mongo_workspaces.insert_one({"workspace_id": ws_to_keep, "test": True})

    token = _login_super_admin()
    res = client.delete(f"/api/v1/workspaces/{ws_to_delete}", headers=_auth_headers(token))
    assert res.status_code == 200

    assert EnterpriseWorkspaceManager.get_workspace(ws_to_keep) is not None
    assert mongo_workspaces.count_documents({"workspace_id": ws_to_keep}) == 1
    print("[PASS] test_other_workspace_data_untouched")


def test_deleted_workspace_cannot_be_deleted_again():
    _clear_workspace_state()
    ws_id = f"ws-redel-{uuid.uuid4().hex[:6]}"
    _make_workspace(ws_id)

    token = _login_super_admin()
    res1 = client.delete(f"/api/v1/workspaces/{ws_id}", headers=_auth_headers(token))
    assert res1.status_code == 200

    res2 = client.delete(f"/api/v1/workspaces/{ws_id}", headers=_auth_headers(token))
    assert res2.status_code == 404, f"Expected 404 on re-delete, got {res2.status_code}"
    print("[PASS] test_deleted_workspace_cannot_be_deleted_again")


def run_all_tests():
    print("\n==================================================")
    print("WORKSPACE DELETION END-TO-END TEST SUITE")
    print("==================================================")
    test_unauthenticated_delete_returns_401()
    test_super_admin_can_delete_workspace()
    test_workspace_creator_can_delete_own_workspace()
    test_non_owner_non_admin_gets_403()
    test_org_admin_can_delete_any_workspace()
    test_deleted_workspace_removed_from_list()
    test_workspace_scoped_mongo_collections_cleaned()
    test_sqlite_datasets_cleaned_on_workspace_delete()
    test_other_workspace_data_untouched()
    test_deleted_workspace_cannot_be_deleted_again()
    print("==================================================")
    print("ALL WORKSPACE DELETION TESTS PASSED!")
    print("==================================================\n")


if __name__ == "__main__":
    run_all_tests()
