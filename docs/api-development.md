# API Development Guide

Complete guide for developing REST API endpoints using Django REST Framework (DRF) in the webnet application.

## Table of Contents
- [ViewSet Patterns](#viewset-patterns)
- [Serializer Patterns](#serializer-patterns)
- [Permission Classes](#permission-classes)
- [Custom Actions](#custom-actions)
- [Filtering and Pagination](#filtering-and-pagination)
- [Error Handling](#error-handling)
- [Testing APIs](#testing-apis)
- [Best Practices](#best-practices)

## ViewSet Patterns

### Basic ModelViewSet
```python
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from webnet.api.permissions import (
    CustomerScopedQuerysetMixin,
    RolePermission,
    ObjectCustomerPermission
)
from webnet.devices.models import Device
from .serializers import DeviceSerializer

class DeviceViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    permission_classes = [
        IsAuthenticated,
        RolePermission,
        ObjectCustomerPermission
    ]
    customer_field = "customer_id"
```

### ReadOnlyViewSet
```python
class DeviceReadOnlyViewSet(CustomerScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    permission_classes = [IsAuthenticated, RolePermission]
    customer_field = "customer_id"
```

### ViewSet (Custom Actions Only)
```python
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

class CommandViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, RolePermission]
    
    @action(detail=False, methods=["post"])
    def run(self, request):
        # Custom action logic
        return Response({"status": "ok"})
```

## Serializer Patterns

### Basic ModelSerializer
```python
from rest_framework import serializers
from webnet.devices.models import Device

class DeviceSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(
        source="customer.name",
        read_only=True
    )
    
    class Meta:
        model = Device
        fields = [
            "id",
            "hostname",
            "mgmt_ip",
            "vendor",
            "platform",
            "customer",
            "customer_name",
            "created_at"
        ]
        read_only_fields = ["id", "created_at"]
```

### Nested Serializer
```python
class CredentialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Credential
        fields = ["id", "name", "username"]

class DeviceSerializer(serializers.ModelSerializer):
    credential_detail = CredentialSerializer(
        source="credential",
        read_only=True
    )
    
    class Meta:
        model = Device
        fields = ["id", "hostname", "credential", "credential_detail"]
```

### Write-Only Fields
```python
class CredentialSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    enable_password = serializers.CharField(
        write_only=True,
        allow_null=True,
        required=False
    )
    
    class Meta:
        model = Credential
        fields = ["id", "name", "username", "password", "enable_password"]
    
    def create(self, validated_data):
        password = validated_data.pop("password")
        enable_password = validated_data.pop("enable_password", None)
        cred = Credential(**validated_data)
        cred.password = password
        if enable_password:
            cred.enable_password = enable_password
        cred.save()
        return cred
```

### Custom Validation
```python
class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ["hostname", "mgmt_ip", "customer"]
    
    def validate_hostname(self, value):
        if not value:
            raise serializers.ValidationError("Hostname required")
        # Check uniqueness within customer
        customer_id = self.initial_data.get("customer")
        if customer_id and Device.objects.filter(
            customer_id=customer_id,
            hostname=value
        ).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise serializers.ValidationError("Hostname already exists")
        return value
    
    def validate(self, data):
        # Cross-field validation
        if data.get("vendor") == "cisco" and not data.get("platform"):
            raise serializers.ValidationError(
                "Platform required for Cisco devices"
            )
        return data
```

### Dynamic Serializer Selection
```python
class UserViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated, RolePermission]
    
    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer
```

## Permission Classes

### Standard Permissions
```python
from rest_framework.permissions import IsAuthenticated
from webnet.api.permissions import RolePermission, ObjectCustomerPermission

permission_classes = [
    IsAuthenticated,
    RolePermission,
    ObjectCustomerPermission
]
```

### RolePermission Behavior
- **viewer**: Read-only (GET, HEAD, OPTIONS)
- **operator**: Read + POST (can create jobs/actions)
- **admin**: Full access (all methods)

### ObjectCustomerPermission
Validates customer access at object level:

```python
class DeviceViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    permission_classes = [
        IsAuthenticated,
        RolePermission,
        ObjectCustomerPermission  # Validates customer access
    ]
```

## Custom Actions

### Detail Action
```python
class DeviceViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    @action(detail=True, methods=["post"])
    def enable(self, request, pk=None):
        device = self.get_object()
        device.enabled = True
        device.save()
        return Response(DeviceSerializer(device).data)
```

### Collection Action
```python
class DeviceViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    @action(detail=False, methods=["post"], url_path="bulk-backup")
    def bulk_backup(self, request):
        device_ids = request.data.get("device_ids", [])
        devices = self.get_queryset().filter(pk__in=device_ids)
        
        # Create backup jobs
        jobs = []
        for device in devices:
            job = create_backup_job(device)
            jobs.append(job.id)
        
        return Response({"jobs": jobs}, status=status.HTTP_202_ACCEPTED)
```

### Action with URL Parameters
```python
class CustomerViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    @action(
        detail=True,
        methods=["post"],
        url_path="users/(?P<user_id>[^/.]+)"
    )
    def add_user(self, request, pk=None, user_id=None):
        customer = self.get_object()
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        customer.users.add(user)
        return Response(status=status.HTTP_204_NO_CONTENT)
```

### GET/POST Action
```python
class CustomerViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    @action(detail=True, methods=["get", "post"], url_path="ranges")
    def ranges(self, request, pk=None):
        if request.method == "GET":
            ranges = CustomerIPRange.objects.filter(customer_id=pk)
            return Response(
                CustomerIPRangeSerializer(ranges, many=True).data
            )
        
        # POST
        serializer = CustomerIPRangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(customer_id=pk)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
```

## Filtering and Pagination

### Query Parameter Filtering
```python
class DeviceViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    def get_queryset(self):
        qs = super().get_queryset()
        
        # Filter by query parameters
        vendor = self.request.query_params.get("vendor")
        if vendor:
            qs = qs.filter(vendor=vendor)
        
        site = self.request.query_params.get("site")
        if site:
            qs = qs.filter(site=site)
        
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(hostname__icontains=search) |
                Q(mgmt_ip__icontains=search)
            )
        
        return qs
```

### Pagination
```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50
}

# In ViewSet
class DeviceViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    pagination_class = PageNumberPagination
    page_size = 25
```

## Error Handling

### Standard Error Responses
```python
from rest_framework import status
from rest_framework.response import Response

# 400 Bad Request
return Response(
    {"detail": "Invalid data"},
    status=status.HTTP_400_BAD_REQUEST
)

# 403 Forbidden
return Response(
    {"detail": "Access denied"},
    status=status.HTTP_403_FORBIDDEN
)

# 404 Not Found
return Response(
    {"detail": "Resource not found"},
    status=status.HTTP_404_NOT_FOUND
)
```

### Validation Errors
```python
serializer = DeviceSerializer(data=request.data)
if not serializer.is_valid():
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
```

### Custom Exception Handling
```python
from rest_framework.views import exception_handler

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    
    if response is not None:
        custom_response_data = {
            "error": {
                "status_code": response.status_code,
                "message": response.data.get("detail", "An error occurred"),
                "details": response.data
            }
        }
        response.data = custom_response_data
    
    return response
```

## Testing APIs

### Basic Test
```python
from rest_framework.test import APIClient
from rest_framework import status

def test_list_devices(operator_user, device1):
    client = APIClient()
    client.force_authenticate(user=operator_user)
    
    response = client.get("/api/v1/devices/")
    
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]["hostname"] == device1.hostname
```

### Create Test
```python
def test_create_device(operator_user, customer1, credential1):
    client = APIClient()
    client.force_authenticate(user=operator_user)
    
    response = client.post("/api/v1/devices/", {
        "customer": customer1.id,
        "hostname": "new-router",
        "mgmt_ip": "192.168.1.10",
        "vendor": "cisco",
        "platform": "ios",
        "credential": credential1.id
    })
    
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["hostname"] == "new-router"
```

### Custom Action Test
```python
def test_enable_device(operator_user, device1):
    client = APIClient()
    client.force_authenticate(user=operator_user)
    
    response = client.post(f"/api/v1/devices/{device1.id}/enable/")
    
    assert response.status_code == status.HTTP_200_OK
    device1.refresh_from_db()
    assert device1.enabled is True
```

## Best Practices

### 1. Always Use Tenant Scoping
```python
# ✅ Good
class DeviceViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    customer_field = "customer_id"

# ❌ Bad
class DeviceViewSet(viewsets.ModelViewSet):
    # Missing tenant scoping
```

### 2. Use select_related/prefetch_related
```python
# ✅ Good - reduces queries
queryset = Device.objects.select_related("customer", "credential")

# ❌ Bad - N+1 queries
queryset = Device.objects.all()
```

### 3. Validate Customer Access
```python
# ✅ Good
from webnet.api.permissions import resolve_customer_for_request

customer = resolve_customer_for_request(request)
if not customer:
    return Response(
        {"detail": "Customer required"},
        status=status.HTTP_400_BAD_REQUEST
    )

# ❌ Bad - no validation
customer_id = request.data.get("customer_id")
```

### 4. Use Appropriate HTTP Methods
- GET: Read operations
- POST: Create operations, actions
- PUT/PATCH: Update operations
- DELETE: Delete operations

### 5. Return Appropriate Status Codes
- 200: Success (GET, PUT, PATCH)
- 201: Created (POST create)
- 202: Accepted (async operations)
- 204: No Content (DELETE)
- 400: Bad Request (validation errors)
- 401: Unauthorized (authentication required)
- 403: Forbidden (permission denied)
- 404: Not Found
- 500: Internal Server Error

### 6. Document Custom Actions
```python
@action(
    detail=False,
    methods=["post"],
    url_path="bulk-backup",
    description="Queue config backup jobs for multiple devices"
)
def bulk_backup(self, request):
    """Queue config backup jobs for multiple devices."""
    pass
```

## References

- [DRF Documentation](https://www.django-rest-framework.org/)
- [Multi-Tenancy Patterns](./multi-tenancy.md)
- [Testing Guide](./testing.md)
- [Code Snippets](./snippets.md#drf-serializers)
