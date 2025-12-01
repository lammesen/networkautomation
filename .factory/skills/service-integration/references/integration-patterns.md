Integration quick patterns
==========================
- APIs: ViewSets use CustomerScopedQuerysetMixin, set customer_field, permission_classes = [IsAuthenticated, RolePermission]; validate with serializers; use select_related/prefetch_related.
- Celery: use @shared_task or celery_app.task(bind=True); load Job via JobService, set_status running/success/failed, append_log for progress; include customer_id in payload; catch exceptions.
- WebSockets: consumers live in `webnet/api/consumers.py`; scope connections by customer; send structured events.
- Broadcasts: `broadcast_entity_update(entity, action, entity_id, customer_id)` and `broadcast_job_update(job, action="updated")` for UI refresh.
- Safety: no secrets in logs, keep type hints, prefer ORM over raw SQL.
