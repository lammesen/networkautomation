# Multi-Tenancy Patterns

This guide covers multi-tenancy implementation patterns, tenant scoping, and security considerations in the webnet application.

## Table of Contents
- [Overview](#overview)
- [Tenant Scoping Mixins](#tenant-scoping-mixins)
- [DRF ViewSet Patterns](#drf-viewset-patterns)
- [Django View Patterns](#django-view-patterns)
- [Permission Classes](#permission-classes)
- [Common Patterns](#common-patterns)
- [Testing Tenant Isolation](#testing-tenant-isolation)
- [Common Pitfalls](#common-pitfalls)

## Overview

### Architecture
- **Tenant Model**: `Customer` (`webnet.customers.models.Customer`)
- **User-Tenant Relationship**: Many-to-Many (`User.customers`)
- **Data Scoping**: All models have `customer` ForeignKey
- **Admin Override**: Admins see all customers; non-admins see only assigned customers

### Key Principles
1. **Always scope queries** by customer unless admin
2. **Validate customer access** before operations
3. **Use mixins** for automatic scoping
4. **Test tenant isolation** thoroughly

## Tenant Scoping Mixins

### CustomerScopedQuerysetMixin (DRF)

For DRF viewsets, use `CustomerScopedQuerysetMixin`:

```python
from webnet.api.permissions import CustomerScopedQuerysetMixin
from rest_framework import viewsets

class DeviceViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    permission_classes = [IsAuthenticated, RolePermission]
    customer_field = "customer_id"  # Field to filter on
```

### Setting customer_field

**Direct field:**
```python
customer_field = "customer_id"  # Simple case
```

**Nested field (for related models):**
```python
customer_field = ("policy__customer_id", "device__customer_id")  # Multiple paths
```

**Example: ComplianceResult scoping**
```python
class ComplianceResultViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = ComplianceResult.objects.all()
    customer_field = ("policy__customer_id", "device__customer_id")
    # Filters by either policy's customer or device's customer
```

### TenantScopedView (Django Views)

For Django template views, use `TenantScopedView`:

```python
from webnet.ui.views import TenantScopedView

class DeviceListView(TenantScopedView):
    template_name = "devices/list.html"
    customer_field = "customer_id"
    
    def get(self, request):
        devices = self.filter_by_customer(Device.objects.all())
        return render(request, self.template_name, {"devices": devices})
```

## DRF ViewSet Patterns

### Basic ViewSet
```python
from webnet.api.permissions import (
    CustomerScopedQuerysetMixin,
    RolePermission,
    ObjectCustomerPermission
)
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

class DeviceViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    permission_classes = [
        IsAuthenticated,
        RolePermission,
        ObjectCustomerPermission  # For object-level checks
    ]
    customer_field = "customer_id"
```

### Custom Actions
Always scope custom actions:

```python
class CustomerViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated, RolePermission]
    
    @action(detail=True, methods=["get", "post"], url_path="ranges")
    def ranges(self, request, pk=None):
        customer = self.get_object()  # Already scoped by mixin
        
        if request.method == "GET":
            ranges = CustomerIPRange.objects.filter(customer_id=pk)
            return Response(CustomerIPRangeSerializer(ranges, many=True).data)
        
        # POST - create range
        serializer = CustomerIPRangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(customer_id=pk)  # Explicitly set customer
        return Response(serializer.data, status=status.HTTP_201_CREATED)
```

### Resolving Customer from Request
Use `resolve_customer_for_request` for operations that need customer context:

```python
from webnet.api.permissions import resolve_customer_for_request

class CommandViewSet(viewsets.ViewSet):
    @action(detail=False, methods=["post"])
    def run(self, request):
        customer = resolve_customer_for_request(request)
        if not customer:
            return Response(
                {"detail": "Customer required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Use customer for job creation
        job = JobService().create_job(
            job_type="run_commands",
            user=request.user,
            customer=customer,
            # ...
        )
```

## Django View Patterns

### Using TenantScopedView
```python
from webnet.ui.views import TenantScopedView

class DeviceListView(TenantScopedView):
    template_name = "devices/list.html"
    customer_field = "customer_id"
    allowed_write_roles = {"operator", "admin"}
    
    def get(self, request):
        # Automatic scoping
        devices = self.filter_by_customer(Device.objects.all())
        
        # Apply filters
        search = request.GET.get("search", "")
        if search:
            devices = devices.filter(hostname__icontains=search)
        
        return render(request, self.template_name, {"devices": devices})
    
    def post(self, request):
        # Check write permission
        error = self.ensure_can_write()
        if error:
            return error
        
        # Validate customer access
        customer_id = request.POST.get("customer_id")
        error = self.ensure_customer_access(customer_id)
        if error:
            return error
        
        # Create device
        form = DeviceForm(request.POST, user=request.user)
        if form.is_valid():
            device = form.save()
            return redirect("devices-detail", pk=device.id)
        
        return render(request, self.template_name, {"form": form})
```

### Form Queryset Filtering
Filter form querysets by customer:

```python
class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = ["customer", "hostname", "credential"]
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        
        if user and getattr(user, "role", "viewer") != "admin":
            # Limit to user's customers
            self.fields["customer"].queryset = user.customers.all()
            self.fields["credential"].queryset = Credential.objects.filter(
                customer__in=user.customers.all()
            )
        else:
            # Admin sees all
            self.fields["customer"].queryset = Customer.objects.all()
            self.fields["credential"].queryset = Credential.objects.all()
```

## Permission Classes

### RolePermission
Enforces role-based access:
- **viewer**: Read-only (GET, HEAD, OPTIONS)
- **operator**: Read + POST (can create jobs/actions)
- **admin**: Full access

```python
permission_classes = [IsAuthenticated, RolePermission]
```

### ObjectCustomerPermission
Object-level customer ownership check:

```python
permission_classes = [
    IsAuthenticated,
    RolePermission,
    ObjectCustomerPermission  # Validates customer access per object
]
```

### Manual Permission Checks
```python
from webnet.api.permissions import user_has_customer_access

def my_view(request, device_id):
    device = get_object_or_404(Device, pk=device_id)
    
    # Check customer access
    if not user_has_customer_access(request.user, device.customer_id):
        return Response(
            {"detail": "Access denied"}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Proceed with operation
```

## Common Patterns

### Creating Tenant-Scoped Objects
Always set customer explicitly:

```python
# In serializer
class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ["hostname", "mgmt_ip", "customer"]
    
    def create(self, validated_data):
        # Customer should be validated by viewset mixin
        return super().create(validated_data)

# In viewset
class DeviceViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    def perform_create(self, serializer):
        # Get customer from request or user's single customer
        customer = resolve_customer_for_request(self.request)
        if customer:
            serializer.save(customer=customer)
        else:
            serializer.save()
```

### Filtering Related Objects
```python
# Get devices for a customer
devices = Device.objects.filter(customer_id=customer_id)

# Get jobs for customer's devices
jobs = Job.objects.filter(customer_id=customer_id)

# Get compliance results for customer's policies
results = ComplianceResult.objects.filter(
    policy__customer_id=customer_id
)
```

### Aggregations with Tenant Scoping
```python
from django.db.models import Count

# Device counts per customer (for admin)
device_counts = Device.objects.values('customer__name').annotate(
    count=Count('id')
)

# For non-admin, filter first
devices = self.filter_by_customer(Device.objects.all())
vendor_counts = devices.values('vendor').annotate(count=Count('id'))
```

### Bulk Operations
Always validate customer access for bulk operations:

```python
def bulk_delete_devices(request, device_ids):
    devices = Device.objects.filter(id__in=device_ids)
    
    # Filter by customer
    devices = self.filter_by_customer(devices)
    
    # Verify all devices belong to accessible customers
    for device in devices:
        if not user_has_customer_access(request.user, device.customer_id):
            return Response(
                {"detail": "Access denied"}, 
                status=status.HTTP_403_FORBIDDEN
            )
    
    devices.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
```

## Testing Tenant Isolation

### Test Fixture Pattern
```python
import pytest
from webnet.customers.models import Customer
from webnet.users.models import User
from webnet.devices.models import Device

@pytest.fixture
def customer1(db):
    return Customer.objects.create(name="Customer 1")

@pytest.fixture
def customer2(db):
    return Customer.objects.create(name="Customer 2")

@pytest.fixture
def admin_user(db):
    user = User.objects.create_user(
        username="admin",
        password="testpass",
        role="admin"
    )
    return user

@pytest.fixture
def operator_user(db, customer1):
    user = User.objects.create_user(
        username="operator",
        password="testpass",
        role="operator"
    )
    user.customers.add(customer1)
    return user

@pytest.fixture
def device1(db, customer1):
    return Device.objects.create(
        customer=customer1,
        hostname="device1",
        mgmt_ip="192.168.1.1",
        vendor="cisco",
        platform="ios",
        credential=credential1
    )
```

### Test Tenant Scoping
```python
def test_viewset_filters_by_customer(operator_user, customer1, customer2, device1):
    """Non-admin users only see their customer's devices."""
    # Create device for customer2 (not accessible to operator_user)
    device2 = Device.objects.create(
        customer=customer2,
        hostname="device2",
        mgmt_ip="192.168.1.2",
        vendor="cisco",
        platform="ios",
        credential=credential2
    )
    
    # Authenticate as operator
    client = APIClient()
    client.force_authenticate(user=operator_user)
    
    # Request devices
    response = client.get("/api/v1/devices/")
    
    # Should only see device1 (customer1), not device2
    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]["hostname"] == "device1"
```

### Test Cross-Tenant Access Prevention
```python
def test_cannot_access_other_customer_device(operator_user, customer2, device2):
    """Users cannot access devices from other customers."""
    client = APIClient()
    client.force_authenticate(user=operator_user)
    
    # Try to access device2 (belongs to customer2)
    response = client.get(f"/api/v1/devices/{device2.id}/")
    
    # Should be 404 (not found) or 403 (forbidden)
    assert response.status_code in [404, 403]
```

### Test Admin Sees All
```python
def test_admin_sees_all_customers(admin_user, customer1, customer2, device1, device2):
    """Admin users see all customers' data."""
    client = APIClient()
    client.force_authenticate(user=admin_user)
    
    response = client.get("/api/v1/devices/")
    
    # Admin should see both devices
    assert response.status_code == 200
    assert len(response.data) == 2
    hostnames = [d["hostname"] for d in response.data]
    assert "device1" in hostnames
    assert "device2" in hostnames
```

## Common Pitfalls

### ❌ Forgetting to Set customer_field
```python
# BAD: Missing customer_field
class DeviceViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Device.objects.all()
    # Missing: customer_field = "customer_id"
```

**Fix:**
```python
class DeviceViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Device.objects.all()
    customer_field = "customer_id"  # Required!
```

### ❌ Not Filtering Form Querysets
```python
# BAD: Form shows all customers
class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = ["customer"]
    # Missing customer filtering in __init__
```

**Fix:**
```python
class DeviceForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user and user.role != "admin":
            self.fields["customer"].queryset = user.customers.all()
```

### ❌ Manual Queries Without Scoping
```python
# BAD: Direct query without scoping
def my_view(request):
    devices = Device.objects.all()  # Shows all customers!
    return render(request, "template.html", {"devices": devices})
```

**Fix:**
```python
def my_view(request):
    devices = self.filter_by_customer(Device.objects.all())
    return render(request, "template.html", {"devices": devices})
```

### ❌ Creating Objects Without Customer
```python
# BAD: Missing customer assignment
def create_device(request):
    device = Device.objects.create(
        hostname="router1",
        mgmt_ip="192.168.1.1"
        # Missing: customer=...
    )
```

**Fix:**
```python
def create_device(request):
    customer = resolve_customer_for_request(request)
    device = Device.objects.create(
        customer=customer,  # Required!
        hostname="router1",
        mgmt_ip="192.168.1.1"
    )
```

### ❌ Nested Field Scoping
```python
# BAD: Wrong customer_field for nested relationship
class ComplianceResultViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    customer_field = "customer_id"  # Wrong! ComplianceResult doesn't have customer_id
```

**Fix:**
```python
class ComplianceResultViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    customer_field = ("policy__customer_id", "device__customer_id")  # Correct nested paths
```

## Security Checklist

- [ ] All viewsets use `CustomerScopedQuerysetMixin` or `TenantScopedView`
- [ ] `customer_field` is set correctly (including nested paths)
- [ ] Form querysets are filtered by customer
- [ ] Object creation validates customer access
- [ ] Bulk operations check customer access for each item
- [ ] Custom actions scope queries properly
- [ ] Tests verify tenant isolation
- [ ] Admin override works correctly
- [ ] No direct queries bypass scoping mixins

## References

- `webnet/api/permissions.py` - Permission classes and mixins
- `webnet/ui/views.py` - TenantScopedView implementation
- `webnet/tests/test_rbac_scoping.py` - Tenant isolation tests
