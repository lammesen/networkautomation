---
name: django-development
description: Use for Django 5 + DRF work: models, migrations, viewsets, serializers, settings, ORM, tests.
license: MIT
---

# Django Development (webnet)

Purpose: ship Django/DRF changes that follow webnet conventions (tenant scoping, RBAC, Celery, HTMX).

Rules
- ALWAYS run sequentialThinking before coding.
- Prefer CustomerScopedQuerysetMixin + RolePermission everywhere.

When to use
- Create/update models and migrations
- Build DRF viewsets/serializers/routes
- Add HTMX views/templates
- Tune ORM queries or permissions
- Write Django tests

Architecture snapshot
- Apps: users, customers, devices, jobs, config_mgmt, compliance, api, ui, core.
- API layer: `webnet/api/{views,serializers,urls,permissions}.py`
- UI: `webnet/ui/views.py` with TenantScopedView
- Celery: `webnet/jobs/{services,tasks}.py`

Core patterns
- Model: include customer FK, ordering, indexes; keep fields typed and reversible migrations.
- ViewSet: CustomerScopedQuerysetMixin, RolePermission (+ ObjectCustomerPermission when needed); set `customer_field`; use select_related/prefetch.
- Actions: create/update should save with customer from mixin getter.
- Queries: use select_related for FK/OneToOne; prefetch_related for M2M/reverse.

Required behavior
- Tenant isolation on every queryset and serializer
- No plaintext credentials in logs/serializers
- Migrations reversible; check constraints/indexes for perf

Verification
- `make backend-lint`
- `make backend-test`
- `cd backend && ../backend/venv/bin/python manage.py makemigrations --check`

File reference
- `webnet/{app}/models.py`
- `webnet/api/serializers.py`
- `webnet/api/views.py`
- `webnet/api/urls.py`
- `webnet/api/permissions.py`
- `webnet/ui/views.py`
- `webnet/settings.py`

Resources: `docs/models-reference.md`, `docs/api-reference.md`.
