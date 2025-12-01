description: Run end-to-end browser tests for a workflow
argument-hint: <workflow-description>
---
Delegate to `e2e-tester` via Task. Ensure server at `http://localhost:8000` (`make dev-login-ready-services`).
`$ARGUMENTS` = workflow (e.g., device create, job monitor, login). Verify HTMX swaps, island hydration, console/network errors.
Output: stepwise PASS/FAIL with screenshots and errors.
