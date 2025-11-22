# Repository Guidelines

Guidelines for the FastAPI backend, React frontend, and supporting microservices.

## Project Structure & Module Organization
- `backend/app/`: FastAPI — routers in `api/`, NAPALM/Nornir tasks in `automation/`, Celery jobs in `jobs/`, DB models in `db/`, schemas in `schemas/`; migrations in `backend/alembic/`.
- `frontend/src/`: React + TS — `components/`, `pages/`, `features/`, `api/`; entry in `App.tsx`.
- `network-microservice/`: SSH relay microservice (Dockerized).
- Ops assets: `deploy/` Dockerfiles, `k8s/` manifests, `docs/` refs, and `Makefile` shortcuts.

## Build, Test, and Development Commands
- `make bootstrap` — install backend (editable + dev extras) and frontend deps via Bun.
- `make backend-lint` — Ruff + Black check on `backend/app`.
- `make backend-test` / `make ssh-test` — full pytest suite or targeted SSH/WebSocket tests.
- `cd frontend && bun run test` — frontend tests (Bun + happy-dom preload); add `*.test.tsx` under `frontend/src`.
- `make frontend-build` / `make frontend-dev` — Vite production or dev server.
- `make test` — backend tests plus frontend build; good pre-PR gate.
- `make dev-up` / `make dev-down` — build images, apply/remove k8s manifests; `make k8s-status` to inspect pods/svcs.
- `make migrate` and `make seed-admin` — run Alembic migrations and seed data inside the backend deployment.

## Coding Style & Naming Conventions
- Python 3.11; Black + Ruff (line length 100); mypy with `disallow_untyped_defs=true`. snake_case for functions/modules, PascalCase for classes/schemas, UPPER_SNAKE for env vars. Versioned FastAPI routers under `backend/app/api`.
- TypeScript strict; functional components in PascalCase, hooks `use*`, 2-space indent. Run `bunx eslint .` before commits.

## Testing Guidelines
- Backend tests live in `backend/app/tests/`; name files `test_*.py`, mirror package layout. Use `pytest -k <pattern>`; async with `pytest.mark.asyncio`; coverage via `pytest --cov=app`.
- Frontend tests use Bun + happy-dom: specs `*.test.tsx` under `frontend/src`, run `bun run test` (or `bun test --preload ./tests/setup.ts <pattern>`). Prefer React Testing Library queries.

## Commit & Pull Request Guidelines
- Commits: imperative, scoped, <72-char subjects (e.g., “Refactor job scheduler”).
- PRs: summary, linked issue, test evidence (`make test` or manual steps), migration notes, UI screenshots/GIFs when visuals change; note k8s/Docker impacts.

## Security & Configuration Notes
- No secrets in git; use env vars or k8s secrets (`k8s/*.yaml`).
- Rotate `SECRET_KEY`, DB, and Redis creds per environment. After schema changes, rebuild images and rerun `make migrate`.
- Limit management network exposure; prefer port-forwarding (`make k8s-port-forward-backend` / `…-frontend`) in dev.
