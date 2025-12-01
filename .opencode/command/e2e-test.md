---
description: Run end-to-end browser tests for a workflow
agent: e2e-tester
---

Use the `e2e-tester` agent to exercise the workflow in `$ARGUMENTS` with Playwright MCP.

Resource scope: only `.opencode/{skills,command,agent}`; ignore `.factory/`.

Prereq: dev server at http://localhost:8000 (`make dev-login-ready-services`).

Process
- Plan flow → navigate/snapshot → interact (click/type/fill_form) → wait_for HTMX results
- Verify HTMX swaps and React island hydration
- Capture screenshots, console, network issues

Examples: device creation, job execution/monitoring, login + dashboard, compliance policy flow.

Output: step results (PASS/FAIL), screenshots, console/network errors, HTMX/React notes.
