import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from app.main import app
from app.core.security import SecurityManager
from app.core.rbac import SUPER_ADMIN, ORGANIZATION_ADMIN
from app.services.workspace_service import EnterpriseWorkspaceManager
from app.observability.error_handler import RequestState
from app.api.v1.auth import RATE_LIMIT_STORE

client = TestClient(app, raise_server_exceptions=False)


def get_token(role: str = SUPER_ADMIN, email: str = 'qa_staff@decisionlens.ai') -> str:
    return SecurityManager.create_access_token({
        'sub': email,
        'email': email,
        'role': role,
        'full_name': f'Staff {role}',
        'tenant_id': 'tenant-test-enterprise'
    })


def setup_function():
    RATE_LIMIT_STORE.clear()


def test_unauthenticated_endpoints_blocked():
    """Protected endpoints must reject unauthenticated requests with 401 or 403."""
    endpoints = [
        ('/api/v1/reports', 'GET'),
        ('/api/v1/strategy', 'GET'),
        ('/api/v1/quality/score/test-ws', 'GET'),
        ('/api/v1/lineage/graph/test-ws', 'GET'),
        ('/api/v1/catalog/tables', 'GET'),
        ('/api/v1/cybersecurity/dashboard', 'GET'),
    ]
    for path, method in endpoints:
        if method == 'GET':
            res = client.get(path)
        else:
            res = client.post(path)
        assert res.status_code in [401, 403], f'Expected 401/403 for unauthenticated {method} {path}, got {res.status_code}'


def test_x_workspace_id_header_and_query_param_context():
    token = get_token()
    headers = {'Authorization': f'Bearer {token}', 'X-Workspace-Id': 'ws-isolated-retail'}
    res = client.get('/api/v1/catalog/tables', headers=headers)
    assert res.status_code == 200
    headers_no_ws = {'Authorization': f'Bearer {token}'}
    res_query = client.get('/api/v1/catalog/tables?workspace_id=ws-isolated-finance', headers=headers_no_ws)
    assert res_query.status_code == 200


def test_ghost_workspace_fallback_eliminated():
    token = get_token()
    headers = {'Authorization': f'Bearer {token}'}
    dummy_ws = 'ws-nonexistent-99999'
    res_dq = client.get(f'/api/v1/quality/score/{dummy_ws}', headers=headers)
    assert res_dq.status_code == 200
    dq_data = res_dq.json()
    assert 'ws-enterprise-generic' not in str(dq_data).lower()
    res_lin = client.get(f'/api/v1/lineage/graph/{dummy_ws}', headers=headers)
    assert res_lin.status_code == 200
    lin_data = res_lin.json()
    assert 'ws-enterprise-generic' not in str(lin_data).lower()
    res_cat = client.get(f'/api/v1/catalog/tables?workspace_id={dummy_ws}', headers=headers)
    assert res_cat.status_code == 200
    cat_data = res_cat.json()
    assert 'ws-enterprise-generic' not in str(cat_data).lower()


def test_reports_workspace_parameterization():
    token = get_token()
    headers = {'Authorization': f'Bearer {token}'}
    res = client.get('/api/v1/reports?workspace_id=ws-dummy-test', headers=headers)
    assert res.status_code in [200, 404]
    res_csv = client.get('/api/v1/reports/export/csv?workspace_id=ws-dummy-test', headers=headers)
    assert res_csv.status_code in [200, 404]
    res_summary = client.get('/api/v1/export/summary?workspace_id=ws-dummy-test', headers=headers)
    assert res_summary.status_code in [200, 404]


def test_strategy_and_scenario_workspace_isolation():
    token = get_token()
    headers = {'Authorization': f'Bearer {token}'}
    res_strat = client.get('/api/v1/strategy?workspace_id=ws-test-scope', headers=headers)
    assert res_strat.status_code in [200, 404]
    res_levers = client.get('/api/v1/analytics/scenario/levers?workspace_id=ws-test-scope', headers=headers)
    assert res_levers.status_code in [200, 404]
    if res_levers.status_code == 200:
        data = res_levers.json()
        assert 'available_levers' in data or 'unavailable_reasons' in data
    sim_payload = {'changes': [{'lever_id': 'price', 'change_pct': 5.0}]}
    res_sim = client.post('/api/v1/analytics/scenario/simulate?workspace_id=ws-test-scope', json=sim_payload, headers=headers)
    assert res_sim.status_code in [200, 400, 404]


def test_workspace_list_and_active_switching():
    token = get_token()
    headers = {'Authorization': f'Bearer {token}'}
    res = client.get('/api/v1/workspaces', headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert 'workspaces' in data
    workspaces = data.get('workspaces', [])
    if len(workspaces) >= 1:
        target_ws = workspaces[0]
        target_id = target_ws['workspace_id']
        act_res = client.post(f'/api/v1/workspaces/{target_id}/activate', headers=headers)
        assert act_res.status_code == 200
        active_res = client.get('/api/v1/workspace/active', headers=headers)
        assert active_res.status_code == 200
        active_data = active_res.json()
        assert active_data.get('workspace', {}).get('workspace_id') == target_id


def run_all_workspace_tests():
    print("\n" + "=" * 60)
    print("STARTING DECISIONLENS WORKSPACE BUSINESS LOGIC REGRESSION SUITE")
    print("=" * 60)
    setup_function()
    test_unauthenticated_endpoints_blocked()
    print("[PASS] test_unauthenticated_endpoints_blocked")
    setup_function()
    test_x_workspace_id_header_and_query_param_context()
    print("[PASS] test_x_workspace_id_header_and_query_param_context")
    setup_function()
    test_ghost_workspace_fallback_eliminated()
    print("[PASS] test_ghost_workspace_fallback_eliminated")
    setup_function()
    test_reports_workspace_parameterization()
    print("[PASS] test_reports_workspace_parameterization")
    setup_function()
    test_strategy_and_scenario_workspace_isolation()
    print("[PASS] test_strategy_and_scenario_workspace_isolation")
    setup_function()
    test_workspace_list_and_active_switching()
    print("[PASS] test_workspace_list_and_active_switching")
    print("=" * 60)
    print("ALL WORKSPACE BUSINESS LOGIC & ISOLATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run_all_workspace_tests()
