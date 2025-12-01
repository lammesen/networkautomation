description: Build DRF viewsets/serializers or Celery tasks
argument-hint: <feature-description>
---
Delegate to `api-developer` via Task. `$ARGUMENTS` describes the feature.
Rules: use `CustomerScopedQuerysetMixin`, `permission_classes = [IsAuthenticated, RolePermission]`, type hints.
Paths: serializers `backend/webnet/api/serializers.py`, viewsets `backend/webnet/api/views.py`, tasks `backend/webnet/jobs/tasks.py`, urls `backend/webnet/api/urls.py`.
After: `make backend-lint && make backend-test`.
