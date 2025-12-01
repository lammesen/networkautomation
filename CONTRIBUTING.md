 # Contributing
 
 Thanks for your interest in contributing! This project is a Django/DRF/Channels/Celery backend with an HTMX‑first UI and small React Islands. Please follow the guidelines below to keep quality high and changes safe.
 
 ## Getting Started
 
 1. Fork and clone the repository
 2. Bootstrap the environment:
    ```bash
    make backend-install backend-npm-install backend-build-static
    make dev-migrate dev-seed
    make dev-services
    ```
 3. Copy `backend/.env.example` to `backend/.env` and set `SECRET_KEY` and `ENCRYPTION_KEY`
 
 ## Development Standards
 
 - Language: Python 3.11 with type hints
 - Frameworks: Django 5 + DRF + Channels; Celery + Redis
 - UI: Django templates + HTMX; React Islands for complex widgets
 - Multi‑tenancy: all queries must be customer‑scoped
 - RBAC: enforce `RolePermission` on all viewsets; use object‑level customer checks where needed
 
 See patterns in [`AGENTS.md`](./AGENTS.md) and docs in `docs/`.
 
 ## Quality Gates
 
 Before opening a PR, ensure all checks pass:
 
 ```bash
 make backend-lint         # Ruff + Black (check)
 make backend-typecheck    # mypy
 make backend-test         # pytest
 make backend-js-check     # TS typecheck for islands
 ```
 
 Recommended: install pre‑commit hooks (`pipx install pre-commit && pre-commit install`). CI also runs CodeQL and secret scanning.
 
 ## Commit & Branching
 
 - Branch names: `feature/<slug>`, `fix/<slug>`, `docs/<slug>`
 - Commits: clear, imperative subject; reference issues when applicable
 - Keep PRs focused and small when possible
 
 ## Adding Features
 
 - Add/modify models → create migrations, include data migrations where needed
 - Add APIs → serializers, viewsets, URLs; apply tenant scoping and permissions
 - Background work → Celery tasks in `webnet/jobs/tasks.py`; use services for job lifecycle and logging
 - UI changes → prefer HTMX partials; for React Islands, register in `static/src/islands.tsx` and rebuild JS
 
 ## Tests
 
 - Add or update tests under `backend/webnet/tests/`
 - Cover permissions, tenant scoping, and edge cases
 - Include WebSocket tests if consumers change
 
 ## Documentation
 
 - Update or add docs in `docs/`
 - Persona‑focused guides: `user-guide.md`, `developer-guide.md`, `maintainers.md`
 - Link new features in `docs/README.md`
 
 ## Review Process
 
 - PR template (if present) should be completed
 - Ensure screenshots for UI changes when relevant
 - Maintainers will review for correctness, security, and multi‑tenancy compliance
 
 ## Reporting Security Issues
 
 Please do not open public issues for sensitive vulnerabilities. Email the maintainer or use the repository’s security policy if available.
 
 Thanks for helping improve the project! 🙌
 