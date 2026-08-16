# DecisionLens Production Deployment Checklist

## Pre-Deployment

- [ ] Set all required environment variables in `.env` or deployment secrets
- [ ] Generate strong `SECRET_KEY`, `JWT_SECRET`, `PASSWORD_SALT`, `OTP_SECRET` (64+ chars each)
- [ ] Set `SUPER_ADMIN_EMAIL` and `SUPER_ADMIN_PASSWORD` to production values
- [ ] Configure `MONGODB_URL`, `DATABASE_URL`, `REDIS_URL`
- [ ] Set `GROQ_API_KEY` if using LLM features
- [ ] Set `RESEND_API_KEY` and `EMAIL_FROM` for email notifications
- [ ] Set `FRONTEND_URL` to production domain
- [ ] Update `CORS_ORIGINS` to production frontend URLs only
- [ ] Set `DEBUG=false` and `ENV=production`
- [ ] Set `IMPORT_ROOT` and `BROWSE_ROOT` to secure directories

## Docker Deployment

- [ ] Build images: `docker-compose build`
- [ ] Start services: `docker-compose up -d`
- [ ] Verify health: `curl http://localhost:8000/health`
- [ ] Verify status: `curl http://localhost:8000/api/v1/status`
- [ ] Check logs: `docker logs decisionlens_backend`
- [ ] Verify MongoDB: `docker logs decisionlens_mongodb`
- [ ] Verify Redis: `docker logs decisionlens_redis`
- [ ] Verify PostgreSQL: `docker logs decisionlens_postgres`

## Security

- [ ] Rotate all default credentials
- [ ] Enable HTTPS/TLS termination (reverse proxy)
- [ ] Configure firewall rules (only ports 80, 443 exposed)
- [ ] Enable MongoDB authentication
- [ ] Enable PostgreSQL authentication
- [ ] Review CORS origins - restrict to production domains
- [ ] Set `allow_credentials=True` only for trusted origins
- [ ] Enable rate limiting on public endpoints
- [ ] Disable `/upload/local-path` and `/upload/local-browse` in production or restrict to internal networks
- [ ] Enable audit logging
- [ ] Review `SECURITY.md` and apply additional hardening

## Performance

- [ ] Set `WORKERS=4` (or match CPU cores)
- [ ] Configure DuckDB memory limit: `SET memory_limit TO '4GB'`
- [ ] Enable Redis cache (`REDIS_URL` configured)
- [ ] Set appropriate cache TTLs:
  - Dashboard: 60s
  - Analytics: 300s
  - Forecast: 600s
- [ ] Monitor `/api/v1/metrics` for latency
- [ ] Profile slow endpoints using `/api/v1/metrics`

## Monitoring

- [ ] Configure log aggregation (ELK, Datadog, etc.)
- [ ] Set up alerts for:
  - Health endpoint failures
  - Error rate > 1%
  - Average latency > 5s
  - Memory usage > 80%
  - Disk usage > 85%
- [ ] Monitor circuit breaker states
- [ ] Monitor cache hit rates
- [ ] Set up uptime monitoring (UptimeRobot, Pingdom, etc.)

## Data

- [ ] Backup MongoDB: `mongodump`
- [ ] Backup PostgreSQL: `pg_dump`
- [ ] Backup storage directory: `storage/`
- [ ] Set up automated backups (daily)
- [ ] Verify backup restoration process

## Scaling

- [ ] Horizontal scaling: increase `WORKERS` or add more backend instances
- [ ] Redis cluster for cache scaling
- [ ] MongoDB replica set for high availability
- [ ] Load balancer configuration (nginx, Traefik, etc.)

## Maintenance

- [ ] Schedule periodic log rotation
- [ ] Schedule cache cleanup
- [ ] Monitor disk usage
- [ ] Review and rotate secrets quarterly
- [ ] Update dependencies monthly
