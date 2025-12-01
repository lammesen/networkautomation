# Django + HTMX + DRF Migration Plan (Project: webnet)

## Objectives
- Replace FastAPI/React stack with Django + HTMX + Tailwind + DRF while preserving automation features.
- Maintain API parity for external systems; expose DRF endpoints with JWT + session auth.
- Keep Celery/Redis-based job orchestration, Nornir/NAPALM/Netmiko automation, compliance, config mgmt, topology, SSH streaming.
- Introduce Channels for websockets (job logs, SSH) and server-rendered UI with HTMX.
- Update Docker/K8s/Makefile/docs/tests accordingly; enforce progress tracking in `progress.md`.

## Phase 1 – Scaffolding & Foundations
1. Create Django project `webnet` under `backend/`.
2. Apps: `core`, `users`, `customers`, `devices`, `jobs`, `config_mgmt`, `compliance`, `networkops`, `api`, `ui`.
3. Settings: DB (PostgreSQL), Redis (cache/broker), Celery, Channels (Redis layer), DRF (JWT + session), CORS, static/media, Tailwind paths, Fernet `ENCRYPTION_KEY`, `SECRET_KEY`.
4. Custom user model (AbstractUser) with `role` (viewer/operator/admin) + M2M `customers`; API keys model.
5. Base utilities: encrypted field/helpers, pagination defaults, filter backends, logging/metrics, base templates.

## Phase 2 – Data Model Migration
Map SQLAlchemy models to Django ORM (with initial migrations):
- Customers: `Customer`, `CustomerIPRange`.
- Users: custom `User`, `APIKey`.
- Credentials: encrypted `Credential` (password/enable_password), FK to Customer.
- Devices: `Device` (hostname, mgmt_ip, vendor, platform, role, site, tags JSON, credential FK, enabled, reachability fields), `TopologyLink`.
- Jobs: `Job` (type/status/timestamps/target+result JSON/payload JSON), `JobLog`.
- Config: `ConfigSnapshot` (hash, text, source, job FK, device FK).
- Compliance: `CompliancePolicy` (scope_json, definition_yaml, customer), `ComplianceResult`.
- Signals/hooks: hash snapshot on save, encrypt secrets on write.

## Phase 3 – Services & Background Tasks
1. Job service: create, set_status, append_log (emit Channels group_send), enqueue Celery task.
2. Celery tasks ported from FastAPI:
   - run_commands, config_backup, deploy_preview/commit (merge/replace), rollback preview/commit, compliance_check, reachability, topology_discovery, refresh_device_info, scheduled backups.
3. Nornir inventory builder from ORM, driver mapping preserved.
4. Error handling: mark jobs failed on exceptions; summaries mirrored.

## Phase 4 – APIs (DRF)
1. Auth: login, refresh, logout, me (JWT + session), optional register.
2. Users/API keys: CRUD, activate/deactivate, nested api-keys.
3. Customers/IP ranges: CRUD, assign/remove users.
4. Credentials: CRUD (write-only secrets).
5. Devices: CRUD + import CSV, enable/disable, filters, jobs list, snapshots list, topology view.
6. Jobs: list/detail/logs, retry, cancel; admin scope listing; pagination + filters.
7. Commands/network ops: run commands, reachability, topology discover.
8. Config: backup, snapshot detail, device snapshots, diff, deploy preview/commit, rollback preview/commit.
9. Compliance: policies CRUD, run, results list/detail, overview.
10. Topology links: list/clear.
11. Permissions: Role-based + customer scoping mixins; viewer read-only, operator job actions, admin full.

## Phase 5 – WebSockets (Channels)
- `/ws/jobs/<id>/` streams job logs/status (JWT or session; tenant checks).
- `/ws/devices/<id>/ssh` for interactive SSH via SSHSessionManager; keep keepalive and close semantics.

## Phase 6 – UI (HTMX + Tailwind)
1. Tailwind config scanning `templates/**`; base layout with nav + customer switcher; flash messages.
2. Pages/partials:
   - Auth (login), dashboard summary.
   - Devices list (filters/pagination via HTMX), detail (snapshots, jobs, topology, SSH link), credentials modals, import modal.
   - Jobs list/detail with live logs (WS) + HTMX poll fallback.
   - Commands run form (creates job), reachability/topology triggers.
   - Config snapshots/diff/deploy/rollback flows with forms + partials.
   - Compliance policies CRUD, run, results/overview.
   - Admin: users/customers/api-keys.
3. JS island: xterm.js for SSH terminal; optional small JS for log streaming.

## Phase 7 – Infrastructure
1. Docker: backend image (Django ASGI via Daphne/Uvicorn), collectstatic, tailwind build; worker image for Celery worker/beat.
2. K8s: update manifests to deploy Django web + worker + redis/postgres; channels config; remove React frontend svc; handle static (volume/whitenoise).
3. Makefile: new targets for manage.py migrate, createsuperuser/seed, tailwind build, runserver, celery worker/beat, tests.

## Phase 8 – Tests
- pytest-django/DRF tests: auth/RBAC/tenant scoping, device CRUD/filter, credential encryption, job creation + eager Celery, config snapshot/diff, compliance run, websocket auth smoke, API endpoints compatibility.

## Phase 9 – Docs & Progress Tracking
- Update README and docs to new stack and workflows.
- Enforce agent progress logging in `progress.md`; update AGENTS.md.
- Maintain `progress.md` with checkpoints during execution.

## Execution Order (high-level)
1) Scaffold project/apps/settings; add requirements. 2) Implement models + migrations. 3) Services + Celery tasks + inventory. 4) DRF serializers/viewsets/permissions + urls. 5) Channels consumers. 6) HTMX templates/layouts. 7) Tailwind config/build. 8) Docker/K8s/Makefile updates. 9) Tests + docs. 10) Final sweep/progress update.
