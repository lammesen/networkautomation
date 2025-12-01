name: service-integration
description: This skill should be used when the user asks to "add an API endpoint", "create a DRF viewset", "add a Celery task", "add WebSocket consumer", or needs to extend backend services.
Extend backend APIs, Celery tasks, and WebSockets. **Use sequentialThinking.**

Paths: serializers/views/urls in `webnet/api/`; tasks in `webnet/jobs/tasks.py`; consumers in `webnet/api/consumers.py`; broadcasts in `webnet/core/broadcasts.py`.

API action pattern:
```python
class MyActionSerializer(serializers.Serializer): target_ids = serializers.ListField(child=serializers.IntegerField())
@action(detail=False, methods=["post"])
def my_action(self, request):
    s = MyActionSerializer(data=request.data); s.is_valid(raise_exception=True)
    return Response({"job_id": job.id}, status=201)
```

Celery pattern: update JobService status/logs, catch exceptions, keep type hints. Broadcast changes with `broadcast_entity_update`/`broadcast_job_update`.

Requirements: `CustomerScopedQuerysetMixin`, `permission_classes = [IsAuthenticated, RolePermission]`, set `customer_field`, run `make backend-lint && make backend-test`. See `references/integration-patterns.md`.
