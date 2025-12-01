name: django-development
description: This skill should be used when the user asks to "add a model", "create a migration", "build a view", "add a serializer", "configure settings", or needs Django ORM/DRF help.
Django/DRF implementation. **Use sequentialThinking.**

Paths: models `webnet/{app}/models.py`; serializers `webnet/api/serializers.py`; viewsets `webnet/api/views.py`; urls `webnet/api/urls.py`; permissions `webnet/api/permissions.py`; tests `webnet/tests/`.

Model sketch:
```python
class MyModel(models.Model):
    customer = models.ForeignKey("customers.Customer", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ("customer", "name")
        indexes = [models.Index(fields=["customer"])]
```

ViewSet sketch (tenant + RBAC):
```python
class MyViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = MyModel.objects.select_related("customer")
    serializer_class = MySerializer
    permission_classes = [IsAuthenticated, RolePermission]
    customer_field = "customer_id"
    def perform_create(self, serializer: MySerializer) -> None:
        serializer.save(customer=self.get_customer())
```
Use `select_related/prefetch_related` for perf. Migrations: `cd backend && ../backend/venv/bin/python manage.py makemigrations && ../backend/venv/bin/python manage.py migrate`. Verify: `make backend-lint` and `make backend-test`. See `references/orm-patterns.md` and `references/drf-patterns.md` for details.
