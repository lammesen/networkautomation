description: Write or fix pytest tests for a file or feature
argument-hint: <file-path-or-feature-name>
---
Delegate to `test-engineer` via Task. `$ARGUMENTS` = file path or feature.
Cover happy path, errors, RBAC, tenant isolation. Tests live in `backend/webnet/tests/`.
After: `make backend-test`.
