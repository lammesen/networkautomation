---
description: Build HTMX templates, React Islands, or shadcn components
agent: ui-builder
---

Use the `ui-builder` agent for the `$ARGUMENTS` UI feature.

Resource scope: only `.opencode/{skills,command,agent}`; ignore `.factory/`.

Process
1) Understand feature and existing patterns.
2) HTMX templates/partials in `backend/templates/`; islands in `backend/static/src/components/islands/` + register in `islands.tsx`; shadcn components in `backend/static/src/components/ui/`.
3) Prefer HTMX; islands for complex interactivity; use shadcn MCP when adding components.
4) Build assets: `make backend-build-static`.

Examples: filter sidebar, modal delete, status badge, live job progress UI.
