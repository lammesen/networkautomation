# Architecture Overview

The NetAuto platform is split into backend and frontend services.

## Backend

* FastAPI application (`backend/app`) exposes REST endpoints for authentication, device inventory, job orchestration, compliance policies, configuration history, and WebSocket job logs.
* SQLAlchemy models describe users, credentials, devices, jobs, config snapshots, and compliance state. Alembic manages migrations.
* Celery workers (`backend/celery_app.py`, `app/jobs/tasks.py`) execute automation tasks using Nornir, Napalm, and Netmiko wrappers under `app/automation`. A dry-run mode is available for development while production deployments connect to live devices.
* Jobs persist structured logs, status transitions, per-device summaries, and publish real-time events to Redis so WebSocket clients see live progress.

## Frontend

* React + TypeScript SPA (`frontend/`) uses Vite tooling and axios-based API utilities.
* Features include device inventory, ad-hoc command runner, config backup/deploy workflows, compliance dashboards, job list/detail views, and a WebSocket-powered job console.
* JWT tokens are stored client-side and attached to every API request while WebSocket connections stream log events directly from `/ws/jobs/{id}`.

## Deployment

* `deploy/docker-compose.yml` orchestrates API, PostgreSQL, Redis, Celery worker, and frontend containers.
* Backend/Frontend Dockerfiles describe production builds, and `deploy/nginx.conf` proxies requests.
