description: Audit the codebase for security, performance, architecture, and quality
argument-hint: [security|performance|architecture|quality|full]
---
Delegate to `codebase-auditor` via Task. `$ARGUMENTS` sets scope (default `full`).
- Security: auth/input, secrets, tenant isolation
- Performance: N+1, indexing, async tasks
- Architecture/Quality: structure, types, error handling, tests
Output: severity-tagged findings with fixes. After fixes: `make backend-lint && make backend-test`.
