 # Developer Guide
 
 Authoritative guide for working on the Network Automation codebase (Django + DRF + Channels + Celery, HTMX UI with React Islands).
 
 See also: [Architecture](./architecture.md) (legacy), [API Development](./api-development.md), [Testing](./testing.md), [HTMX Patterns](./htmx-patterns.md), [React Islands](./react-islands.md), and [Multi‑tenancy](./multi-tenancy.md).
 
 ## Prerequisites
 - Python 3.11+
 - Node.js + npm
 - Redis and PostgreSQL (Docker/K8s manifests provided; SQLite works for quick dev)
 - GNU Make
 
 ## Quick Start (Local Dev)
 
 ```bash
 make backend-install         # Python deps (editable, [dev])
 make backend-npm-install     # Frontend deps for Tailwind/Islands
 make backend-build-static    # Tailwind + Islands + collectstatic
 make dev-migrate             # Django migrations
 make dev-seed                # Create superuser from env
 make dev-services            # Daphne (ASGI) + Celery worker + Celery beat
 # UI → http://localhost:8000
 ```
 
 Useful alternates:
 - `make dev-backend` (Daphne ASGI only)
 - `make dev-worker` (Celery worker)
 - `make dev-beat` (Celery beat)
 
 Environment file: `backend/.env` (copy from `backend/.env.example`).
 
 Required secrets:
 - `SECRET_KEY`: random 32+ char string
 - `ENCRYPTION_KEY`: Fernet base64 key (`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)
 
 ## Project Structure (Backend)
 
 - `backend/webnet/api`: DRF viewsets, serializers, permissions, Channels consumers
 - `backend/webnet/core`: Celery app, crypto, middleware, SSH manager, metrics
 - `backend/webnet/jobs`: Job models, serializers, services, Celery tasks
 - `backend/webnet/devices`, `users`, `customers`, `config_mgmt`, `compliance`, `networkops`: domain apps
 - `backend/templates`: Django templates (HTMX first)
 - `backend/static/src`: React Islands and shadcn/ui components; Tailwind input
 - `backend/webnet/tests`: pytest test suite
 
 See paths and patterns in [AGENTS.md](/AGENTS.md).
 
 ## Runtime Architecture
 - Django 5 + DRF for APIs and server‑rendered UI (HTMX)
 - Channels + Daphne (ASGI) for WebSockets (live job logs, SSH)
 - Celery + Redis for background tasks
 - PostgreSQL as the main DB (SQLite for quick dev)
 
 ## Multi‑tenancy & RBAC
 - All queries must be tenant‑scoped to the current `customer_id`
 - Standard permissions: `IsAuthenticated` + `RolePermission`; use `ObjectCustomerPermission` for object‑level checks
 - Viewset pattern:
 
 ```python
 class DeviceViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
     customer_field = "customer_id"  # or nested: "policy__customer_id"
     permission_classes = [IsAuthenticated, RolePermission]
 ```
 
 See: [multi-tenancy.md](./multi-tenancy.md) and patterns in [AGENTS.md](/AGENTS.md).
 
 ## Celery Tasks
 - Define tasks in `webnet/jobs/tasks.py`
 - Import Celery app from `webnet/core/celery.py`
 - Always pass `customer_id` and use services for lifecycle/logging
 
 ```python
 from webnet.core.celery import celery_app
 
 @celery_app.task(bind=True)
 def run_commands(self, job_id: int, customer_id: int) -> dict:
     # Scope by customer; write logs; broadcast updates
     ...
 ```
 
 ## WebSockets
 - Job logs: `/ws/jobs/<id>/` → `JobLogsConsumer`
 - SSH terminal: `/ws/devices/<id>/ssh/` → `SSHConsumer`
 - Updates: `/ws/updates/` → `UpdatesConsumer`
 
 Defined in `webnet/api/consumers.py` and `webnet/api/ssh_consumer.py`; routing in `webnet/routing.py`.
 
 ## UI: HTMX + React Islands
 - Prefer HTMX partials for most interactions (`backend/templates/.../_*.html`)
 - Use React Islands for highly interactive widgets (tables, terminals)
 - Register islands in `backend/static/src/islands.tsx`
 - Build bundles: `make backend-build-js`; Tailwind: `make backend-build-css`; full: `make backend-build-static`
 
 Quick island embed pattern:
 
 ```html
 <div data-island="JobsTable" data-props='{"customerId": 1}'></div>
 ```
 
 ## Testing & Quality Gates
 
 - Run tests: `make backend-test`
 - Lint/format: `make backend-lint` / `make backend-format`
 - Type check: `make backend-typecheck`
 - Verify all: `make backend-verify`
 - Tests live in `backend/webnet/tests/`
 
 Recommended pre‑commit hooks: see `.pre-commit-config.yaml`.
 
 ## Makefile Cheat Sheet
 
 - Setup: `make backend-install`, `make backend-npm-install`, `make bootstrap`
 - Build assets: `make backend-build-css`, `make backend-build-js`, `make backend-build-static`
 - Dev runtime: `make dev-backend`, `make dev-worker`, `make dev-beat`, `make dev-services`
 - DB: `make dev-migrate`, `make migrate`, `make dev-seed`, `make seed-admin`
 - CI: `make backend-verify`, `make backend-test`, `make backend-js-check`
 - K8s: `make dev-up`, `make k8s-status`, `make k8s-redeploy`, `make dev-down`
 
 ## Common Dev Tasks
 
 - Add a model: create in `models.py`, run `makemigrations/migrate`, add admin as needed
 - Add an API: serializer + viewset + url in `webnet/api`; apply tenant scoping and permissions
 - Add a background task: define Celery task; call from a service; emit job updates via Channels
 - Add an island: create component in `static/src/components/islands`, register in `islands.tsx`, rebuild JS
 - Add HTMX interaction: create partial `_partial.html`; use `hx-get/post`, `hx-target`, `hx-swap`
 
 ## Security & Compliance
 - Never bypass tenant scoping
 - Encrypt device secrets; ensure `ENCRYPTION_KEY` is set in all envs
 - Follow RBAC patterns; add tests for permission boundaries
 - CodeQL and secret scanning run in CI
 
 ## Troubleshooting Dev Env
 - Missing static: run `make backend-build-static`
 - WebSockets not working: ensure you're running Daphne (`make dev-backend`) not `runserver`
 - Worker idle: check Redis and Celery env (`CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`)
 
 ## Contributing
 See [CONTRIBUTING](/CONTRIBUTING.md). Ensure tests/lint/typecheck pass and follow tenant/RBAC patterns before opening a PR.
 