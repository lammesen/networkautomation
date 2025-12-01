description: Run code review on a branch or file changes
argument-hint: <branch-name-or-file-path>
---
Delegate to `code-reviewer` via Task. `$ARGUMENTS` = branch/path or empty for working tree.
Checks: Django/DRF patterns, tenant scoping, RBAC, security, queries, tests.
Output: APPROVE / REQUEST CHANGES / NEEDS DISCUSSION with Critical, Warnings, Suggestions.
