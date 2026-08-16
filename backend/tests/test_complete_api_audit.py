import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def get_all_routes_deep(routes, prefix=''):
    extracted = []
    for r in routes:
        name = type(r).__name__
        if name == '_IncludedRouter':
            sub_prefix = prefix + getattr(getattr(r, 'include_context', None), 'prefix', '')
            if hasattr(r, 'original_router'):
                extracted.extend(get_all_routes_deep(r.original_router.routes, sub_prefix))
        elif hasattr(r, 'routes'):
            sub_prefix = prefix + getattr(r, 'prefix', '')
            extracted.extend(get_all_routes_deep(r.routes, sub_prefix))
        elif hasattr(r, 'methods') and hasattr(r, 'path'):
            methods = list(r.methods) if r.methods else ['GET']
            for m in methods:
                extracted.append((m, prefix + r.path))
    return extracted

def get_auth_headers():
    import uuid
    email = f"audit_{uuid.uuid4().hex[:6]}@decisionlens.ai"
    reg_payload = {
        "email": email,
        "password": "Password123!",
        "full_name": "Audit User",
        "organization": "Audit Corp",
        "role": "SUPER_ADMIN"
    }
    client.post("/api/v1/auth/register", json=reg_payload)
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    token = login_res.json().get("access_token")
    return {"Authorization": f"Bearer {token}"}

def test_programmatic_full_api_audit():
    all_endpoints = set(get_all_routes_deep(app.routes))
    real_endpoints = [
        (m, p) for m, p in all_endpoints
        if not p.startswith('/docs') and not p.startswith('/openapi') and not p.startswith('/redoc')
    ]

    total_discovered = len(real_endpoints)
    headers = get_auth_headers()

    failed_details = []

    for method, path in real_endpoints:
        test_path = path \
            .replace("{workspace_id}", "default") \
            .replace("{dataset_id}", "default") \
            .replace("{target_id}", "test_item") \
            .replace("{job_id}", "job_123") \
            .replace("{audience}", "executive") \
            .replace("{session_id}", "sess_123") \
            .replace("{tenant_id}", "tenant_123") \
            .replace("{provider}", "google") \
            .replace("{period}", "monthly")

        try:
            if method == "GET":
                res = client.get(test_path, headers=headers)
            elif method == "POST":
                res = client.post(test_path, json={"query": "test", "question": "test"}, headers=headers)
            elif method == "DELETE":
                res = client.delete(test_path, headers=headers)
            elif method == "HEAD":
                res = client.head(test_path, headers=headers)
            else:
                continue

            if res.status_code >= 500:
                failed_details.append(f"{method:<6} {test_path} -> HTTP {res.status_code} ({res.text[:150]})")
        except Exception as e:
            failed_details.append(f"{method:<6} {test_path} -> EXCEPTION: {e}")

    print(f"\n================ 500 INTERNAL SERVER ERRORS ({len(failed_details)}) ================")
    for f in failed_details:
        print(f)
    print("==========================================================================")

    assert len(failed_details) == 0, f"{len(failed_details)} endpoints failed with 500 or raised exceptions"
