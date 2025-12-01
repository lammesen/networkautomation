# Documentation Index

Welcome to the documentation for the Network Automation platform. This index is organized by audience: Users (operators), Developers, and Maintainers/Operators. Each section links to focused guides and deeper reference material.

## Users (Operators)
- Start here: [User Guide](./user-guide.md)
- Day‑to‑day operations: [Operations Guide](./operations.md)
- Common workflows: [Workflows](./workflows.md)
- Troubleshooting: [Troubleshooting](./troubleshooting.md)

## Developers
- Start here: [Developer Guide](./developer-guide.md)
- Architecture overview: [Architecture](./architecture.md) (legacy; see Developer Guide for the current Django/HTMX stack)
- API development: [API Development](./api-development.md)
- API endpoints: [API Reference](./api-reference.md)
- Multi‑tenancy & RBAC: [Multi‑tenancy](./multi-tenancy.md)
- UI patterns: [HTMX Patterns](./htmx-patterns.md) · [React Islands](./react-islands.md)
- Models quick reference: [Models Reference](./models-reference.md)
- Streaming & WebSockets: [SSH Streaming](./ssh-streaming.md)
- Testing strategy: [Testing](./testing.md)
- Performance tips: [Performance](./performance.md)
- Useful snippets: [Snippets](./snippets.md)

## Maintainers / Operators (SRE/Platform)
- Start here: [Maintainers Guide](./maintainers.md)
- Deployment (Kubernetes & Compose): [Deployment](./deployment.md)
- Operations runbook: [Operations Guide](./operations.md)
- Security hardening: [Security](./security.md)
- Performance & scaling: [Performance](./performance.md)

## Doc Status & Notes

- The project migrated from a FastAPI/React architecture to a Django + HTMX backend with small React Islands. Some documents still reference the legacy stack. When in doubt, prefer the latest: [Developer Guide](./developer-guide.md) and [User Guide](./user-guide.md).
- If you find inconsistencies, open an issue or PR. See [CONTRIBUTING](../CONTRIBUTING.md).

## Quick Links
- Root README: [/README.md](../README.md)
- Makefile commands: [/Makefile](../Makefile)
- Kubernetes manifests: [/k8s](../k8s)
- Backend project: [/backend/webnet](../backend/webnet)
