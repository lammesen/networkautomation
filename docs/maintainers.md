 # Maintainers Guide (SRE/Platform)
 
 Guidance for deploying, operating, and upgrading the Network Automation platform.
 
 See also: [Deployment](./deployment.md), [Operations](./operations.md), [Security](./security.md), [Performance](./performance.md), and [Troubleshooting](./troubleshooting.md).
 
 ## Components
 - Backend (Django ASGI via Daphne)
 - Worker (Celery) and Beat (scheduling)
 - PostgreSQL (DB)
 - Redis (broker + channel layer)
 - Static assets (Tailwind + React Islands bundle served by Django)
 
 ## Deployment Options
 
 ### Docker Compose (local/dev)
 File: [/docker-compose.yml](../docker-compose.yml)
 
 ```bash
 docker compose up -d --build
 docker compose logs -f backend worker beat
 ```
 
 Environment is provided via `backend/.env` and compose service `environment` block.
 
 ### Kubernetes (recommended)
 Manifests: [/k8s](../k8s)
 
 ```bash
 make dev-up           # docker build + kubectl apply (see Makefile)
 make k8s-status
 ```
 
 Secrets to set (examples in `k8s/secrets.yaml`):
 - `SECRET_KEY` (Django)
 - `ENCRYPTION_KEY` (Fernet for device secrets)
 - `DATABASE_URL`, `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
 - CORS/CSRF origins as required
 
 ## Post‑Deploy Checklist
 - Migrate database: `make migrate`
 - Create admin user: `make seed-admin`
 - Build static (if not prebuilt in image): `make backend-build-static`
 - Port‑forward or expose ingress as needed
 
 ## Scaling & Performance
 - Backend replicas: scale `Deployment/backend` for read traffic and WebSockets
 - Workers: scale `Deployment/worker`; adjust Celery concurrency
 - Redis: ensure adequate memory; consider persistence/HA
 - Database: provision CPU/IO; create indexes as needed; monitor connections
 
 ## Observability
 - Logs: `kubectl logs -f deployment/backend|worker|beat`
 - Metrics: Prometheus client is available; integrate with your scraper
 - Job health: monitor job throughput, failure rate, and queue latency
 
 ## Backups & Restore
 - PostgreSQL: use `pg_dump`/`psql` (see [Operations](./operations.md))
 - Config snapshots: export via API or DB
 - Secrets: back up Kubernetes secrets or your secret manager entries
 
 ## Security
 - Never run with default `SECRET_KEY` or weak `ENCRYPTION_KEY`
 - Restrict CORS/CSRF origins in production
 - Rotate device credentials and admin passwords regularly
 - Enable HTTPS at ingress and restrict management network access
 - CI runs CodeQL and secret scanning; fix findings before release
 
 ## Upgrade Procedure
 1. Announce maintenance window (if needed)
 2. `git pull` and review release notes
 3. Rebuild images: `make docker-build`
 4. Redeploy: `make k8s-redeploy`
 5. Run migrations: `make migrate`
 6. Verify:
    - App reachable; jobs run end‑to‑end
    - WebSockets (job logs, SSH) are functional
    - No DB migration issues or background queue backlog
 
 Rollback: keep previous image tags available; `kubectl rollout undo deployment/backend deployment/worker`.
 
 ## Runbooks
 
 - Worker stuck / not processing:
   - Check Redis connectivity and broker env
   - Restart worker; inspect logs for serialization errors
 
 - WebSockets failing:
   - Ensure ASGI/Daphne is serving; verify Channels Redis settings
   - Check ingress/web proxy supports WebSockets
 
 - Migrations failed:
   - Run with verbose logs; if needed, create a new migration to resolve conflicts
 
 ## Compliance & Audit
 - Keep audit of config deploys and compliance runs
 - Review job logs regularly
 - Limit operator privileges via RBAC roles
 
 ## References
 - Makefile workflows: [/Makefile](../Makefile)
 - Kubernetes manifests: [/k8s](../k8s)
 - Developer Guide: [docs/developer-guide.md](./developer-guide.md)
 