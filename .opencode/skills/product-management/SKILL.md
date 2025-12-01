---
name: product-management
description: Use for PRDs, feature analysis, prioritization, and roadmap planning for webnet.
license: MIT
---

# Product Management (webnet)

Purpose: produce concise PRDs, evaluations, and roadmaps for webnet features with network-automation awareness.

Rules
- ALWAYS run sequentialThinking before drafting.
- Ground recommendations in webnet architecture and constraints.

When to use
- PRDs, feature request analysis, prioritization (RICE), roadmap updates, decision records.

Context
- Platform: multi-tenant automation (inventory, commands/jobs, config backup/diff/deploy, compliance, WebSocket updates).
- Personas: engineer/operator (run tasks), architect/admin (policies/inventory), NOC viewer (monitor), security analyst (audit).

Outputs (pick as needed)
- PRD (problem, goals/metrics, user stories, requirements, tech impact, risks, rollout)
- Feature analysis (RICE score + recommendation)
- One-pager/exec summary
- Roadmap entry (Now/Next/Later)
- Decision log

RICE quick ref
- Score = (Reach × Impact × Confidence) / Effort
- Impact guide: 3 massive (new workflow), 2 high (big time saver), 1 medium, 0.5 low, 0.25 minimal.
- Effort factors: model+migration (+1w), Celery task (+0.5w), React island (+1w), NAPALM/Netmiko (+2w), multi-tenant (+0.5w), WebSocket (+1w).

Checklists
- PRD: pain point + data, success metrics, user stories by persona, architecture impact (models/API/tasks/UI), risks/mitigations, phased rollout/flags, stakeholders.
- Feature analysis: clarify problem/persona, estimate RICE, align to strategy, note technical complexity/deps.

Safety
- AI advises; human owns decisions.
- Validate feasibility with engineering/security; consider tenant isolation and credential handling.

References: `docs/architecture.md`, `docs/operations.md`, `.opencode/agent/` for feasibility.
