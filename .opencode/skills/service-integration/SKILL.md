---
name: service-integration
description: Use for adding DRF endpoints, Celery tasks, WebSocket updates, or cross-app integrations in webnet.
license: MIT
---

# Service Integration (webnet)

Purpose: extend Django apps (API, jobs, sockets) while preserving domain boundaries and tenancy.

Rules
- ALWAYS run sequentialThinking before work.
- Keep customer scoping and RBAC on every path.

When to use
- New/changed DRF endpoint or serializer
- New Celery task or job type
- WebSocket consumer or broadcast hooks
- Cross-app coordination (devices + jobs + compliance, etc.)

Process
1) Plan domain touchpoints and tenants.
2) API: add serializer → ViewSet/action → URL; use CustomerScopedQuerysetMixin + RolePermission.
3) Celery: add task in `webnet/jobs/tasks.py`, register in JobService enqueue + Job.TYPE_CHOICES.
4) WebSocket: emit via `webnet.core.broadcasts.*` after state changes; consumers live in `webnet/api/consumers.py`.
5) Observability: log via JobService append_log/set_status; handle partial failures.

Required behavior
- Respect domain ownership (reuse services, no cross-app leaks)
- Enforce tenant isolation on queries and broadcasts
- Keep API compatibility; version if breaking
- Never expose credentials

Verification
- `make backend-lint`
- `make backend-test`
- `make dev-login-ready-services` for manual checks

File reference
- `webnet/api/{views,serializers,urls,permissions,consumers}.py`
- `webnet/jobs/{services,tasks}.py`
- `webnet/core/broadcasts.py`

Resources: `docs/api-development.md`, `docs/nornir-integration.md`, JobService patterns.
