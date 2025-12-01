name: task-orchestration
description: This skill should be used at the START of every session to evaluate delegation to specialized subagents. MANDATORY for complex or multi-domain tasks.
Delegation checklist. **Use sequentialThinking.**

Decision: trivial (<10 min/1 file) → handle; single-domain → delegate to matching subagent; multi-domain → split and delegate; uncertain → investigate briefly then decide.
Subagents: code-reviewer (reviews/audits), test-engineer (pytest), ui-builder (HTMX/React/shadcn), api-developer (DRF/Celery), e2e-tester (Playwright), codebase-auditor (full audit).
Skip delegation for tiny fixes/explanations/config/git.
Use Task tool with `subagent_type` to dispatch.
Ensure delegated work still passes `make backend-lint` + `make backend-test`; reassess if blocked or security-sensitive.
