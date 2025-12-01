Design quick notes (token-light)
================================
- Keep layouts clean: generous spacing, single column on mobile, avoid noisy borders.
- Typography: reuse project font stack; stick to a small scale (xs, sm, base, lg) and consistent weights.
- Color: follow existing theme neutrals; use clear accents for primary, destructive, success, warning; ensure contrast.
- Components: prefer shadcn primitives with consistent padding/radius/shadow; avoid custom ad-hoc styles when utilities work.
- Motion: light transitions on hover/focus/loading; avoid distracting animations; respect reduced-motion.
- Accessibility: visible focus, keyboard navigation, aria-labels for icons, sufficient hit areas.
- HTMX/Islands: partials named `_*.html`; islands only for complex interactivity.
