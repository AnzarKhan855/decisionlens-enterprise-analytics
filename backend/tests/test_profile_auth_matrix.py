import pytest
import time
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import SecurityManager

client = TestClient(app)

def test_user_profile_name_parsing_matrix():
    # 1. Full name user
    reg1 = {
        "email": "john.doe@decisionlens.ai",
        "password": "Password123!",
        "full_name": "John Doe",
        "organization": "Acme Corp",
        "role": "EMPLOYEE"
    }
    client.post("/api/v1/auth/register", json=reg1)
    l1 = client.post("/api/v1/auth/login", json={"email": reg1["email"], "password": reg1["password"]}).json()
    t1 = l1.get("access_token")
    me1 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {t1}"}).json()
    assert me1["full_name"] == "John Doe"

    # 2. First name only user
    reg2 = {
        "email": "adminonly@decisionlens.ai",
        "password": "Password123!",
        "full_name": "Administrator",
        "organization": "Acme Corp",
        "role": "EMPLOYEE"
    }
    client.post("/api/v1/auth/register", json=reg2)
    l2 = client.post("/api/v1/auth/login", json={"email": reg2["email"], "password": reg2["password"]}).json()
    t2 = l2.get("access_token")
    me2 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {t2}"}).json()
    assert me2["full_name"] == "Administrator"

def test_jwt_auth_matrix_and_expiration():
    # Missing JWT
    assert client.get("/api/v1/auth/me").status_code == 401

    # Invalid JWT
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid.jwt.token"}).status_code == 401

    # Expired JWT
    expired_token = SecurityManager.create_access_token({"sub": "expired@decisionlens.ai", "role": "EMPLOYEE"}, expires_in=-100)
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"}).status_code == 401
