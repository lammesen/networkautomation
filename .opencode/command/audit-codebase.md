---
description: Run a comprehensive codebase audit for security, performance, and quality
agent: codebase-auditor
---

Use the `codebase-auditor` agent for the scope in `$ARGUMENTS` (security/performance/architecture/quality/full default).

Resource scope: only `.opencode/{skills,command,agent}`; ignore `.factory/`.

Process
1) Map codebase; plan with TodoWrite.
2) Scan by category using glob/read; collect evidence with file:line and severity (critical/important/minor).
3) Apply security, performance, testing, and Django/DRF checklists.
4) Summarize with priority actions; suggest fixes.

Output
- Executive summary
- Findings table by severity
- Stats and prioritized actions
- Notes on tests (`make backend-lint`/`make backend-test` recommended after fixes)

Examples: `/audit-codebase security`, `/audit-codebase performance`, `/audit-codebase full`.
