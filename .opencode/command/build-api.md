---
description: Build DRF viewsets, serializers, or Celery tasks
agent: api-developer
---

Use the `api-developer` agent to build the feature in `$ARGUMENTS`.

Resource scope: only `.opencode/{skills,command,agent}`; ignore `.factory/`.

Process
1) Read requirements from `$ARGUMENTS`.
2) Follow webnet conventions: serializers → viewset/action → router entry; tasks in `backend/webnet/jobs/tasks.py` if needed.
3) Enforce CustomerScopedQuerysetMixin + RolePermission; type hints everywhere.
4) Run lint/tests.

Examples: device tagging endpoint, bulk job action, config diff API, async discovery task.

Verification: `make backend-lint` and `make backend-test`.
