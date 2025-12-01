---
name: code-review-excellence
description: Use for PR reviews, audits, and quality checks with webnet (Django/DRF) focus.
license: MIT
---

# Code Review Excellence

Purpose: catch correctness, security, performance, and tenant/RBAC issues while giving clear feedback.

Rules
- ALWAYS run sequentialThinking before review.
- Prioritize findings first; be specific with file:line.

When to use
- PR/code review, security/perf audit, architecture/design critique.

Process
1) Context: read description/issue, skim size/CI.
2) High-level: architecture fit, file placement, testing strategy.
3) Detail: logic/edge cases, security (auth/input/secrets), tenant isolation, performance (N+1/pagination/indexes), maintainability.
4) Summarize decision: Approve / Comment / Request changes.

Severity tags
- [blocking], [important], [nit], [suggestion], [praise].

Checklists
- Security: input validated, RolePermission/CSRF, no secrets.
- Tenant: CustomerScopedQuerysetMixin/ObjectCustomerPermission, no cross-tenant serializers.
- Performance: select_related/prefetch, indexes, pagination, heavy work in Celery.
- Testing: happy/edge/error paths; deterministic.
- Django/DRF: type hints, serializer validation, reversible migrations.

Comment template (short)
- Summary
- Strengths
- Required changes (with tags)
- Suggestions
- Verdict

Escalate: auth bypass, tenant leaks, credential exposure, severe perf regressions.

References: `webnet/api/permissions.py`, `webnet/tests/test_rbac_scoping.py`, `docs/security.md`.
