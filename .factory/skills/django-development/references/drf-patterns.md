DRF quick patterns (token-light)
================================
- Scope: use CustomerScopedQuerysetMixin, set customer_field, permission_classes = [IsAuthenticated, RolePermission]; add ObjectCustomerPermission when object checks are needed.
- Querysets: prefer select_related/prefetch_related; define filterset_fields/search_fields/ordering_fields where useful.
- Serializers: ModelSerializer with read_only_fields; use validate_* and validate; keep create/update typed; use SerializerMethodField only when required.
- Actions: @action(detail=..., methods=[...]) with explicit serializer_class; return Response with status; raise ValidationError for bad input.
- Time/Security: always timezone.now(), no raw SQL, never expose secrets or passwords.
- Pagination: rely on project defaults unless endpoint needs streaming/large exports.
