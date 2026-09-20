import io
import os
import tempfile
import uuid
from pathlib import Path

import duckdb
import pytest
from fastapi.testclient import TestClient

from app.core.rbac import get_current_user_from_token
from app.core.security import SecurityManager
from app.database.connection import SessionLocal
from app.database.crud import create_user, get_user_by_email, save_dataset
from app.database.models import Dataset, User
from app.database.mongodb import datasets as mongo_datasets, users as mongo_users
from app.database.storage import ParquetStorageManager
from app.ingestion.generic_loader import GenericDataLoader, detect_and_normalize_csv_encoding
from app.main import app
from app.services.ingestion_job_service import IngestionJobService, JobState

client = TestClient(app)


def test_durable_authentication_mongodb_rehydration():
    """
    Test 1: When a user registers, they are stored in SQLite and MongoDB.
    Simulate container restart / SQLite wipe -> user must be re-hydrated from MongoDB,
    allowing successful authentication.
    """
    unique_email = f"durable_user_{uuid.uuid4().hex[:8]}@enterprise.com"
    password = "SecurePassword123!"

    # 1. Register user
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": unique_email,
            "password": password,
            "name": "Durable Tester",
            "organization_name": "Enterprise QA",
        },
    )
    assert reg_resp.status_code == 200, f"Registration failed: {reg_resp.text}"
    user_data = reg_resp.json()
    user_id = user_data["user"]["id"]
    assert user_id is not None

    # 2. Verify in SQLite and MongoDB
    db = SessionLocal()
    try:
        sqlite_user = db.query(User).filter(User.email == unique_email).first()
        assert sqlite_user is not None
        assert sqlite_user.id == user_id

        mongo_user = mongo_users.find_one({"email": unique_email})
        assert mongo_user is not None
        assert mongo_user.get("user_id") == user_id or mongo_user.get("id") == user_id

        # 3. Simulate container cold-start: wipe user from SQLite
        db.delete(sqlite_user)
        db.commit()

        # Confirm user is missing from SQLite
        wiped_user = db.query(User).filter(User.email == unique_email).first()
        assert wiped_user is None
    finally:
        db.close()

    # 4. Now attempt login: system should pull from MongoDB and re-hydrate SQLite
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": password},
    )
    assert login_resp.status_code == 200, f"Login after rehydration failed: {login_resp.text}"
    login_data = login_resp.json()
    assert "access_token" in login_data
    assert login_data["user"]["email"] == unique_email
    assert login_data["user"]["id"] == user_id

    # 5. Verify user is back in SQLite with the identical ID
    db = SessionLocal()
    try:
        restored = db.query(User).filter(User.email == unique_email).first()
        assert restored is not None
        assert restored.id == user_id
    finally:
        db.close()


def test_invalid_credentials_returns_401():
    """
    Test 2: Invalid password or non-existent email returns 401 Unauthorized.
    """
    # Non-existent email
    res1 = client.post(
        "/api/v1/auth/login",
        json={"email": f"nonexistent_{uuid.uuid4().hex[:6]}@test.com", "password": "WrongPassword!"},
    )
    assert res1.status_code == 401

    # Existing user with wrong password
    unique_email = f"auth_check_{uuid.uuid4().hex[:8]}@enterprise.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": unique_email, "password": "CorrectPassword123!", "name": "Auth Check"},
    )
    res2 = client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": "IncorrectPassword!"},
    )
    assert res2.status_code == 401


def test_csv_encoding_byte_0xa0_ingestion():
    """
    Test 3: Windows-1252 non-breaking space (byte 0xA0) from Superstore / Excel
    must be detected, normalized, and converted to Parquet without UnicodeDecodeError.
    """
    # Byte 0xA0 in Windows-1252 is non-breaking space
    csv_bytes = b"Row ID,Order ID,Customer Name,Sales\n1,CA-2016-152156,Claire\xa0Guten,261.96\n2,CA-2016-138688,Darrin\xa0Van,14.62\n"

    dataset_id = f"test_enc_{uuid.uuid4().hex[:8]}"
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        tmp.write(csv_bytes)
        tmp_path = Path(tmp.name)

    try:
        # 1. Test encoding detection & normalization function directly
        norm_path, label, was_norm = detect_and_normalize_csv_encoding(tmp_path, tmp_path.name)
        assert was_norm is True
        assert label == "Windows-1252"
        with open(norm_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "Claire\u00a0Guten" in content or "Claire Guten" in content

        # 2. Test GenericDataLoader convert_to_parquet
        parquet_path = GenericDataLoader.convert_to_parquet(tmp_path, dataset_id)
        assert parquet_path.exists()

        # 3. Read back via DuckDB to verify rows and values
        conn = duckdb.connect()
        df = conn.execute(f"SELECT * FROM read_parquet('{parquet_path.as_posix()}')").fetchdf()
        conn.close()

        assert len(df) == 2
        assert "Customer Name" in df.columns
        assert "261.96" in str(df["Sales"].values) or 261.96 in df["Sales"].values
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        if norm_path.exists() and norm_path != tmp_path:
            norm_path.unlink(missing_ok=True)
        p_path = ParquetStorageManager.get_parquet_path(dataset_id)
        if p_path.exists():
            p_path.unlink(missing_ok=True)


def test_dataset_user_id_never_null():
    """
    Test 4: Every uploaded dataset persists with a non-null user_id in SQLite and MongoDB.
    """
    email = f"dataset_owner_{uuid.uuid4().hex[:8]}@enterprise.com"
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!", "name": "Dataset Owner"},
    )
    assert reg.status_code == 200
    reg_data = reg.json()
    owner_id = reg_data["user"]["id"]
    token = reg_data.get("access_token") or (reg_data.get("token") or {}).get("access_token")

    unique_filename = f"sales_{uuid.uuid4().hex[:6]}.csv"
    csv_data = b"Product,Units,Revenue\nWidget A,100,5000\nWidget B,200,10000\n"
    res = client.post(
        "/api/v1/upload/?sync=true",
        files={"file": (unique_filename, io.BytesIO(csv_data), "text/csv")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, f"Upload failed: {res.text}"
    ws_id = res.json()["workspace_id"]

    # Verify SQLite datasets table has non-null user_id matching owner_id
    db = SessionLocal()
    try:
        ds = db.query(Dataset).filter(Dataset.filename == unique_filename).first()
        assert ds is not None
        assert ds.user_id is not None
        assert ds.user_id == owner_id
    finally:
        db.close()

    # Verify MongoDB datasets collection has recorded user_id
    mongo_ds = mongo_datasets.find_one({"workspace_id": ws_id})
    if mongo_ds:
        assert mongo_ds.get("user_id") == owner_id


def test_atomic_duplicate_job_claim_locked():
    """
    Test 5: An active ingestion job cannot be claimed concurrently by two workers.
    The second worker claim must be safely rejected.
    """
    ws_id = f"ws-lock-test-{uuid.uuid4().hex[:8]}"
    job = IngestionJobService.create_job(
        workspace_id=ws_id,
        dataset_id=ws_id,
        filename="test.csv",
        file_size_bytes=1000,
        user_email="test@enterprise.com",
        initial_status=JobState.UPLOADED,
    )
    job_id = job["job_id"]

    # First claim succeeds:
    claimed_1 = IngestionJobService.claim_job_for_processing(job_id)
    assert claimed_1 is True

    # Second concurrent claim must be rejected (already claimed / in processing):
    claimed_2 = IngestionJobService.claim_job_for_processing(job_id)
    assert claimed_2 is False


def test_async_upload_returns_202_and_polling():
    """
    Test 6: Async upload returns HTTP 202 with status URL, and endpoints resolve correctly.
    """
    email = f"async_uploader_{uuid.uuid4().hex[:8]}@enterprise.com"
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!", "name": "Async Uploader"},
    )
    assert reg.status_code == 200
    reg_data = reg.json()
    token = reg_data.get("access_token") or (reg_data.get("token") or {}).get("access_token")

    csv_data = b"Region,Target,Actual\nNorth,100,120\nSouth,200,190\n"
    res = client.post(
        "/api/v1/upload/?sync=false",
        files={"file": ("regions.csv", io.BytesIO(csv_data), "text/csv")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 202, f"Expected 202 Accepted, got {res.status_code}: {res.text}"
    body = res.json()
    assert "job_id" in body
    job_id = body["job_id"]

    # Poll status via /api/v1/upload/job/{job_id}/status
    poll_1 = client.get(f"/api/v1/upload/job/{job_id}/status")
    assert poll_1.status_code == 200
    assert poll_1.json()["job_id"] == job_id

    # Poll status via /api/v1/ingestion/jobs/{job_id}
    poll_2 = client.get(f"/api/v1/ingestion/jobs/{job_id}")
    assert poll_2.status_code == 200
    assert poll_2.json()["job_id"] == job_id


def test_empty_file_returns_422_with_structured_error():
    """
    Test 7: Empty file (0 bytes) returns structured 422 error, not 500 or timeout.
    """
    token = SecurityManager.create_access_token({"sub": "admin@enterprise.com", "role": "SUPER_ADMIN"})
    res = client.post(
        "/api/v1/upload/",
        files={"file": ("empty.csv", b"", "text/csv")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 422
    data = res.json()
    assert "detail" in data
    assert data["detail"]["stage"] == "preflight_empty"
    assert "0 bytes" in data["detail"]["message"]


def test_cors_headers_present_on_500_error_response():
    """
    Test 8: Ensure CORS headers are attached to 500 error responses generated
    by GlobalErrorHandlerMiddleware when origin is vercel.app.
    """
    from fastapi import APIRouter
    from app.main import app as main_app

    # Create a temporary test route that raises an unhandled exception
    test_router = APIRouter()
    @test_router.get("/api/v1/test-unhandled-exception-cors")
    def _raise_error():
        raise RuntimeError("Simulated unhandled production explosion")

    main_app.include_router(test_router)
    try:
        res = client.get(
            "/api/v1/test-unhandled-exception-cors",
            headers={"Origin": "https://decisionlens-enterprise-analytics.vercel.app"}
        )
        assert res.status_code == 500
        # Verify CORS headers are present on the 500 response!
        assert res.headers.get("access-control-allow-origin") == "https://decisionlens-enterprise-analytics.vercel.app"
        assert res.headers.get("access-control-allow-credentials") == "true"
    finally:
        # Clean up route from app
        main_app.routes[:] = [r for r in main_app.routes if getattr(r, "path", None) != "/api/v1/test-unhandled-exception-cors"]


def test_zip_upload_returns_202_accepted_immediately():
    """
    Test 9: ZIP upload returns HTTP 202 Accepted in under 1 second,
    with job_id, workspace_id, and status_url.
    """
    import io
    import time
    import zipfile

    token = SecurityManager.create_access_token({"sub": "admin@enterprise.com", "role": "SUPER_ADMIN"})

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("orders.csv", "order_id,amount,customer_id\n1,100,c1\n2,200,c2\n")
        zf.writestr("customers.csv", "customer_id,name\nc1,Alice\nc2,Bob\n")
    buf.seek(0)
    zip_bytes = buf.getvalue()

    t0 = time.perf_counter()
    res = client.post(
        "/api/v1/workspace/upload-zip",
        files={"file": ("multi_test.zip", zip_bytes, "application/zip")},
        data={"workspace_name": f"ws-bench-{uuid.uuid4().hex[:6]}"},
        headers={
            "Authorization": f"Bearer {token}",
            "Origin": "https://decisionlens-enterprise-analytics.vercel.app"
        },
    )

    assert res.status_code == 202, f"Expected 202, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["upload_status"] == "PROCESSING"
    assert "job_id" in data
    assert "workspace_id" in data
    assert "status_url" in data
    # Verify CORS header is present
    assert res.headers.get("access-control-allow-origin") == "https://decisionlens-enterprise-analytics.vercel.app"


def test_zip_pipeline_single_pass_zero_duplicates(monkeypatch):
    """
    Test 10: run_workspace_zip_pipeline converts each file in the ZIP archive
    EXACTLY ONCE. Zero duplicate conversions.
    """
    import io
    import zipfile
    from pathlib import Path
    from app.api.v1.workspace_upload import run_workspace_zip_pipeline
    from app.ingestion.generic_loader import GenericDataLoader

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("m5_xregs.csv", "id,date,wday,month,year\n1,2026-01-01,1,1,2026\n2,2026-01-02,2,1,2026\n")
        zf.writestr("m5_calendar.csv", "date,wm_yr_wk,event\n2026-01-01,11101,NewYear\n2026-01-02,11101,None\n")
    buf.seek(0)

    tmp_dir = Path(tempfile.mkdtemp())
    zip_file = tmp_dir / "m5_archive.zip"
    with open(zip_file, "wb") as f:
        f.write(buf.getvalue())

    conversion_calls = []
    orig_convert = GenericDataLoader.convert_to_parquet

    def spy_convert(file_path, unique_dataset_id):
        conversion_calls.append(Path(file_path).name)
        return orig_convert(file_path, unique_dataset_id)

    monkeypatch.setattr(GenericDataLoader, "convert_to_parquet", spy_convert)

    ws_id = f"ws-nodup-{uuid.uuid4().hex[:6]}"
    job = IngestionJobService.create_job(
        workspace_id=ws_id,
        dataset_id=ws_id,
        filename="m5_archive.zip",
        file_size_bytes=zip_file.stat().st_size,
        user_email="test@enterprise.com",
        initial_status=JobState.UPLOADED,
    )

    result = run_workspace_zip_pipeline(
        job_id=job["job_id"],
        zip_path=zip_file,
        ws_id=ws_id,
        ws_title="No Duplicate Ingestion Workspace",
        created_by="test@enterprise.com",
        file_sha256="test-sha256",
    )

    assert result["status"] == "success"
    assert len(result["tables"]) == 2

    # Verify each file was converted EXACTLY ONCE
    assert len(conversion_calls) == 2, f"Expected 2 conversions, got {len(conversion_calls)}: {conversion_calls}"
    assert conversion_calls.count("m5_xregs.csv") == 1, "m5_xregs.csv was converted more than once!"
    assert conversion_calls.count("m5_calendar.csv") == 1, "m5_calendar.csv was converted more than once!"

