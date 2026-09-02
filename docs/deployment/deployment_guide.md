# DecisionLens Deployment & Operations Guide

## 1. Containerized Deployment via Docker Compose

DecisionLens includes a complete multi-container Docker Compose configuration:

```bash
# Build and launch all services
docker-compose up -d --build
```

### Services Deployed
- **frontend**: Next.js 16 standalone server on port `3000`.
- **backend**: FastAPI Uvicorn server on port `8000`.
- **mongo**: MongoDB database with persistent volume on port `27017`.
- **redis**: In-memory Redis cache on port `6379`.

---

## 2. Production Environment Configuration

Create a `.env` file from `.env.example` in production:
```bash
cp .env.example .env
```

Ensure the following critical variables are generated with cryptographically secure values (>= 64 chars):
```ini
SECRET_KEY=generate-with-openssl-rand-hex-32
JWT_SECRET=generate-with-openssl-rand-hex-32
PASSWORD_SALT=generate-with-openssl-rand-hex-32
OTP_SECRET=generate-with-openssl-rand-hex-32
```

---

## 3. Health Checks & Verification
- Backend Health Check: `GET https://your-domain.com/api/v1/health`
- Diagnostics Telemetry: `GET https://your-domain.com/api/v1/diagnostics/status`
