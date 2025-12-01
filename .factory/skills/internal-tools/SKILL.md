name: internal-tools
description: This skill should be used when the user asks to "build an admin panel", "create a dashboard", "add operator tools", "implement job tracking", "add audit logging", or needs RBAC/multi-tenancy features.
Internal tools with RBAC + tenancy. **Use sequentialThinking.**

RBAC: viewer=read-only, operator=read+job create, admin=full. Apply `permission_classes = [IsAuthenticated, RolePermission, ObjectCustomerPermission]` and set `customer_field` on viewsets; HTMX views inherit TenantScopedView helpers (`filter_by_customer`, `ensure_can_write`, `ensure_customer_access`).

JobService usage:
```python
job = JobService().create_job(job_type="run_commands", user=request.user, customer=customer,
    target_summary={"device_count": len(device_ids)}, payload={"device_ids": device_ids, "commands": commands})
JobService().enqueue(job)
```
Broadcast updates with `broadcast_job_update` / `broadcast_entity_update` for realtime UI.

Guardrails: always scope by customer, keep audit trail via JobService, never expose credentials, add dry-run for destructive flows. See `references/rbac-audit-patterns.md` for patterns.
