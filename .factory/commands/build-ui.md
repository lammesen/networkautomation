description: Build HTMX templates, React islands, or shadcn components
argument-hint: <feature-description>
---
Delegate to `ui-builder` via Task. `$ARGUMENTS` = feature.
Paths: templates `backend/templates/`, islands `backend/static/src/components/islands/`, shadcn `backend/static/src/components/ui/`.
Process: reuse patterns, use shadcn MCP if needed, register islands in `backend/static/src/islands.tsx`, then `make backend-build-static`.
