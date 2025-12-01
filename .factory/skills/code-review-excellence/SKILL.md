name: code-review-excellence
description: This skill should be used when the user asks to "review code", "audit the codebase", "check for bugs", "review this PR", or needs systematic code analysis.
Code review checklist. **Use sequentialThinking.**

Focus: tenant scoping (`CustomerScopedQuerysetMixin`/customer filters), `permission_classes`, security (ORM, no secrets, CSRF), performance (`select_related/prefetch`, pagination, heavy work in Celery), tests and type hints.

Common issues: mutable defaults, bare `except`, missing types, TS `any`, unhandled async errors.

Output:
```
Summary: APPROVE | REQUEST CHANGES
Critical: <file:line issue>
Warnings: <issue>
Suggestions: <idea>
```
