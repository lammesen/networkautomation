RBAC + audit quick patterns
===========================
- Roles: viewer = read-only; operator = read + create/run jobs; admin = full CRUD.
- APIs: `permission_classes = [IsAuthenticated, RolePermission, ObjectCustomerPermission]`, set `customer_field`, scope querysets to customer.
- HTMX views: inherit TenantScopedView; use `filter_by_customer()`, `ensure_can_write()`, `ensure_customer_access(customer_id)` before mutations.
- Auditing: favor JobService for queued work (captures user/customer/status/logs); log admin actions with user + customer + payload summary (no secrets).
- Safety: no cross-tenant data, no raw IDs from other customers, avoid storing credentials in logs.
