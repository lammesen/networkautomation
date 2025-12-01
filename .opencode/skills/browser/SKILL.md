---
name: browser
description: Use for Playwright/Chrome MCP browser automation: HTMX flows, island hydration, screenshots, E2E checks.
license: MIT
---

# Browser Automation (webnet)

Purpose: validate webnet UI via Playwright or Chrome DevTools MCP (HTMX swaps, island hydration, screenshots, E2E).

Rules
- ALWAYS run sequentialThinking first.
- Prefer snapshot → interact → verify; wait for HTMX swaps.

When to use
- Test HTMX interactions or forms
- Verify React island hydration
- Capture screenshots/console/network evidence
- Run end-to-end flows

Tool quick-reference (Playwright MCP)
- navigate, snapshot, take_screenshot, click, type/fill_form, evaluate, wait_for, console_messages, network_requests.

Key pages/islands
- Login `/login/`, Dashboard `/`, Devices `/devices/`, Jobs `/jobs/`, Job detail `/jobs/{id}/`.
- Islands: DataTable, JobsTable, JobLogs (hydrate after HTMX events).

Workflows
- Login: navigate → snapshot → fill_form → click login → wait_for dashboard text.
- HTMX form: open modal → fill_form → submit → wait_for success → snapshot.
- Hydration check: evaluate `document.querySelectorAll('[data-island]')` and confirm React roots.

Checklist
- Page loads clean (no console/network errors)
- Islands hydrated after load and after HTMX swaps
- Forms/filters update content
- Screenshots captured when useful

Safety
- Use dev environment only; clean up test data; keep tenant isolation in mind.

References: `backend/webnet/tests/` for patterns.
