import io
import time
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app
from app.services.ingestion_job_service import IngestionJobService, JobState
from app.core.security import SecurityManager


@pytest.fixture
def auth_headers():
    token = SecurityManager.create_access_token({"sub": "test-engineer@decisionlens.ai", "role": "admin"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client():
    return TestClient(app)


class TestAsyncIngestionJobStateMachine:
    """Unit and integration tests for the asynchronous ingestion job state machine."""

    def test_job_state_machine_lifecycle(self):
        """Verify complete linear progression of the ingestion job state machine."""
        ws_id = "ws-test-state-machine"
        job_doc = IngestionJobService.create_job(
            workspace_id=ws_id,
            dataset_id="ds-test-1",
            filename="transactions.csv",
            file_size_bytes=1024 * 1024,
            user_email="test@decisionlens.ai",
            initial_status=JobState.CREATED,
        )
        job_id = job_doc["job_id"]
        assert job_id.startswith("job-")

        # Initial state
        job = IngestionJobService.get_job(job_id)
        assert job is not None
        assert job["status"] == JobState.CREATED.value

        # Step 1: Uploading -> Uploaded
        IngestionJobService.update_job(job_id, status=JobState.UPLOADING, progress_pct=10, message="Uploading chunks")
        job = IngestionJobService.get_job(job_id)
        assert job["status"] == JobState.UPLOADING.value
        assert job["progress_pct"] == 10

        IngestionJobService.update_job(job_id, status=JobState.UPLOADED, progress_pct=20, message="Uploaded")
        assert IngestionJobService.get_job(job_id)["status"] == JobState.UPLOADED.value

        # Step 2: Validating
        IngestionJobService.update_job(job_id, status=JobState.VALIDATING, progress_pct=30, message="Validating format")
        assert IngestionJobService.get_job(job_id)["status"] == JobState.VALIDATING.value

        # Step 3: Processing (Parquet conversion)
        IngestionJobService.update_job(job_id, status=JobState.PROCESSING, progress_pct=50, message="Converting to DuckDB Parquet")
        assert IngestionJobService.get_job(job_id)["status"] == JobState.PROCESSING.value

        # Step 4: Profiling
        IngestionJobService.update_job(job_id, status=JobState.PROFILING, progress_pct=75, message="Profiling dataset columns")
        assert IngestionJobService.get_job(job_id)["status"] == JobState.PROFILING.value

        # Step 5: Semantic Model
        IngestionJobService.update_job(job_id, status=JobState.BUILDING_SEMANTIC_MODEL, progress_pct=90, message="Building semantic model")
        assert IngestionJobService.get_job(job_id)["status"] == JobState.BUILDING_SEMANTIC_MODEL.value

        # Step 6: Ready
        metrics = {
            "rows": 1500,
            "columns": 8,
            "domain": "Retail",
            "health_score": 98,
        }
        IngestionJobService.update_job(job_id, status=JobState.READY, progress_pct=100, message="Ready", metrics_update=metrics)
        final_job = IngestionJobService.get_job(job_id)
        assert final_job["status"] == JobState.READY.value
        assert final_job["progress_pct"] == 100
        assert final_job["metrics"]["rows"] == 1500
        assert final_job["metrics"]["domain"] == "Retail"
        assert final_job["completed_at"] is not None

    def test_job_cancellation(self):
        """Verify that jobs can be cleanly cancelled by the user."""
        ws_id = "ws-test-cancel"
        job_doc = IngestionJobService.create_job(
            workspace_id=ws_id,
            dataset_id="ds-cancel-1",
            filename="big_dataset.csv",
            file_size_bytes=50 * 1024 * 1024,
        )
        job_id = job_doc["job_id"]
        assert IngestionJobService.cancel_job(job_id) is True
        job = IngestionJobService.get_job(job_id)
        assert job["status"] == JobState.CANCELLED.value
        assert "cancelled by user" in job["message"].lower()

    def test_job_failure_with_error_diagnostics(self):
        """Verify that failure stores structured exception info and suggested fix."""
        ws_id = "ws-test-failure"
        job_doc = IngestionJobService.create_job(
            workspace_id=ws_id,
            dataset_id="ds-fail-1",
            filename="malformed.csv",
            file_size_bytes=100,
        )
        job_id = job_doc["job_id"]
        IngestionJobService.update_job(
            job_id,
            status=JobState.FAILED,
            stage_name="Parquet Conversion",
            message="Invalid CSV dialect delimiter",
            error_details={
                "failed_stage": "Parquet Conversion",
                "exception_class": "CsvImportError",
                "message": "Invalid CSV dialect delimiter",
                "suggested_fix": "Ensure CSV is comma or tab delimited with UTF-8 encoding."
            }
        )
        job = IngestionJobService.get_job(job_id)
        assert job["status"] == JobState.FAILED.value
        assert job["error"]["failed_stage"] == "Parquet Conversion"
        assert job["error"]["exception_class"] == "CsvImportError"
        assert "suggested_fix" in job["error"]


class TestAsyncUploadApiIntegration:
    """Integration tests for FastAPI async upload endpoints."""

    def test_async_file_upload_and_status_polling(self, client, auth_headers):
        """Test uploading a CSV asynchronously and checking job status."""
        csv_data = b"id,store_id,date,revenue,cost\n1,STORE-A,2025-01-01,1000.5,500.2\n2,STORE-B,2025-01-02,2500.0,1200.0\n3,STORE-C,2025-01-03,3200.75,1500.0\n"
        files = {"file": ("test_sales_async.csv", io.BytesIO(csv_data), "text/csv")}

        # POST /api/v1/upload/
        res = client.post("/api/v1/upload/", files=files, headers=auth_headers)
        assert res.status_code == 200, f"Upload failed: {res.text}"
        data = res.json()

        assert data["upload_status"] in ("PROCESSING", "COMPLETED")
        job_id = data.get("job_id")
        assert job_id is not None
        assert job_id.startswith("job-")

        # GET /api/v1/upload/status/{job_id}
        st_res = client.get(f"/api/v1/upload/status/{job_id}")
        assert st_res.status_code == 200
        st_data = st_res.json()
        assert st_data["job_id"] == job_id
        assert "status" in st_data
        assert "progress_pct" in st_data

    def test_synchronous_upload_flag(self, client, auth_headers):
        """Test that ?sync=true completes immediately before returning."""
        csv_data = b"customer_id,churn,monthly_spend\nCUST-001,False,89.5\nCUST-002,True,45.0\nCUST-003,False,120.0\n"
        files = {"file": ("test_sync_flag.csv", io.BytesIO(csv_data), "text/csv")}

        res = client.post("/api/v1/upload/?sync=true", files=files, headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["upload_status"] == "COMPLETED"
        assert data["rows"] == 3
        assert data["columns"] == 3
        assert "workspace_id" in data

    def test_cancel_job_endpoint(self, client, auth_headers):
        """Test POST /api/v1/upload/cancel/{job_id}."""
        ws_id = "ws-test-endpoint-cancel"
        job_doc = IngestionJobService.create_job(
            workspace_id=ws_id,
            dataset_id="ds-cancel-ep",
            filename="cancel_me.csv",
            file_size_bytes=5000,
        )
        job_id = job_doc["job_id"]
        res = client.post(f"/api/v1/upload/cancel/{job_id}", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] in ("success", "cancelled")
        assert data["job"]["status"] == JobState.CANCELLED.value
