---
name: internal-tools
description: Use for building internal tools with RBAC, tenant isolation, audit logging, and job workflows in webnet.
license: MIT
---

# Internal Tools Development (webnet)

Purpose: design/extend operator/admin tooling that touches devices/configs/jobs while honoring RBAC, tenancy, and audit trails.

Rules
- ALWAYS run sequentialThinking first.
- Use tenant mixins/permissions and JobService for any device-affecting work.

When to use
- Bulk operations, job scheduling, compliance runs
- Admin/operator UX, RBAC enforcement, audit logging
- Real-time updates for operational dashboards

Key context
- Roles: viewer (read), operator (read+jobs), admin (full). Implemented in `webnet/api/permissions.py` (RolePermission, CustomerScopedQuerysetMixin, ObjectCustomerPermission).
- Tenancy: scope all queries by customer; use TenantScopedView (UI) or CustomerScopedQuerysetMixin (DRF).
- Job system: use JobService create_job/append_log/set_status; tasks in `webnet/jobs/tasks.py`; broadcasts in `webnet/core/broadcasts.py` for live UI.
- Credentials: encrypted via `webnet/core/crypto.py`; never log/expose plaintext.

Required behavior
- Customer scoping + RBAC on all endpoints/views
- Device operations go through JobService and are logged
- Broadcast updates for UI consistency; handle partial failures
- Add confirmation/dry-run for destructive actions

Artifacts
- HTMX views (`webnet/ui/views.py`) and templates
- DRF viewsets (`webnet/api/views.py`) with permissions set
- Celery tasks if new job types
- Tests for permissions and happy/error paths

Checklist
- Persona/role identified; write permissions gated
- Customer access checked before mutations
- JobService used; logs appended
- WebSocket broadcast wired when state changes
- Tests added; lint/tests passing

Verification
- `make backend-lint`
- `make backend-test`
- Targeted RBAC test: `backend/venv/bin/python -m pytest backend/webnet/tests/test_rbac_scoping.py -v`
- Manual check via `make dev-login-ready-services`

Resources: `docs/security.md`, `docs/multi-tenancy.md`.
