const axios = require('axios');
const fs = require('fs');
const path = require('path');

const API_BASE = 'http://127.0.0.1:8000/api/v1';
const OUT_DIR = path.join(__dirname, 'audit_results');

const TEST_TOKEN = 'eyJhbGciOiAiSFMyNTYiLCAidHlwIjogIkpXVCJ9.eyJzdWIiOiAiZm9ydHVuZTUwMF9jZm9AZW50ZXJwcmlzZS5jb20iLCAicm9sZSI6ICJPUkdBTklaQVRJT05fQURNSU4iLCAiZnVsbF9uYW1lIjogIlNhcmFoIEplbmtpbnMgQ0ZPIiwgInRlbmFudF9pZCI6ICJ0ZW5hbnQtZm9ydHVuZTUwMF9jZm8iLCAiZXhwIjogMTc4ODQyMjc1MX0.0eGCc67u1DqbY53fviTBo8Y4ou5BdP5FClT2hJpOIec';

async function testSecurity() {
  console.log('\n🛡️ Starting API Security, IDOR, Injection & Headers Audit...');
  const results = {
    headers: {},
    idor: {},
    sql_injection: {},
    auth_bypass: {},
    cors: {},
    sensitive_data_exposure: {}
  };

  // 1. SECURITY HEADERS AUDIT
  console.log('1. Auditing Security Headers on API and Health endpoints...');
  try {
    const healthResp = await axios.get(`${API_BASE}/health`);
    const h = healthResp.headers;
    results.headers = {
      hsts: h['strict-transport-security'] || 'MISSING',
      x_frame_options: h['x-frame-options'] || 'MISSING',
      x_content_type_options: h['x-content-type-options'] || 'MISSING',
      csp: h['content-security-policy'] || 'MISSING',
      referrer_policy: h['referrer-policy'] || 'MISSING'
    };
  } catch (err) {
    results.headers.error = err.message;
  }

  // 2. CORS AUDIT
  console.log('2. Auditing CORS policy for untrusted origins...');
  try {
    const corsResp = await axios.options(`${API_BASE}/workspaces`, {
      headers: {
        'Origin': 'https://evil-hacker-domain.com',
        'Access-Control-Request-Method': 'GET'
      }
    });
    const acao = corsResp.headers['access-control-allow-origin'];
    results.cors.untrusted_origin_allowed = acao === '*' || acao === 'https://evil-hacker-domain.com';
    results.cors.allow_origin_header = acao || 'Not Returned';
  } catch (err) {
    results.cors.preflight_status = err.response ? err.response.status : err.message;
  }

  // 3. AUTH BYPASS / UNPROTECTED SENSITIVE ENDPOINTS
  console.log('3. Checking Protected Endpoints without Bearer Token...');
  const sensitiveEndpoints = [
    { url: `${API_BASE}/cybersecurity/audit-logs`, method: 'get' },
    { url: `${API_BASE}/audit/events`, method: 'get' },
    { url: `${API_BASE}/strategy/recommendations`, method: 'get' },
    { url: `${API_BASE}/business-memory`, method: 'get' },
    { url: `${API_BASE}/diagnostics/system`, method: 'get' }
  ];

  results.auth_bypass.endpoints = {};
  for (const ep of sensitiveEndpoints) {
    try {
      const resp = await axios[ep.method](ep.url, { timeout: 3000 });
      results.auth_bypass.endpoints[ep.url] = {
        status: resp.status,
        vulnerable: resp.status === 200,
        message: 'Endpoint accessed WITHOUT authorization header!'
      };
      if (resp.status === 200) {
        console.log(`  🚨 SECURITY ISSUE: Unauthenticated access permitted to ${ep.url}!`);
      }
    } catch (err) {
      results.auth_bypass.endpoints[ep.url] = {
        status: err.response ? err.response.status : 'ERR',
        vulnerable: false
      };
    }
  }

  // 4. SQL / DUCKDB INJECTION AUDIT
  console.log('4. Testing SQL / DuckDB Injection in Parameters...');
  const sqliPayloads = [
    "' OR '1'='1",
    "'; DROP TABLE users; --",
    "1 UNION SELECT null, email, hashed_password FROM users --"
  ];

  results.sql_injection.tests = [];
  for (const payload of sqliPayloads) {
    try {
      const resp = await axios.get(`${API_BASE}/workspaces/${encodeURIComponent(payload)}`, {
        headers: { 'Authorization': `Bearer ${TEST_TOKEN}` },
        timeout: 3000
      });
      results.sql_injection.tests.push({ payload, status: resp.status, response: resp.data });
    } catch (err) {
      const errDetail = err.response ? err.response.data : err.message;
      const leaksSqlTrace = typeof errDetail === 'string' && (errDetail.includes('syntax error') || errDetail.includes('Parser Error') || errDetail.includes('duckdb'));
      results.sql_injection.tests.push({
        payload,
        status: err.response ? err.response.status : 'ERR',
        leaksSqlTrace,
        detail: typeof errDetail === 'object' ? JSON.stringify(errDetail).slice(0, 100) : String(errDetail).slice(0, 100)
      });
    }
  }

  // 5. IDOR AUDIT (Insecure Direct Object Reference)
  console.log('5. Testing Insecure Direct Object Reference (IDOR)...');
  try {
    // Attempt to access another workspace or arbitrary UUID
    const idorResp = await axios.get(`${API_BASE}/workspaces/ws-victim-organization-999`, {
      headers: { 'Authorization': `Bearer ${TEST_TOKEN}` }
    });
    results.idor.unauthorized_access_granted = true;
    results.idor.status = idorResp.status;
  } catch (err) {
    results.idor.status = err.response ? err.response.status : 'ERR';
    results.idor.blocked = err.response && (err.response.status === 403 || err.response.status === 404);
  }

  const reportFile = path.join(OUT_DIR, 'security_audit_summary.json');
  fs.writeFileSync(reportFile, JSON.stringify(results, null, 2));
  console.log(`\n🎉 Security audit complete! Saved results to ${reportFile}`);
}

testSecurity().catch(err => {
  console.error('Fatal Security Audit Error:', err);
  process.exit(1);
});
