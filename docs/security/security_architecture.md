# DecisionLens Security Architecture & Compliance

## 1. Threat Model & Defense-in-Depth
DecisionLens enforces enterprise defense-in-depth across the application lifecycle:

`
[ Edge Network ]
       |
[ Security Headers: HSTS, CSP, X-Frame DENY, X-Content-Type ]
       |
[ Sliding Window Rate Limiter ]
       |
[ Next.js Edge Middleware Session Interceptor ]
       |
[ FastAPI JWT & RBAC Authorization Layer ]
       |
[ In-Process Vectorized OLAP & Polyglot Data Store ]
`

## 2. Authentication & Session Management
- **JWT Tokens**: Signed with HS256 using constant-time hmac.compare_digest to eliminate timing attacks.
- **Two-Factor Authentication (2FA)**: Time-based OTP verification via authenticated mailer.
- **Edge Middleware**: Next.js server-side route interception blocks unauthenticated access before HTML dispatch and preserves deep links (?redirect=...).

## 3. Role-Based Access Control (RBAC) Matrix

| Endpoint Group | ANONYMOUS | VIEWER | ANALYST | ORG_ADMIN | SUPER_ADMIN |
| :--- | :---: | :---: | :---: | :---: | :---: |
| /auth/login, /auth/register | Allow | Allow | Allow | Allow | Allow |
| /dynamic-dashboard, /reports | Deny (401) | Read-Only | Read-Only | Manage | Manage |
| /analytics/universal | Deny (401) | Read-Only | Execute | Execute | Execute |
| /workspace/upload-* | Deny (401) | Deny (403) | Upload | Upload | Upload |
| /cybersecurity/dashboard | Deny (401) | Deny (403) | Deny (403) | Allow | Allow |
| /sso/idp/config | Deny (401) | Deny (403) | Deny (403) | Deny (403) | Allow |
| /workspace/{id} (DELETE) | Deny (401) | Deny (403) | Deny (403) | Org Scope | Global |

## 4. Input Validation & File Upload Security
- Multi-format validator enforcing magic byte inspection (PAR1 for Apache Parquet, PK zip signature).
- Path traversal sanitization preventing arbitrary file writes outside uploads/ directory.
