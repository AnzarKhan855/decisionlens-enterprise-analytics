import pytest
import io
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import SecurityManager

client = TestClient(app)

def test_unauthenticated_upload_returns_401():
    # Test unauthenticated /upload/
    res_single = client.post("/api/v1/upload/", files={"file": ("test.csv", b"a,b\n1,2", "text/csv")})
    assert res_single.status_code == 401, f"Expected 401, got {res_single.status_code}"

    # Test unauthenticated /upload/batch
    res_batch = client.post("/api/v1/upload/batch", files=[("files", ("test.csv", b"a,b\n1,2", "text/csv"))])
    assert res_batch.status_code == 401, f"Expected 401, got {res_batch.status_code}"

    # Test unauthenticated /workspace/upload-zip
    res_zip = client.post("/api/v1/workspace/upload-zip", files={"file": ("test.zip", b"PK\x03\x04", "application/zip")})
    assert res_zip.status_code == 401, f"Expected 401, got {res_zip.status_code}"

def test_authenticated_upload_accepted():
    token = SecurityManager.create_access_token({"sub": "admin@enterprise.com", "role": "SUPER_ADMIN"})
    headers = {"Authorization": f"Bearer {token}"}

    csv_data = b"Category,Quantity,Price\nA,10,25.5\nB,20,50.0\n"
    res = client.post(
        "/api/v1/upload/batch",
        files=[("files", ("sales.csv", io.BytesIO(csv_data), "text/csv"))],
        headers=headers
    )
    assert res.status_code in (200, 201), f"Expected 200/201 for authenticated upload, got {res.status_code}: {res.text}"
    json_data = res.json()
    assert "processed_datasets" in json_data or "message" in json_data
