# webnet Agent Guidelines

## Mandatory Rules
1. **Always use `sequentialThinking`** for ALL tasks - plan before coding
2. **EVALUATE DELEGATION FIRST** - Before starting any non-trivial task, assess if it should be delegated to a specialized subagent (see Orchestration below)
3. **Log progress** to `progress.md` with timestamped bullets for every meaningful step
4. **Use MCP tools first** before standard tools when relevant
5. **Use Skills** for domain-specific tasks (see below)
6. **Delegate complex tasks** to specialized agents via Task tool

## Task Orchestration (MANDATORY)

**At the START of every non-trivial request**, evaluate delegation using the `task-orchestration` skill:

```
1. CLASSIFY: Is this trivial (<10 min), focused (1 domain), or complex (multi-domain)?
2. MATCH: Which subagent(s) specialize in this domain?
3. DECIDE: Handle directly OR delegate to subagent(s)
4. EXECUTE: If delegating, use Task tool with appropriate subagent_type
```

### Quick Delegation Reference

| Task Type | Action |
|-----------|--------|
| Code review, security audit | → `code-reviewer` |
| Writing/fixing tests | → `test-engineer` |
| HTMX templates, React components | → `ui-builder` |
| DRF APIs, Celery tasks | → `api-developer` |
| Browser testing, E2E | → `e2e-tester` |
| Full codebase audit | → `codebase-auditor` |
| Trivial changes (<10 lines) | → Handle directly |

### When to Delegate

- **DO delegate**: Multi-file changes, domain-specific work, testing, reviews
- **DON'T delegate**: Quick fixes, explanations, config changes, git commits

## Core Commands
| Task | Command |
|------|---------|
| Install deps | `make backend-install && make backend-npm-install` |
| Build CSS | `make backend-build-css` |
| Build JS | `make backend-build-js` |
| Build static | `make backend-build-static` (CSS + JS + collectstatic) |
| Run tests | `make backend-test` |
| Single test | `backend/venv/bin/python -m pytest backend/webnet/tests/<file>.py -k <name>` |
| Lint/format | `make backend-lint` |
| Dev server | `make dev-backend` (Daphne ASGI for WebSocket support) |
| Dev server (simple) | `make dev-backend-simple` (Django runserver, no WebSocket) |
| Dev worker | `make dev-worker` (Celery worker) |
| Dev beat | `make dev-beat` (Celery beat scheduler) |
| Dev all services | `make dev-login-ready-services` (install + build + migrate + seed + start all) |
| Migrate | `make migrate` or `make dev-migrate` |
| Seed admin | `make seed-admin` or `make dev-seed` |
| Bootstrap | `make bootstrap` (install Python + npm deps) |
| Type check | `backend/venv/bin/python -m mypy backend/webnet` |

## Architecture
- **Backend**: Django 5 + DRF + Channels + Celery (Python 3.11)
- **Frontend**: HTMX (95%) + React Islands (5%) + shadcn/ui + Tailwind
- **Database**: PostgreSQL (production) / SQLite (dev default)
- **Message Broker**: Redis (Celery + Channels)
- **Automation**: Nornir + NAPALM + Netmiko
- **Multi-tenant**: All queries must be customer-scoped
- **RBAC**: Use `RolePermission` on all viewsets
- **WebSockets**: Channels + Daphne ASGI server

## Django Apps
| App | Purpose |
|-----|---------|
| `api` | REST API endpoints, serializers, permissions, WebSocket consumers |
| `compliance` | Compliance policies and results |
| `config_mgmt` | Configuration snapshots and deployment |
| `core` | Celery, crypto, middleware, signals, SSH manager |
| `customers` | Multi-tenant customer model and IP ranges |
| `devices` | Network device inventory and credentials |
| `jobs` | Job tracking and Celery tasks |
| `networkops` | Network operations support |
| `ui` | HTMX view handlers |
| `users` | User model, authentication, API keys |

## Skills (`.opencode/context/skills/`)
Invoke skills for domain expertise:

| Skill | Use When |
|-------|----------|
| `task-orchestration` | **START OF EVERY SESSION** - Evaluate delegation before starting work |
| `django-development` | Models, migrations, views, serializers, ORM |
| `frontend-ui-integration` | HTMX templates, React Islands, shadcn/ui |
| `service-integration` | DRF APIs, Celery tasks, WebSocket consumers |
| `browser` | Playwright E2E testing, screenshots |
| `code-review-excellence` | PR reviews, security audits, quality checks |
| `data-querying` | Django ORM queries, reports, metrics |
| `internal-tools` | Admin panels, RBAC, audit logging |
| `ai-data-analyst` | Data analysis, insights, reporting |
| `product-management` | Feature planning, user stories, requirements |
| `vibe-coding` | Rapid prototyping, creative UI building |

## Agents (`.opencode/agent/`)
Delegate to specialized subagents via Task tool:

| Agent | Purpose | Invoke |
|-------|---------|--------|
| `code-reviewer` | Review code for correctness, security, tenant scoping | `/review <branch>` |
| `test-engineer` | Write/fix pytest tests | `/write-tests <file>` |
| `ui-builder` | Build HTMX/React/shadcn UI | `/build-ui <feature>` |
| `api-developer` | Build DRF viewsets, Celery tasks | `/build-api <feature>` |
| `e2e-tester` | Playwright browser automation | `/e2e-test <workflow>` |
| `codebase-auditor` | Full security/performance audit | `/audit-codebase [scope]` |

## Slash Commands (`.opencode/command/`)
| Command | Purpose |
|---------|---------|
| `/audit-codebase` | Run comprehensive security/performance audit |
| `/build-api` | Create DRF viewsets and Celery tasks |
| `/build-ui` | Build HTMX templates and React Islands |
| `/e2e-test` | Run Playwright browser tests |
| `/review` | Review code for quality and security |
| `/write-tests` | Generate pytest test cases |

## MCP Servers (`opencode.json`)
| Server | Use For |
|--------|---------|
| `sequential-thinking` | Structured problem-solving (MANDATORY) |
| `context7` | Library documentation lookup |
| `shadcn` | UI component discovery and installation |
| `gh-grep` | Real-world code examples from GitHub |
| `playwright` | Browser automation and testing |
| `chrome-devtools` | DevTools control and inspection |

## Code Style
- Type hints on all functions (mypy strict)
- Line length: 100 chars (ruff + black)
- Imports: standard → third-party → local
- Use `timezone.now()`, never naive datetimes
- DRF serializers/viewsets patterns already present

## Key Patterns

### Tenant Scoping
```python
# All customer-related viewsets must use CustomerScopedQuerysetMixin
class DeviceViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    customer_field = "customer_id"  # or nested like "policy__customer_id"
    permission_classes = [IsAuthenticated, RolePermission]
```

### Permissions
```python
# Standard permission pattern for all viewsets
permission_classes = [IsAuthenticated, RolePermission]
# RolePermission enforces: viewer=read-only, operator=CRUD, admin=all

# For object-level customer checks
permission_classes = [IsAuthenticated, RolePermission, ObjectCustomerPermission]
```

### HTMX Partials
- Prefix partial templates with `_` (e.g., `_table.html`, `_modal.html`)
- Partials are swapped via HTMX `hx-swap` attribute
- Use `hx-target` to specify swap target

### React Islands
- Register components in `backend/static/src/islands.tsx`
- Use `data-island="ComponentName"` attribute in templates
- Pass props via `data-props='{"key": "value"}'` JSON attribute
- Islands auto-hydrate on DOM ready and after HTMX swaps
- Build with `make backend-build-js` (esbuild)

### Celery Tasks
```python
from webnet.core.celery import celery_app

@celery_app.task(bind=True)
def my_task(self, job_id: int, customer_id: int) -> dict:
    # Always scope by customer_id
    # Use JobService for job lifecycle management
    # Broadcast updates via Channels for WebSocket clients
```

### WebSocket Consumers
- Job logs: `/ws/jobs/<id>/` - `JobLogsConsumer`
- SSH terminal: `/ws/devices/<id>/ssh/` - `SSHConsumer`
- Updates: `/ws/updates/` - `UpdatesConsumer` (entity change broadcasts)

## File Locations
| Type | Path |
|------|------|
| Django apps | `backend/webnet/{app}/` |
| Models | `backend/webnet/{app}/models.py` |
| API views/serializers | `backend/webnet/api/views.py`, `backend/webnet/api/serializers.py` |
| API permissions | `backend/webnet/api/permissions.py` |
| API URLs | `backend/webnet/api/urls.py` |
| UI views | `backend/webnet/ui/views.py` |
| UI URLs | `backend/webnet/ui/urls.py` |
| Templates | `backend/templates/` |
| Template partials | `backend/templates/{app}/_*.html` |
| React Islands | `backend/static/src/components/islands/` |
| Island registry | `backend/static/src/islands.tsx` |
| shadcn components | `backend/static/src/components/ui/` |
| CSS entry | `backend/static/src/input.css` |
| Celery tasks | `backend/webnet/jobs/tasks.py` |
| Celery app | `backend/webnet/core/celery.py` |
| Tests | `backend/webnet/tests/` |
| Settings | `backend/webnet/settings.py` |
| ASGI config | `backend/webnet/asgi.py`, `backend/webnet/routing.py` |

## Verification Checklist
Before completing any task:
- [ ] `make backend-lint` passes (ruff + black)
- [ ] `make backend-test` passes (pytest)
- [ ] Tenant scoping verified (no cross-customer data leaks)
- [ ] Type hints added to new functions (mypy strict)
- [ ] Progress logged to `progress.md` with timestamp
- [ ] Static assets rebuilt (`make backend-build-static` if UI changes)
- [ ] Migrations created/applied if model changes
- [ ] WebSocket consumers tested if added/modified
- [ ] React islands registered in `islands.tsx` if new component added
