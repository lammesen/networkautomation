---
name: frontend-ui-integration
description: Use for HTMX templates, React Islands, or shadcn/ui work in webnet.
license: MIT
---

# Frontend UI Integration (HTMX + React Islands)

Purpose: build user-facing flows with Django templates, HTMX swaps, and React islands using shadcn/ui + Tailwind.

Rules
- ALWAYS run sequentialThinking before changes.
- Follow existing layout/components; keep accessibility and CSRF.

When to use
- Add/modify HTMX pages or partials
- Create React islands for interactive pieces
- Wire shadcn/ui components

Architecture
- HTMX templates: `backend/templates/`, partials prefixed `_`, extend `base.html`.
- Islands: `backend/static/src/components/islands/`, registered in `backend/static/src/islands.tsx`, hydrate via `data-island` + JSON `data-props` (rehydrates after htmx swaps).
- UI primitives: `backend/static/src/components/ui/`; styles in `backend/static/src/input.css`.

Conventions
- HTMX attrs: hx-get/hx-post, hx-target, hx-swap, hx-trigger, hx-indicator; include `{% csrf_token %}`.
- Templates should use TenantScopedView data and avoid inline JS secrets.
- Islands should stay stateless, server is source of truth; handle loading/error states.

Verification
- `make backend-build-static`
- `make backend-lint`
- `make dev-login-ready-services` for manual check

Safety
- CSRF on forms; escape JSON props (`|escapejs`); keep tenant scoping via views.

References: `docs/htmx-patterns.md`, `docs/react-islands.md`, shadcn MCP for components.
