# Copilot Instructions for Network Automation

## Architecture Overview

Django 5 + DRF + Channels backend with HTMX-first UI and React Islands. Multi-tenant SaaS architecture where **all queries must be customer-scoped**.

```
backend/webnet/
├── api/          # DRF viewsets, serializers, permissions, WebSocket consumers
├── core/         # Celery app, crypto, middleware, SSH manager
├── jobs/         # Job models, services, Celery tasks (automation orchestration)
├── devices/      # Device inventory, credentials (encrypted), topology
├── compliance/   # YAML-based policy validation (NAPALM)
├── config_mgmt/  # Configuration backup/deploy, templates
├── customers/    # Tenant model
├── plugins/      # Extensibility system
├── ui/           # Django views for HTMX pages
templates/        # Django templates (HTMX partials prefixed with _)
static/src/       # React Islands + shadcn/ui components
```

## Critical Patterns

### Multi-Tenancy (REQUIRED for all data access)

Always use `CustomerScopedQuerysetMixin` for DRF viewsets:

```python
from webnet.api.permissions import CustomerScopedQuerysetMixin, RolePermission

class DeviceViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    customer_field = "customer_id"  # or "policy__customer_id" for nested
    permission_classes = [IsAuthenticated, RolePermission]
```

For Django views, use `TenantScopedView` from `webnet.ui.views`.

### RBAC Roles
- `viewer`: read-only (SAFE_METHODS)
- `operator`: read + POST (can run jobs)
- `admin`: full access, sees all customers

### Celery Tasks

Define in `webnet/jobs/tasks.py`, always pass `customer_id`:

```python
from webnet.core.celery import celery_app

@celery_app.task(bind=True)
def my_task(self, job_id: int, customer_id: int) -> dict:
    js = JobService()
    job = Job.objects.get(pk=job_id)
    js.set_status(job, "running")
    # ... work ...
    js.set_status(job, "success")
```

### WebSocket Routes (Channels)
- `/ws/jobs/<id>/` – live job logs
- `/ws/devices/<id>/ssh/` – SSH terminal
- `/ws/updates/` – general updates

Consumers in `webnet/api/consumers.py` and `webnet/api/ssh_consumer.py`.

## UI Patterns

### HTMX (Primary)
- Partials: `templates/{app}/_*.html`
- Use `hx-get`, `hx-post`, `hx-target`, `hx-swap`
- Always include `{% csrf_token %}` in forms

### React Islands (Complex widgets)
1. Create component in `static/src/components/islands/`
2. Register in `static/src/islands.tsx`
3. Embed: `<div data-island="MyComponent" data-props='{"key": "value"}'></div>`
4. Build: `make backend-build-js`

## Developer Workflow

```bash
make bootstrap                 # Install Python + npm deps
make backend-build-static      # Build CSS/JS + collectstatic
make dev-migrate               # Django migrations
make dev-seed                  # Create superuser
make dev-services              # Start Daphne + Celery (tmux)
```

### Quality Gates (run before PR)
```bash
make backend-lint              # Ruff + Black
make backend-typecheck         # mypy
make backend-test              # pytest
make backend-js-check          # TypeScript check
```

### Required Environment
- `SECRET_KEY`: random 32+ char string
- `ENCRYPTION_KEY`: Fernet key for credential encryption
- `DATABASE_URL`, `CELERY_BROKER_URL`, `REDIS_URL` for non-dev

## Testing

Tests in `backend/webnet/tests/`. Key fixtures in `conftest.py`:
- `customer`, `other_customer` – tenant isolation
- `admin_user`, `operator_user`, `viewer_user` – RBAC testing
- `device`, `credential` – device fixtures

Always test tenant isolation and permission boundaries.

## Key Files Reference
- Entry: `backend/webnet/urls.py`, `backend/webnet/routing.py`
- Settings: `backend/webnet/settings.py`
- Celery: `backend/webnet/core/celery.py`
- Permissions: `backend/webnet/api/permissions.py`
- Island registry: `backend/static/src/islands.tsx`
