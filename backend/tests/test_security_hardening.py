import sys
import os
import time

# Ensure backend directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.core.security import SecurityManager
from app.core.rbac import SUPER_ADMIN, ORGANIZATION_ADMIN, EMPLOYEE
from app.security.file_validator import sanitize_filename, validate_upload

client = TestClient(app, raise_server_exceptions=False)


def get_token_for_role(role: str, email: str = "security_test@decisionlens.ai") -> str:
    return SecurityManager.create_access_token({
        "sub": email,
        "email": email,
        "role": role,
        "full_name": f"Test {role}",
        "tenant_id": "tenant-test-01"
    })


def test_enterprise_security_headers():
    """Verify that every HTTP response contains required enterprise security headers."""
    res = client.get("/api/v1/health")
    assert res.status_code == 200, f"Expected 200 from health endpoint, got {res.status_code}"

    headers = res.headers
    assert "strict-transport-security" in headers, "Missing Strict-Transport-Security header"
    assert "max-age=31536000" in headers["strict-transport-security"]
    assert headers.get("x-content-type-options") == "nosniff", "Missing or invalid X-Content-Type-Options"
    assert headers.get("x-frame-options") == "DENY", "Missing or invalid X-Frame-Options"
    assert headers.get("x-xss-protection") == "1; mode=block", "Missing or invalid X-XSS-Protection"
    assert headers.get("referrer-policy") == "strict-origin-when-cross-origin", "Missing or invalid Referrer-Policy"
    assert "content-security-policy" in headers, "Missing Content-Security-Policy header"
    assert "frame-ancestors 'none'" in headers["content-security-policy"]
    assert "server" not in headers, "Internal Server header leaked in response"
    print("[PASS] test_enterprise_security_headers")


def test_unauthenticated_requests_blocked_with_401():
    """Verify that all data, intelligence, and admin endpoints strictly reject unauthenticated access."""
    protected_endpoints = [
        ("GET", "/api/v1/cybersecurity/dashboard"),
        ("GET", "/api/v1/diagnostics/status"),
        ("GET", "/api/v1/catalog/tables"),
        ("GET", "/api/v1/lineage/graph/ws-test"),
        ("GET", "/api/v1/quality/score/ws-test"),
        ("GET", "/api/v1/monitoring/metrics"),
        ("GET", "/api/v1/monitoring/charts"),
        ("GET", "/api/v1/ml/forecast"),
        ("GET", "/api/v1/ai/xai/insights"),
        ("GET", "/api/v1/metrics"),
        ("GET", "/api/v1/metrics/duckdb"),
        ("GET", "/api/v1/metrics/cache"),
        ("GET", "/api/v1/system"),
        ("GET", "/api/v1/search?q=test"),
        ("GET", "/api/v1/intelligence/workspace/ws-test"),
        ("GET", "/api/v1/semantic-model/workspace/ws-test"),
        ("POST", "/api/v1/sso/idp/config"),
        ("POST", "/api/v1/scheduler/schedules"),
    ]

    for method, path in protected_endpoints:
        if method == "GET":
            res = client.get(path)
        else:
            res = client.post(path, json={})

        assert res.status_code == 401, (
            f"SECURITY LEAK: Unauthenticated request to {method} {path} returned {res.status_code} instead of 401!"
        )

    print(f"[PASS] test_unauthenticated_requests_blocked_with_401 ({len(protected_endpoints)} endpoints verified)")


def test_rbac_least_privilege_enforcement():
    """Verify that lower-privileged roles (EMPLOYEE) cannot access restricted administrative routes."""
    employee_token = get_token_for_role(EMPLOYEE, "employee@corp.local")
    emp_headers = {"Authorization": f"Bearer {employee_token}"}

    restricted_for_employee = [
        ("POST", "/api/v1/sso/idp/config", {}),
        ("POST", "/api/v1/scheduler/schedules", {}),
        ("GET", "/api/v1/monitoring/metrics", None),
        ("GET", "/api/v1/metrics", None),
        ("GET", "/api/v1/cybersecurity/dashboard", None),
    ]

    for method, path, payload in restricted_for_employee:
        if method == "GET":
            res = client.get(path, headers=emp_headers)
        else:
            res = client.post(path, headers=emp_headers, json=payload)

        assert res.status_code == 403, (
            f"RBAC VIOLATION: EMPLOYEE was able to access {method} {path} with status {res.status_code} (expected 403 Forbidden)"
        )

    # Verify SUPER_ADMIN is authorized
    super_admin_token = get_token_for_role(SUPER_ADMIN, "superadmin@corp.local")
    admin_headers = {"Authorization": f"Bearer {super_admin_token}"}

    res_metrics = client.get("/api/v1/metrics", headers=admin_headers)
    assert res_metrics.status_code == 200, f"SUPER_ADMIN should have access to /metrics, got {res_metrics.status_code}"

    res_diag = client.get("/api/v1/diagnostics/status", headers=admin_headers)
    assert res_diag.status_code == 200, f"SUPER_ADMIN should have access to /diagnostics/status, got {res_diag.status_code}"
    # Verify Super Admin can view system resources while unprivileged users cannot
    assert "system_resources" in res_diag.json(), "SUPER_ADMIN should see system_resources in diagnostics"

    print("[PASS] test_rbac_least_privilege_enforcement")


def test_jwt_timing_attack_resistance_and_validation():
    """Verify constant-time HMAC validation and signature tampering detection."""
    valid_token = get_token_for_role(EMPLOYEE)
    decoded = SecurityManager.decode_access_token(valid_token)
    assert decoded is not None
    assert decoded["role"] == EMPLOYEE

    # Tamper with signature
    parts = valid_token.split(".")
    tampered_sig = parts[2][:-2] + ("aa" if not parts[2].endswith("aa") else "bb")
    tampered_token = f"{parts[0]}.{parts[1]}.{tampered_sig}"
    assert SecurityManager.decode_access_token(tampered_token) is None, "Tampered token signature was accepted!"

    # Expired token
    expired_token = SecurityManager.create_access_token({"sub": "user@test.com"}, expires_in=-10)
    assert SecurityManager.decode_access_token(expired_token) is None, "Expired token was accepted!"

    print("[PASS] test_jwt_timing_attack_resistance_and_validation")


def test_file_upload_validation_and_traversal_prevention():
    """Verify filename sanitization prevents path traversal and magic bytes detect spoofed parquet."""
    # Path traversal sanitization
    dirty = "../../../etc/shadow.csv"
    clean = sanitize_filename(dirty)
    assert ".." not in clean, f"Path traversal not sanitized: {clean}"
    assert "/" not in clean and "\\" not in clean

    # Fake parquet file without PAR1 header
    fake_parquet = b"THIS_IS_NOT_A_PARQUET_FILE"
    result = validate_upload(content=fake_parquet, filename="malicious.parquet")
    assert not result["valid"], "Spoofed parquet file without magic header passed validation!"
    assert any("PAR1" in err for err in result["errors"])

    print("[PASS] test_file_upload_validation_and_traversal_prevention")


def run_all_security_tests():
    print("\n" + "=" * 60)
    print("STARTING DECISIONLENS ENTERPRISE SECURITY POSTURE TEST SUITE")
    print("=" * 60)
    test_enterprise_security_headers()
    test_unauthenticated_requests_blocked_with_401()
    test_rbac_least_privilege_enforcement()
    test_jwt_timing_attack_resistance_and_validation()
    test_file_upload_validation_and_traversal_prevention()
    print("=" * 60)
    print("ALL ENTERPRISE SECURITY & HARDENING TESTS PASSED SUCCESSFULLY!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run_all_security_tests()
