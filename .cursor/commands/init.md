# Init: Codebase Analysis & AGENTS.md Management

This command provides your Cursor coding agent with instructions to analyze the codebase and create/update `AGENTS.md` documentation.

---

## Phase 1: Codebase Analysis

### 1.1 Discover Project Structure

Execute these steps to understand the codebase:

```
1. Read the root README.md for project overview
2. Read docs/architecture.md for system design
3. List backend/webnet/ to identify Django apps
4. Read backend/webnet/settings.py for configuration patterns
5. Read Makefile for available commands and workflows
6. List .factory/ for skills, droids, and MCP configuration
```

### 1.2 Identify Key Patterns

Analyze these critical files to extract patterns:

| Pattern | Key Files |
|---------|-----------|
| **Models** | `backend/webnet/{app}/models.py` |
| **API Views** | `backend/webnet/api/views.py` |
| **Serializers** | `backend/webnet/api/serializers.py` |
| **Permissions** | `backend/webnet/api/permissions.py` |
| **Celery Tasks** | `backend/webnet/jobs/tasks.py` |
| **UI Views** | `backend/webnet/ui/views.py` |
| **Templates** | `backend/templates/` |
| **React Islands** | `backend/static/src/components/islands/` |
| **Tests** | `backend/webnet/tests/` |

### 1.3 Technology Stack Detection

Confirm these technologies by checking config files:

| Tech | Detection File | Key Indicators |
|------|----------------|----------------|
| Django | `backend/pyproject.toml` | Django version, DRF, Channels |
| Celery | `backend/webnet/core/celery.py` | Celery app configuration |
| HTMX | `backend/templates/base.html` | htmx script inclusion |
| React Islands | `backend/static/src/islands.tsx` | Island registrations |
| Tailwind | `backend/tailwind.config.js` | Tailwind configuration |
| shadcn/ui | `backend/components.json` | shadcn configuration |

### 1.4 Multi-Tenancy Architecture

Analyze tenant isolation by reading:

```
backend/webnet/api/permissions.py  # CustomerScopedQuerysetMixin, RolePermission
backend/webnet/customers/models.py # Customer model
backend/webnet/users/models.py     # User model with customer relationships
```

Key patterns to document:
- `CustomerScopedQuerysetMixin` - filters querysets by user's customers
- `RolePermission` - enforces viewer/operator/admin semantics
- `ObjectCustomerPermission` - object-level customer ownership checks

---

## Phase 2: AGENTS.md Creation/Update

### 2.1 AGENTS.md Structure

The `AGENTS.md` file at the project root should follow this structure:

```markdown
# {Project Name} Agent Guidelines

## Mandatory Rules
1. [Critical workflow rules]
2. [Tool usage priorities]
3. [Progress tracking requirements]

## Task Orchestration (MANDATORY)
[Decision framework for task delegation]

### Quick Delegation Reference
| Task Type | Action |
|-----------|--------|
| ... | → `subagent-name` |

## Core Commands
| Task | Command |
|------|---------|
| ... | `make target` |

## Architecture
- **Backend**: [tech stack]
- **Frontend**: [tech stack]
- **Multi-tenant**: [isolation approach]
- **RBAC**: [permission model]

## Skills (.factory/skills/)
| Skill | Use When |
|-------|----------|
| ... | ... |

## Droids (.factory/droids/)
| Droid | Purpose | Invoke |
|-------|---------|--------|
| ... | ... | ... |

## MCP Servers (.factory/mcp.json)
| Server | Use For |
|--------|---------|
| ... | ... |

## Code Style
- [Type hints requirement]
- [Formatting rules]
- [Import ordering]
- [Datetime handling]

## Key Patterns
- **Tenant scoping**: [mixin/filter used]
- **Permissions**: [permission classes]
- **HTMX partials**: [naming convention]
- **React Islands**: [registration pattern]

## File Locations
| Type | Path |
|------|------|
| ... | `path/to/files/` |

## Verification Checklist
- [ ] Lint passes
- [ ] Tests pass
- [ ] Tenant scoping verified
- [ ] Type hints added
```

### 2.2 Content Generation Steps

For each section, gather information from:

#### Mandatory Rules
- Extract from existing `.cursorrules` or workspace rules
- Include `sequentialThinking` requirement if MCP available
- Include progress logging to `progress.md`

#### Task Orchestration
- Read `.factory/skills/task-orchestration/SKILL.md`
- Map task types to available droids in `.factory/droids/`

#### Core Commands
- Parse `Makefile` for key targets
- Focus on: install, build, test, lint, run, migrate, seed

#### Architecture
- Extract from `README.md` and `docs/architecture.md`
- Identify all major frameworks and their roles

#### Skills
- List `.factory/skills/` directory
- Read each `SKILL.md` for description

#### Droids
- List `.factory/droids/` directory
- Read each droid `.md` for purpose and invocation

#### MCP Servers
- Read `.factory/mcp.json`
- Document each server's purpose

#### Code Style
- Check `pyproject.toml` for ruff/black config
- Check `tsconfig.json` for TypeScript settings
- Note any style guides in docs/

#### Key Patterns
- Analyze actual code for patterns (see Phase 1.2)
- Document mixins, base classes, decorators

#### File Locations
- Map from project structure analysis

---

## Phase 3: Automated Analysis Script

When starting a new project analysis, run these commands:

```bash
# 1. Get project overview
head -100 README.md

# 2. List Django apps
ls -la backend/webnet/

# 3. Check for factory configuration
ls -la .factory/

# 4. List available Make targets
make help

# 5. Check test structure
ls backend/webnet/tests/

# 6. Identify key model patterns
grep -r "class.*Model" backend/webnet/*/models.py

# 7. Check permission classes
grep -r "permission_classes" backend/webnet/

# 8. Find tenant scoping usage
grep -r "CustomerScopedQuerysetMixin" backend/webnet/
```

---

## Phase 4: Updating AGENTS.md

### 4.1 When to Update

Update `AGENTS.md` when:
- New Django app is added
- New skill or droid is created
- Core patterns change (new mixin, permission class)
- Make targets are added/changed
- MCP server configuration changes

### 4.2 Update Procedure

1. **Read current AGENTS.md**
   ```
   Read AGENTS.md to understand existing structure
   ```

2. **Identify changes**
   ```
   Compare against current codebase state
   ```

3. **Update incrementally**
   - Add new entries to existing tables
   - Update outdated information
   - Preserve working sections

4. **Verify completeness**
   - All Django apps listed
   - All skills/droids documented
   - All Make targets current
   - All patterns accurate

### 4.3 Version Control

After updating `AGENTS.md`:
```bash
git add AGENTS.md
git commit -m "docs: update AGENTS.md with [change summary]"
```

---

## Quick Reference: This Project (webnet)

### Current Architecture
- **Backend**: Django 5 + DRF + Channels + Celery
- **Frontend**: HTMX (95%) + React Islands (5%) + shadcn/ui + Tailwind
- **Database**: PostgreSQL + Redis
- **Automation**: Nornir + NAPALM + Netmiko

### Django Apps
| App | Purpose |
|-----|---------|
| `api` | REST API endpoints, serializers, permissions |
| `compliance` | Compliance policies and results |
| `config_mgmt` | Configuration snapshots and deployment |
| `core` | Celery, crypto, middleware, signals |
| `customers` | Multi-tenant customer model |
| `devices` | Network device inventory |
| `jobs` | Job tracking and Celery tasks |
| `networkops` | Network operations support |
| `ui` | HTMX view handlers |
| `users` | User model and authentication |

### Critical Patterns
```python
# ViewSet with tenant scoping and RBAC
class DeviceViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, RolePermission]
    customer_field = "customer_id"
```

### Key Commands
```bash
make backend-install       # Install Python deps
make backend-npm-install   # Install npm deps
make backend-build-static  # Build CSS + JS + collectstatic
make backend-lint          # Ruff + Black check
make backend-test          # Run pytest
make dev-login-ready-services  # Full dev environment
```

---

## Output: What to Produce

After running this init command, the agent should:

1. **Create/update `AGENTS.md`** with all sections filled in from codebase analysis
2. **Log progress** to `progress.md` with timestamped bullets
3. **Report findings** including:
   - Number of Django apps discovered
   - Number of skills and droids available
   - Any missing patterns or inconsistencies
   - Recommendations for documentation improvements

---

## Example Invocation

```
@init

Analyze this codebase and update AGENTS.md with:
- All Django apps and their purposes
- Current skills and droids from .factory/
- Accurate Make targets from Makefile
- Key code patterns from the codebase
```

The agent will then:
1. Use `sequentialThinking` to plan the analysis
2. Read necessary files to gather information
3. Create/update `AGENTS.md` with structured content
4. Log all progress to `progress.md`

