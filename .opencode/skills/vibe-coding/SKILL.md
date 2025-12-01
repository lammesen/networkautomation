---
name: vibe-coding
description: Use to rapidly prototype features/pages in webnet with HTMX + React Islands + Tailwind while keeping tenant/RBAC rules.
license: MIT
---

# Vibe Coding (webnet)

Purpose: build fast, creative prototypes in the existing stack without skipping safety (tenancy, RBAC, JobService).

Rules
- ALWAYS run sequentialThinking first—even when moving fast.
- Stick to Django + HTMX + React Islands + Tailwind + shadcn/ui.

When to use
- Quick feature/page prototypes, UI iterations, end-to-end flow spikes.

Constraints
- Respect tenant isolation (TenantScopedView/CustomerScopedQuerysetMixin) and write permissions (ensure_can_write/RolePermission).
- Device-affecting actions go through JobService for audit trail.
- Reuse existing components/islands before creating new ones.

Quick patterns
- HTMX page: template in `backend/templates/{feature}/`, extend `base.html`, partials prefixed `_`; view in `webnet/ui/views.py`; route in `webnet/ui/urls.py`; include `{% csrf_token %}`.
- React island: component in `backend/static/src/components/islands/`, typed props, registered in `backend/static/src/islands.tsx`; used via `data-island` + JSON props; handle loading/error states.
- Fast API action: ViewSet action with RolePermission + tenant mixin; respond with minimal JSON for HTMX/islands.

Checklists
- Template extends base; view uses TenantScopedView; URL wired; CSRF included; queries scoped by customer.
- Islands registered and props escaped; static rebuilt.
- JobService used for jobs; no credential exposure.

Verification
- `make backend-build-static`
- `make dev-backend` or `make dev-login-ready-services`
- `make backend-test` (or targeted tests) when behavior matters

Safety: sanitize inputs, avoid exposing secrets, keep console clean.
