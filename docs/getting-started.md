# Getting Started (Django + HTMX + DRF)

This guide helps you run the new server-rendered Django stack with DRF APIs and Celery workers.

## Prerequisites
- Docker + Kubernetes (or Docker Compose) with `kubectl`
- GNU Make
- Git
- Node.js + npm
- Optional: Redis + Postgres reachable (defaults provided in k8s manifests)
- Network devices reachable via SSH for automation testing

## Quick Start (local k8s)
1) Clone
```bash
git clone https://github.com/lammesen/networkautomation.git
cd networkautomation
```
2) Install deps (backend venv + tools)
```bash
make bootstrap
```
3) Build images and apply k8s manifests (backend as Django/Channels, worker as Celery)
```bash
make dev-up
```
4) Migrate DB and create superuser
```bash
make migrate
make seed-admin   # createsuperuser --no-input, ensure envs provide credentials
```
5) Port-forward backend (HTML + API + websockets)
```bash
make k8s-port-forward-backend   # exposes 8000 locally
```
6) Build static assets (Tailwind + collectstatic) if not already done:
```bash
make backend-build-static
```
7) Visit http://localhost:8000 for the HTMX UI; APIs under http://localhost:8000/api/v1/.

## Core Environment Variables
- `SECRET_KEY`, `ENCRYPTION_KEY` (required for crypto), `DEBUG=false`, `ALLOWED_HOSTS` (comma-separated)
- `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS` (comma-separated, required for prod)
- `DATABASE_URL` (Postgres recommended), `REDIS_URL`
- `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
- `DJANGO_SETTINGS_MODULE=webnet.settings`

## Running locally without k8s
```bash
make backend-install
. backend/venv/bin/activate
cd backend && python manage.py migrate
cd backend && python manage.py runserver 0.0.0.0:8000
# In another terminal:
cd backend && ../venv/bin/celery -A webnet.core.celery:celery_app worker -l info
```

## APIs (session or JWT)
- `POST /api/v1/auth/login` → {access, refresh}
- `POST /api/v1/auth/refresh`
- CRUD: users (with api-keys), customers (ranges/users), credentials, devices, jobs, compliance, config, topology
- Actions: commands/run, reachability/run, config/backup, deploy preview/commit, compliance/run
- WebSockets: `/ws/jobs/<id>/` for logs, `/ws/devices/<id>/ssh/` for interactive SSH

## HTMX UI
- Devices list: server-rendered with HTMX filters at `/devices/`
- Additional pages (jobs/logs/config/compliance/topology) follow the same pattern with HTMX partials.

## Build / CI
- Install Node deps once: `make backend-tailwind-install`
- Build CSS + collect static assets: `make backend-build-static`
- Run backend tests: `make backend-test`
- CI runners should execute: `make backend-tailwind-install backend-build-static backend-test`

## Notes
- React frontend is deprecated; Django/HTMX is the primary UI.
- Tailwind is built via npm; ensure `make backend-build-static` before packaging images.
- Secrets must not use defaults in production; set strong `SECRET_KEY` and `ENCRYPTION_KEY`.

The legacy React frontend is archived under `tech-dept/legacy-frontend`; Django/HTMX is the primary UI.

## Configuration

### Environment Variables

The Kubernetes manifests define runtime configuration directly inside `k8s/backend.yaml`. Edit the `env` block to customize items such as the FastAPI secret key, database connection, or CORS policy:

```yaml
      containers:
      - name: backend
        env:
        - name: SECRET_KEY
          value: "change-me"
        - name: DB_PATH
          value: "/app/data/netauto.sqlite"
        # Optional: switch to Postgres instead of SQLite
        # - name: DATABASE_URL
        #   value: "postgresql://netauto:netauto@postgres:5432/netauto"
        - name: CORS_ALLOWED_ORIGINS
          value: "http://localhost:8000"
        - name: CSRF_TRUSTED_ORIGINS
          value: "http://localhost:8000"
```

Apply changes with `make k8s-apply` (or `kubectl apply -f k8s/backend.yaml`). For one-off tweaks you can also run:

```bash
kubectl set env deployment/backend SECRET_KEY=$(openssl rand -hex 32) -n default
```

### Database Credentials

`k8s/postgres.yaml` contains the PostgreSQL deployment and environment variables. Update the `POSTGRES_PASSWORD` (and matching `DATABASE_URL` in `k8s/backend.yaml` if you switch away from SQLite), then redeploy:

```bash
kubectl apply -f k8s/postgres.yaml
kubectl rollout restart deployment/postgres
```

## Testing Without Real Devices

For testing without physical network devices, you can:

1. **Use a Network Simulator**
   - GNS3
   - EVE-NG
   - Cisco CML (VIRL)
   - Containerlab

2. **Mock Device for Testing**
   - The application will gracefully handle connection failures
   - Jobs will show status and error messages
   - Useful for testing the UI and workflow

3. **Use Docker Network Containers**
   ```bash
   docker run -d --name cisco-sim -p 2222:22 \
     networkprofile/cisco-sim
   ```
   Then add device with `mgmt_ip: host.docker.internal:2222`

## Common Issues

### "Cannot connect to database"

```bash
# Ensure the pod is running
make k8s-status

# Inspect logs
kubectl logs deployment/postgres -n default

# Restart the deployment if needed
kubectl rollout restart deployment/postgres -n default
```

### "Celery worker not processing jobs"

```bash
# Check worker logs
kubectl logs deployment/worker -n default

# Restart worker deployment
kubectl rollout restart deployment/worker -n default
```

### "Frontend won't connect to API"

Check CORS settings in `backend/app/core/config.py`:
```python
cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
```

### Port Already in Use

When port-forwarding, change the local bind port:

```bash
# Backend API on localhost:9000 instead of 8000
kubectl port-forward svc/backend 9000:8000 -n default

# Frontend on localhost:3333 instead of 3000
kubectl port-forward svc/frontend 3333:3000 -n default
```

## Stopping the Application

```bash
make dev-down
```

To also remove persistent volumes (SQLite + Postgres data):
```bash
kubectl delete pvc sqlite-pvc postgres-pvc --ignore-not-found=true -n default
```

## Updating the Application

```bash
git pull
make dev-down
make docker-build
make k8s-redeploy
make migrate
```

## Development Mode

### Backend Development

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# Run migrations
alembic upgrade head

# Start FastAPI with auto-reload
uvicorn app.main:app --reload
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at http://localhost:5173 with hot reload.

## Production Deployment

### Security Checklist

- [ ] Change all default passwords
- [ ] Generate strong SECRET_KEY
- [ ] Use HTTPS (configure reverse proxy)
- [ ] Restrict CORS origins
- [ ] Use environment-specific credentials
- [ ] Enable PostgreSQL SSL
- [ ] Implement rate limiting
- [ ] Setup firewall rules
- [ ] Regular backups
- [ ] Monitor logs

### Recommended Architecture

```
Internet
    │
    ▼
[NGINX/Traefik]  ← SSL termination
    │
    ├─▶ [Frontend]  (static files)
    │
    └─▶ [Backend API]
          │
          ├─▶ [PostgreSQL]  (primary DB)
          ├─▶ [Redis]       (cache/queue)
          └─▶ [Celery Workers] × N
```

## Getting Help

- **Documentation**: See `docs/` directory
- **API Reference**: http://localhost:8000/docs
- **Issues**: https://github.com/lammesen/networkautomation/issues
- **Operations Guide**: `docs/operations.md`
- **Architecture**: `docs/architecture.md`

## What's Next?

1. **Add Devices**: Start adding your network devices
2. **Run Commands**: Test command execution
3. **Setup Backup Schedule**: Use Celery Beat for scheduled backups
4. **Create Compliance Policies**: Define compliance checks
5. **Customize**: Extend with custom tasks and integrations

## Example Workflow

Here's a typical workflow:

1. **Morning**: Run compliance checks
   ```bash
   curl -X POST .../compliance/run -d '{"policy_id": 1}'
   ```

2. **Backup configs** before changes
   ```bash
   curl -X POST .../config/backup -d '{"targets": {}}'
   ```

3. **Deploy change** with preview
   ```bash
   # Preview
   curl -X POST .../config/deploy/preview -d '{...}'
   
   # Review diff
   curl .../jobs/{job_id}/results
   
   # Commit if OK
   curl -X POST .../config/deploy/commit -d '{...}'
   ```

4. **Verify** with commands
   ```bash
   curl -X POST .../commands/run -d '{...}'
   ```

5. **Evening**: Review job history and compliance results

Enjoy automating your network! 🚀
