# Refactor Baseline Inventory

This document captures the current behaviour of the Network Automation platform before the refactor. It focuses on API surface area, automation flows, data models, and frontend responsibilities so that parity can be preserved while restructuring the codebase.

## 1. Backend API Surface

| Router | Module | Key Endpoints | Notes |
| --- | --- | --- | --- |
| Auth | `app/api/auth.py` | `POST /auth/login`, `GET /auth/me`, `POST /auth/register` | JWT issuance via `app.core.auth`; registration creates inactive viewer accounts. |
| Users | `app/api/users.py` | `GET /users`, `GET/PUT /users/{id}` | Admin-only mutations; manages role/activation. |
| Customers | `app/api/customers.py` | CRUD for tenants + `/ranges` sub-resource | Multi-tenancy implemented via explicit customer context and IP range scoping. |
| Devices | `app/api/devices.py` | CRUD, CSV import | Mixes validation, tenancy resolution, and DB writes inside router. |
| Credentials | `app/api/devices.py` (`cred_router`) | CRUD | Names are unique per customer. |
| Jobs | `app/api/jobs.py` | List jobs, fetch detail/logs/results | Relies on `app.jobs.manager` helpers and `Job.result_summary_json`. |
| Commands | `app/api/commands.py` | `POST /commands/run`, `GET /commands/suggestions` | Kicks off Celery jobs for multi-device CLI execution. |
| Config | `app/api/config.py` | Backup, deploy preview/commit, snapshot diff | Uses `tasks_config` and NAPALM under the hood. |
| Compliance | `app/api/compliance.py` | Policy CRUD, run compliance, fetch results | Stores YAML definitions and per-device run output. |
| Websocket | `app/api/websocket.py` | `/ws/jobs/{job_id}` | Streams logs from Redis pub/sub for real-time updates. |

Cross-cutting dependencies:

- `Depends(get_db)` wires a request-scoped SQLAlchemy session.
- `get_current_user` + `get_current_active_customer` enforce auth + tenant context (header `X-Customer-ID`).
- Routers presently contain domain logic (queries, validations, logging) that will be relocated into services.

## 2. Data Models & Persistence

Defined in `app/db/models.py` with Alembic migrations (`backend/alembic`). Highlights:

- **User**: username, bcrypt password, role (`viewer|operator|admin`), activation flags.
- **Customer**: multi-tenancy anchor, with many-to-many `user_customers` association and IP ranges.
- **Credential**: per-customer device credentials (future encryption/Vault integration).
- **Device**: inventory record with vendor/platform/role/site/tags, credential reference, reachability metadata.
- **Job / JobLog**: asynchronous execution lifecycle, JSON blobs for targets and results.
- **ConfigSnapshot**: captured device configs, hashed for deduplication.
- **CompliancePolicy / ComplianceResult**: YAML definitions mapped to per-device outcomes.

All relationships are eager-friendly; indexes exist on common filters (role, site, vendor, status).

## 3. Automation & Job Fabric

- **Celery Stack**: Configured via `backend/app/celery_app.py` with Redis broker; tasks live in `app/jobs/tasks.py`.
- **Job Orchestration**: `app/jobs/manager.py` creates jobs, transitions status (`queued → running → success/partial/failed`), and persists logs (`JobLog`). Websocket consumers subscribe to Redis channels for streaming.
- **Nornir Integration**: `app/automation/nornir_init.py` bootstraps inventory from the database; tasks split across:
  - `tasks_cli.py`: Netmiko command execution, capturing per-device outputs.
  - `tasks_config.py`: NAPALM config backup/deploy (load/compare/commit + snapshot persistence).
  - `tasks_validate.py`: Compliance runs using NAPALM validation YAML.
- **Inventory Adapter**: `automation/inventory.py` maps DB devices → Nornir hosts including credential resolution and attribute enrichment.

Pain points motivating the refactor:

- Router functions directly manipulate SQLAlchemy sessions and Celery tasks.
- No shared abstractions for selecting device cohorts or constructing job payloads.
- Logging/error handling duplicated across tasks and API modules.

## 4. Frontend Baseline

- **Framework**: React 18 + TypeScript, Vite toolchain, Bun scripts.
- **State/Data**: Zustand (`src/store/authStore.ts`) for auth; TanStack Query for server state; fetch wrapper in `src/api/client.ts`.
- **UI**: Shadcn-inspired components already present under `src/components/ui`.
- **Pages**: Monolithic route components in `src/pages/*.tsx` (e.g., `DevicesPage` combines filters, tables, dialogs, import workflow in ~400 lines).
- **Routing**: React Router with guarded dashboard layout; websocket consumption limited to job log console components.

Goals for refactor:

- Introduce feature directories (`src/features/<domain>/`) housing hooks, components, and mutations.
- Generate typed API clients from FastAPI OpenAPI schema instead of manual fetch helpers.
- Encapsulate websocket logic in reusable hooks/components for jobs/log streaming.

## 5. Deployment Context

- Docker Compose (`deploy/docker-compose.yml`) orchestrates Postgres, Redis, backend (Uvicorn), Celery worker, and frontend (Vite dev or static build via nginx).
- Kubernetes manifests under `k8s/` mirror the same topology with dedicated deployments/services and PVCs.
- `docs/architecture.md` outlines roadmap items (NetBox integration, scheduled jobs, etc.) that must remain possible after the refactor.

This baseline should be treated as the contract to preserve during the backend/service reorganization and frontend feature-module rewrite.


