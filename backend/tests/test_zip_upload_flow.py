import os
import io
import zipfile
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import SecurityManager

client = TestClient(app)

@pytest.fixture
def auth_headers():
    token = SecurityManager.create_access_token({"sub": "admin@enterprise.com", "role": "SUPER_ADMIN"})
    return {"Authorization": f"Bearer {token}"}

def create_sample_zip_bytes():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        csv_data = "date,revenue,quantity,category\n2026-01-01,1000,5,Electronics\n2026-01-02,1500,8,Electronics\n2026-01-03,800,12,Apparel\n"
        zf.writestr("sales_data.csv", csv_data)
    buf.seek(0)
    return buf.getvalue()

def test_unauthenticated_zip_upload_returns_401():
    zip_bytes = create_sample_zip_bytes()
    response = client.post("/api/v1/workspace/upload-zip", files={"file": ("test.zip", zip_bytes, "application/zip")})
    assert response.status_code == 401
    assert "Authorization" in response.json().get("detail", "") or "Bearer" in response.json().get("detail", "")

def test_missing_file_parameter_returns_422(auth_headers):
    response = client.post("/api/v1/workspace/upload-zip", headers=auth_headers)
    assert response.status_code == 422
    assert "detail" in response.json()

def test_invalid_file_extension_returns_400(auth_headers):
    response = client.post(
        "/api/v1/workspace/upload-zip",
        headers=auth_headers,
        files={"file": ("test.txt", b"plain text content", "text/plain")}
    )
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "error"
    assert "Only .zip archive files are supported" in data["message"]

def test_corrupt_zip_archive_returns_400(auth_headers):
    response = client.post(
        "/api/v1/workspace/upload-zip",
        headers=auth_headers,
        files={"file": ("corrupt.zip", b"not a zip file", "application/zip")}
    )
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "error"
    assert "corrupted" in data["message"].lower() or "badzipfile" in data["exception"].lower()

def test_valid_zip_upload_ingestion_succeeds(auth_headers):
    zip_bytes = create_sample_zip_bytes()
    response = client.post(
        "/api/v1/workspace/upload-zip",
        headers=auth_headers,
        files={"file": ("enterprise_dataset.zip", zip_bytes, "application/zip")},
        data={"workspace_name": "Test Orlys Enterprise"}
    )
    assert response.status_code in (200, 201)
    data = response.json()
    assert data["status"] == "success"
    assert "workspace_id" in data
    assert data["workspace_name"] == "Test Orlys Enterprise"
    assert len(data["tables"]) > 0
