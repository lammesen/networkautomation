name: browser
description: This skill should be used when the user asks to "test the UI", "verify the page works", "capture a screenshot", "check HTMX swaps", or needs Playwright browser automation.
Playwright MCP for UI checks. **Use sequentialThinking.**

Flow: `browser_navigate` → `browser_snapshot` (use refs) → `browser_fill_form`/`browser_click` → `browser_wait_for` after HTMX → `browser_console_messages` → `browser_take_screenshot`.
Key pages: `/login/`, `/`, `/devices/`, `/jobs/`. Island check: `browser_evaluate("() => document.querySelectorAll('[data-island]').length")`.
Stay on localhost, avoid sensitive screenshots, clean up test data.
