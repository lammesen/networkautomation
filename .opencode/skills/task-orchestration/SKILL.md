---
name: task-orchestration
description: Use at the start of every non-trivial task to decide direct handling vs delegation to specialized agents.
license: MIT
---

# Task Orchestration

Purpose: pick the fastest safe path—self-serve for trivial work, delegate for focused/complex tasks.

Rules
- ALWAYS run sequentialThinking before working.
- Use TodoWrite to track multi-step efforts.

When to use
- Any task that is not an obvious single-line change.

Process
1) Classify: trivial (single file <10 lines), focused (one domain, 1-2 files), complex (multi-domain/3+ files), exploratory (research first).
2) Match agent: code-reviewer (reviews/audits), test-engineer (tests), ui-builder (HTMX/React/shadcn), api-developer (DRF/Celery), e2e-tester (browser flows), codebase-auditor (full audit).
3) Decide: handle trivial yourself; delegate focused tasks; for complex break into subtasks and delegate sequentially or in parallel; revisit after exploration.
4) Patterns: single delegation, sequential (if dependencies), parallel (independent), iterative (build→test→fix).

Avoid delegation when
- Quick fixes/typos
- Simple read/explanation
- Minor config or git hygiene

Checklist
- sequentialThinking run
- Task classified and domains noted
- Delegation choice made and agents selected if needed
- Sequence (parallel/sequential) chosen
- Todos created/updated

Safety
- Re-evaluate if scope grows or agents block
- Keep tenant/RBAC/security rules in mind for downstream work

References: `.opencode/agent/`, `AGENTS.md`, `.opencode/skills/`.
