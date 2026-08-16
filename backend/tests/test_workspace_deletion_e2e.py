import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.workspace_service import EnterpriseWorkspaceManager
from app.database.connection import SessionLocal

client = TestClient(app)

def get_auth_token():
    import uuid
    email = f"deleter_{uuid.uuid4().hex[:6]}@decisionlens.ai"
    reg_payload = {
        "email": email,
        "password": "Password123!",
        "full_name": "Deleter Admin",
        "organization": "Deletion Enterprise",
        "role": "EMPLOYEE"
    }
    client.post("/api/v1/auth/register", json=reg_payload)
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    data = login_res.json()
    token = data.get("access_token")
    if not token and data.get("require_otp"):
        otp_res = client.post("/api/v1/auth/verify-otp", json={"email": email, "otp_code": data.get("otp_code", "123456")})
        token = otp_res.json().get("access_token")
    return token, email

def test_workspace_deletion_e2e_and_isolation():
    token, email = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Create Workspace A created by email
    ws_a = EnterpriseWorkspaceManager.create_or_get_workspace("ws-test-a", "Workspace Alpha", industry="Retail", created_by=email)
    EnterpriseWorkspaceManager.register_table("ws-test-a", "sales_a", [{"name": "revenue", "type": "FLOAT"}], 100, "dummy_a.parquet")

    # Create Workspace B
    ws_b = EnterpriseWorkspaceManager.create_or_get_workspace("ws-test-b", "Workspace Beta", industry="Finance", created_by=email)
    EnterpriseWorkspaceManager.register_table("ws-test-b", "trades_b", [{"name": "amount", "type": "FLOAT"}], 200, "dummy_b.parquet")

    # Verify both exist
    assert EnterpriseWorkspaceManager.get_workspace("ws-test-a") is not None
    assert EnterpriseWorkspaceManager.get_workspace("ws-test-b") is not None

    # Delete Workspace A via API with JWT (as creator)
    del_res = client.delete("/api/v1/workspaces/ws-test-a", headers=headers)
    assert del_res.status_code == 200, f"Deletion failed: {del_res.text}"
    assert del_res.json()["status"] == "success"

    # Verify Workspace A is gone
    assert EnterpriseWorkspaceManager.get_workspace("ws-test-a") is None
    assert "ws-test-a" in EnterpriseWorkspaceManager._deleted_workspaces

    # Verify Workspace B remains untouched
    assert EnterpriseWorkspaceManager.get_workspace("ws-test-b") is not None

    # Test unauthenticated deletion returns 401
    unauth_res = client.delete("/api/v1/workspaces/ws-test-b")
    assert unauth_res.status_code == 401

    # Cleanup Workspace B
    client.delete("/api/v1/workspaces/ws-test-b", headers=headers)

def test_deletion_logging_path_with_no_files_or_none():
    import uuid
    email = f"admin_{uuid.uuid4().hex[:6]}@decisionlens.ai"
    reg_payload = {
        "email": email,
        "password": "Password123!",
        "full_name": "Org Admin",
        "organization": "Deletion Org",
        "role": "ORGANIZATION_ADMIN"
    }
    client.post("/api/v1/auth/register", json=reg_payload)
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    token = login_res.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}

    # Create workspace with 0 files
    ws = EnterpriseWorkspaceManager.create_or_get_workspace("ws-empty-files", "Empty Files WS", created_by=email)

    # Delete dataset directly via datasets API
    res = client.delete("/api/v1/datasets/ws-empty-files", headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "success"

def test_workspace_deletion_authorization_matrix():
    token_a, email_a = get_auth_token()
    token_b, email_b = get_auth_token()

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Create workspace owned by email_a
    EnterpriseWorkspaceManager.create_or_get_workspace("ws-auth-test", "Auth Test WS", created_by=email_a)

    # 1. No JWT -> 401
    assert client.delete("/api/v1/workspaces/ws-auth-test").status_code == 401

    # 2. Invalid JWT -> 401
    assert client.delete("/api/v1/workspaces/ws-auth-test", headers={"Authorization": "Bearer invalid_token_123"}).status_code == 401

    # 3. Non-owner -> 403
    non_owner_res = client.delete("/api/v1/workspaces/ws-auth-test", headers=headers_b)
    assert non_owner_res.status_code == 403

    # 4. Owner -> 200 Success
    owner_res = client.delete("/api/v1/workspaces/ws-auth-test", headers=headers_a)
    assert owner_res.status_code == 200

    # 5. Idempotent repeated deletion -> Safe (200 or 404)
    repeat_res = client.delete("/api/v1/workspaces/ws-auth-test", headers=headers_a)
    assert repeat_res.status_code in (200, 404)
