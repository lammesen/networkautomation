# Repository Guidelines

FastAPI backend + React/TS frontend. Tests in `backend/app/tests/` and `frontend/src/__tests__/`.

## Commands
- `make bootstrap` — install all deps (backend editable + frontend via Bun)
- `make backend-lint` — Ruff + Black check; `make backend-test` — full pytest suite
- Single backend test: `cd backend && ../backend/venv/bin/python -m pytest app/tests/test_file.py::test_name -v`
- `cd frontend && bun run test` — all frontend tests; single: `bun test --preload ./tests/setup.ts src/__tests__/file.test.tsx`
- `make test` — backend tests + frontend build (pre-PR gate)

## Code Style
- **Python 3.11**: Black + Ruff (line-length 100), mypy `disallow_untyped_defs=true`. snake_case functions, PascalCase classes/schemas, UPPER_SNAKE env vars. All functions require type hints.
- **TypeScript**: strict mode, 2-space indent, PascalCase components, `use*` hooks. Lint: `bunx eslint .`
- **Imports**: stdlib → third-party → local (blank line between groups). Prefer absolute imports.
- **Errors**: Use domain exceptions in `backend/app/domain/exceptions.py`; FastAPI error handlers in `api/errors.py`.

## Structure
- Backend: `api/` routers, `automation/` Nornir/NAPALM tasks, `jobs/` Celery, `db/` models, `schemas/` Pydantic
- Frontend: `components/`, `pages/`, `features/`, `api/`; entry `App.tsx`
- Migrations: `backend/alembic/versions/`; run via `make migrate`
