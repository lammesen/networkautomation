---
description: Write or fix pytest tests for a file or feature
agent: test-engineer
---

Use the `test-engineer` agent for tests described in `$ARGUMENTS`.

Resource scope: only `.opencode/{skills,command,agent}`; ignore `.factory/`.

Scope
- `$ARGUMENTS` path → tests for that file
- `$ARGUMENTS` feature → tests for that feature
- Mentions "fix" → focus on failing tests

Process
- Review code + existing tests in `backend/webnet/tests/`
- Cover happy, validation/error, RBAC/tenant cases
- Place tests in `backend/webnet/tests/` (api/view/ws/model naming)
- Run `make backend-test` or targeted pytest

Output: summary, tests added/changed, pytest result, coverage impact if known.
