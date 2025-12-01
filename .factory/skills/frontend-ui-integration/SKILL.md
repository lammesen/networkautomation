name: frontend-ui-integration
description: This skill should be used when the user asks to "add a page", "create a template", "build a UI component", "add HTMX partial", "create React island", "style with Tailwind", or needs frontend implementation.
Frontend integration for HTMX (95%) + React islands (5%) + shadcn/ui. **Use sequentialThinking.**

Paths: templates `backend/templates/` (partials `_*.html`), islands `backend/static/src/components/islands/`, shadcn `backend/static/src/components/ui/`, CSS `backend/static/src/input.css`.

HTMX pattern: `<div hx-get="{% url 'partial' %}" hx-trigger="load" hx-swap="innerHTML"></div>`; partials render tables/cards for swaps.
Island pattern: component in `components/islands`, register in `backend/static/src/islands.tsx` as `const islands = { MyIsland: () => import("./components/islands/MyIsland") };`, use `<div data-island="MyIsland" data-props='{{ json }}'></div>`.
Use shadcn MCP to search/add components. Build static assets with `make backend-build-static` (then lint/test as needed). Keep UI accessible; prefer HTMX over islands unless interactivity demands JS.
See `references/shadcn-patterns.md` and `references/design-guidelines.md` for quick patterns.
