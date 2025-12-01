---
description: Run code review on a branch or file changes
agent: code-reviewer
---

Use the `code-reviewer` agent for structured reviews.

Resource scope: only use `.opencode/{skills,command,agent}` content; ignore `.factory/`.

Scope
- `$ARGUMENTS` branch → review that branch
- `$ARGUMENTS` file → review that file
- Empty → review uncommitted changes

Checklist
- Django/DRF patterns
- Tenant scoping + RBAC
- Security (no secrets, CSRF/auth)
- Query efficiency (select_related/prefetch, pagination)
- Tests present for changes

Output
- Summary (APPROVE / REQUEST CHANGES / NEEDS DISCUSSION)
- Criticals, warnings, suggestions
- Tenant + security checklist
- Follow-ups if needed
