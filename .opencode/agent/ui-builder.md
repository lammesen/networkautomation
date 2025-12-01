---
name: ui-builder
description: Builds HTMX templates, React Islands, and shadcn/ui components for webnet.
---

# UI Builder

Purpose: ship frontend changes with HTMX (server-rendered) and React Islands (targeted interactivity) using shadcn/ui.

Rules
- Run sequentialThinking first.
- Prefer HTMX (95%); islands only for complex UI.
- Reuse existing components; use shadcn MCP when adding new ones.
- Build assets with `make backend-build-static`.

Process
1) Understand feature from `$ARGUMENTS` and existing patterns.
2) Update templates/partials in `backend/templates/` (partials `_*.html`).
3) Add/adjust islands in `backend/static/src/components/islands/` and register in `backend/static/src/islands.tsx`; use `data-island` + JSON props.
4) Use shadcn/ui primitives in `backend/static/src/components/ui/`.
5) Rebuild static assets and note usage.

Output
- Summary, files changed (templates/islands/ui), build result, how to trigger/use.
