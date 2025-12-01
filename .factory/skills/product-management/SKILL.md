name: product-management
description: This skill should be used when the user asks to "write a PRD", "analyze a feature request", "plan the roadmap", "prioritize features", or needs help with product management.
Product planning support. **Use sequentialThinking.**

Context: network automation platform (inventory, commands, configs, compliance, jobs, realtime updates). Personas: operator (run jobs), admin/architect (configure), viewer/NOC/Sec (read-only insights).

RICE: Score = (Reach × Impact × Confidence) / Effort; Impact scale 0.25–3; Effort in engineer-weeks.

PRD skeleton: Problem → Goals/Metrics → User stories (P0/P1/P2) → Requirements (functional/non-functional) → Technical notes (models/APIs/tasks/UI) → Risks/Mitigations → Launch/rollout.
Roadmap: Now (0-6w) committed, Next (6-12w) high-confidence, Later (12+w) themes.
Guardrails: AI suggests, humans decide; validate feasibility/security; call out auth/credential risks. See `references/prd-template.md` for template.
