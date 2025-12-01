name: vibe-coding
description: This skill should be used when the user asks to "quickly build", "prototype a feature", "rapidly create", "hack together", or wants to build with creative flow and fast iteration.
Rapid prototyping with HTMX, islands, Tailwind. **Use sequentialThinking.**

Quick patterns: extend `base.html`, use HTMX swaps (`hx-get/hx-post` + `hx-target/hx-swap`), and TenantScopedView helpers (`filter_by_customer`, `ensure_can_write`). Register islands in `islands.tsx` and mount via `data-island` + `data-props`.

Available pieces: shadcn primitives (Button, Card, Dialog, Table, Tabs, Alert, Skeleton), islands (DataTable, JobsTable, FormSelect, JobLogs, ConfirmDialog). Run `make backend-build-static` and keep console clean.

Guardrails: always customer-scope, enforce permissions, avoid secrets.
