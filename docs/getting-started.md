# Getting Started (Django + HTMX + DRF)

This guide helps you run the Django server‑rendered stack with DRF APIs, Channels (WebSockets), and Celery workers.

## Prerequisites
- Docker + Kubernetes (or Docker Compose) with `kubectl`
- GNU Make
- Git
- Node.js + npm
- Optional: Redis + Postgres reachable (defaults provided in k8s and Compose)
- Network devices reachable via SSH for automation testing

## Quick Start (local Kubernetes)
1) Clone
```bash
git clone https://github.com/lammesen/networkautomation.git
cd networkautomation
```
2) Install deps (backend venv + npm)
```bash
make bootstrap
```
3) Build images and apply manifests (Django/Channels + Celery + infra)
```bash
make dev-up
```
4) Migrate DB and create superuser
```bash
make migrate
make seed-admin   # createsuperuser --no-input (ensure envs provide credentials)
```
5) Port-forward backend (HTML + API + WebSockets)
```bash
make k8s-port-forward-backend   # exposes 8000 locally
```
6) Build static assets (Tailwind + Islands + collectstatic) if not done by CI
```bash
make backend-build-static
```
7) Open http://localhost:8000 for the UI; APIs under http://localhost:8000/api/v1/.

## Quick Start (Docker Compose)
```bash
docker compose up -d --build
make migrate
make seed-admin
open http://localhost:8000
```

## Core Environment Variables
- `SECRET_KEY`, `ENCRYPTION_KEY` (required), `DEBUG=false`, `ALLOWED_HOSTS`
- `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS` (comma‑separated; set in prod)
- `DATABASE_URL` (Postgres recommended), `REDIS_URL`
- `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
- `DJANGO_SETTINGS_MODULE=webnet.settings`

## Running locally without k8s
```bash
make backend-install
cd backend && ../venv/bin/python manage.py migrate
cd backend && ../venv/bin/python manage.py runserver 0.0.0.0:8000
# In another terminal:
cd backend && ../venv/bin/celery -A webnet.core.celery:celery_app worker -l info
```

## APIs & WebSockets
- Browseable API: `/api/v1/`
- Auth: session or JWT (`/api/v1/auth/login`, `/api/v1/auth/refresh`)
- WebSockets: `/ws/jobs/<id>/` (logs), `/ws/devices/<id>/ssh/` (terminal)

## UI (HTMX)
- Devices at `/devices/` with HTMX filters/partials
- Jobs, Config, Compliance, Topology follow similar patterns

## Build / CI
- Install Node deps: `make backend-npm-install`
- Build assets and collectstatic: `make backend-build-static`
- Tests: `make backend-test`
- CI should run: `make backend-build-static backend-test`

## Notes
- Django/HTMX is the primary UI; React Islands augment interactive widgets
- Ensure `make backend-build-static` before packaging images if not done in CI
- Do not use default secrets in production; set strong `SECRET_KEY` and `ENCRYPTION_KEY`

## Configuration (Kubernetes)

Edit `k8s/backend.yaml` env block (example):

```yaml
      - name: SECRET_KEY
        valueFrom:
          secretKeyRef:
            name: webnet-secrets
            key: SECRET_KEY
      - name: ENCRYPTION_KEY
        valueFrom:
          secretKeyRef:
            name: webnet-secrets
            key: ENCRYPTION_KEY
      - name: DATABASE_URL
        value: postgresql://postgres:postgres@postgres:5432/networkautomation
      - name: REDIS_URL
        value: redis://redis:6379/0
      - name: CELERY_BROKER_URL
        value: redis://redis:6379/0
      - name: CELERY_RESULT_BACKEND
        value: redis://redis:6379/1
```

Apply changes with `make k8s-apply` or `kubectl apply -f k8s/backend.yaml`.

## Testing Without Real Devices

Use simulators (GNS3, EVE‑NG, CML, Containerlab) or target non‑existent IPs to exercise UI and job flows (failures are logged).

## Common Issues

### "Cannot connect to database"
```bash
make k8s-status
kubectl logs deployment/postgres -n default
kubectl rollout restart deployment/postgres -n default
```

### "Celery worker not processing jobs"
```bash
kubectl logs deployment/worker -n default
kubectl rollout restart deployment/worker -n default
```

### CORS/CSRF errors
Configure `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` for your domains.

### Port already in use
```bash
kubectl port-forward svc/backend 9000:8000 -n default
```

## Stop & Update
```bash
make dev-down
git pull
make docker-build
make k8s-redeploy
make migrate
```

## Development Tips
- Use `make dev-services` to run Daphne + worker + beat locally
- Use `make backend-verify` before committing (lint, typecheck, tests)
- See [Developer Guide](./developer-guide.md)

Enjoy automating your network! 🚀
