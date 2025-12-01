# Common Workflows

This guide covers common development workflows and step-by-step procedures for adding features to the webnet application.

## Table of Contents
- [Adding a New Device Type](#adding-a-new-device-type)
- [Creating a New Job Type](#creating-a-new-job-type)
- [Adding a New API Endpoint](#adding-a-new-api-endpoint)
- [Creating a New HTMX Page](#creating-a-new-htmx-page)
- [Adding a React Island Component](#adding-a-react-island-component)
- [Creating a New Compliance Check](#creating-a-new-compliance-check)
- [Adding a New Model](#adding-a-new-model)

## Adding a New Device Type

### 1. Update Vendor/Platform Mapping

If the device type requires special handling, update the automation inventory:

```python
# backend/webnet/automation.py or similar
VENDOR_PLATFORM_MAP = {
    "cisco": {
        "ios": "napalm_ios",
        "iosxe": "napalm_ios",
        "nxos": "napalm_nxos",
    },
    "juniper": {
        "junos": "napalm_junos",
    },
    "arista": {
        "eos": "napalm_eos",
    },
    # Add your new vendor/platform
    "newvendor": {
        "newplatform": "napalm_driver_name",
    },
}
```

### 2. Test Device Connection

Test with a real device or simulator:

```python
# In Django shell
from webnet.automation import build_inventory
from nornir.core import Nornir

inventory = build_inventory(
    targets={"vendor": "newvendor", "platform": "newplatform"},
    customer_id=1
)
nr = Nornir(inventory=inventory)
result = nr.run(task=some_task)
```

### 3. Update Device Form (if needed)

If the new platform requires additional fields:

```python
# backend/webnet/ui/views.py
class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = [
            "customer",
            "hostname",
            "mgmt_ip",
            "vendor",
            "platform",  # New platform should appear in dropdown
            "role",
            "site",
            "credential",
        ]
```

### 4. Add Tests

```python
# backend/webnet/tests/test_devices.py
def test_newvendor_device_connection(db, customer1, credential1):
    device = Device.objects.create(
        customer=customer1,
        hostname="test-device",
        mgmt_ip="192.168.1.1",
        vendor="newvendor",
        platform="newplatform",
        credential=credential1
    )
    
    # Test inventory building
    inventory = build_inventory({"id": device.id}, customer_id=customer1.id)
    assert len(inventory.hosts) == 1
    assert inventory.hosts[device.hostname]["platform"] == "newplatform"
```

## Creating a New Job Type

### 1. Add Job Type to Model

```python
# backend/webnet/jobs/models.py
class Job(models.Model):
    TYPE_CHOICES = (
        ("run_commands", "Run commands"),
        ("config_backup", "Config backup"),
        # ... existing types
        ("new_job_type", "New Job Type"),  # Add here
    )
    # ...
```

### 2. Create Celery Task

```python
# backend/webnet/jobs/tasks.py
from celery import shared_task
from webnet.jobs.models import Job
from webnet.jobs.services import JobService
from webnet.automation import build_inventory

@shared_task(name="new_job_type_job")
def new_job_type_job(job_id: int, targets: dict, **kwargs) -> None:
    """Execute new job type."""
    js = JobService()
    try:
        job = Job.objects.get(pk=job_id)
    except Job.DoesNotExist:
        logger.warning("Job %s not found", job_id)
        return
    
    js.set_status(job, "running")
    
    # Build inventory
    inventory = build_inventory(targets, customer_id=job.customer_id)
    if not inventory.hosts:
        js.append_log(job, level="ERROR", message="No devices matched targets")
        js.set_status(job, "failed", result_summary={"error": "no devices"})
        return
    
    # Execute task logic
    try:
        # Your task implementation here
        result = execute_new_task(inventory, **kwargs)
        
        js.set_status(job, "success", result_summary=result)
    except Exception as exc:
        js.append_log(job, level="ERROR", message=str(exc))
        js.set_status(job, "failed", result_summary={"error": str(exc)})
```

### 3. Add API Endpoint

```python
# backend/webnet/api/views.py
class CommandViewSet(viewsets.ViewSet):
    @action(detail=False, methods=["post"])
    def new_job_type(self, request):
        """Create and queue new job type."""
        customer = resolve_customer_for_request(request)
        if not customer:
            return Response(
                {"detail": "Customer required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        targets = request.data.get("targets", {})
        # Validate targets
        
        # Create job
        js = JobService()
        job = js.create_job(
            job_type="new_job_type",
            user=request.user,
            customer=customer,
            target_summary={"targets": targets},
            payload=request.data
        )
        
        # Queue Celery task
        from webnet.jobs.tasks import new_job_type_job
        new_job_type_job.delay(job.id, targets, **request.data)
        
        return Response(JobSerializer(job).data, status=status.HTTP_201_CREATED)
```

### 4. Add URL Route

```python
# backend/webnet/api/urls.py
router.register(r"commands", CommandViewSet, basename="commands")
# Endpoint: POST /api/v1/commands/new_job_type/
```

### 5. Add UI (Optional)

```python
# backend/webnet/ui/views.py
class NewJobTypeView(TenantScopedView):
    template_name = "jobs/new_job_type.html"
    
    def post(self, request):
        error = self.ensure_can_write()
        if error:
            return error
        
        # Create job via API or directly
        # ...
```

## Adding a New API Endpoint

### 1. Create Serializer

```python
# backend/webnet/api/serializers.py
class MyModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyModel
        fields = ["id", "name", "customer", "created_at"]
        read_only_fields = ["id", "created_at"]
```

### 2. Create ViewSet

```python
# backend/webnet/api/views.py
from webnet.api.permissions import (
    CustomerScopedQuerysetMixin,
    RolePermission,
    ObjectCustomerPermission
)
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

class MyModelViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = MyModel.objects.all()
    serializer_class = MyModelSerializer
    permission_classes = [
        IsAuthenticated,
        RolePermission,
        ObjectCustomerPermission
    ]
    customer_field = "customer_id"
```

### 3. Register URL

```python
# backend/webnet/api/urls.py
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"my-models", views.MyModelViewSet, basename="my-models")

urlpatterns = [
    # ... existing patterns
] + router.urls
```

### 4. Add Tests

```python
# backend/webnet/tests/test_my_models.py
def test_list_my_models(operator_user, customer1, my_model1):
    client = APIClient()
    client.force_authenticate(user=operator_user)
    
    response = client.get("/api/v1/my-models/")
    assert response.status_code == 200
    assert len(response.data) == 1
```

## Creating a New HTMX Page

### 1. Create Template

```html
{# backend/templates/myfeature/list.html #}
{% extends "base.html" %}
{% block title %}My Feature - webnet{% endblock %}

{% block content %}
<div class="page-header">
  <h1 class="page-title">My Feature</h1>
  <p class="page-subtitle">Description</p>
</div>

<div class="card">
  <div id="myfeature-table"
       hx-get="{% url 'myfeature-partial' %}"
       hx-trigger="load"
       hx-target="#myfeature-table"
       hx-swap="innerHTML">
    <div class="animate-pulse">Loading...</div>
  </div>
</div>
{% endblock %}
```

### 2. Create Partial Template

```html
{# backend/templates/myfeature/_table.html #}
<div class="relative w-full overflow-auto">
  <table class="table-grid">
    <thead>
      <tr class="table-head-row">
        <th class="table-head-cell">Name</th>
        <th class="table-head-cell">Status</th>
      </tr>
    </thead>
    <tbody>
      {% for item in items %}
      <tr class="table-row">
        <td class="table-cell">{{ item.name }}</td>
        <td class="table-cell">{{ item.status }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
```

### 3. Create View

```python
# backend/webnet/ui/views.py
from webnet.ui.views import TenantScopedView

class MyFeatureListView(TenantScopedView):
    template_name = "myfeature/list.html"
    partial_name = "myfeature/_table.html"
    customer_field = "customer_id"
    
    def get(self, request):
        items = self.filter_by_customer(MyModel.objects.all())
        
        # Check if HTMX partial request
        if request.headers.get('HX-Request'):
            return render(request, self.partial_name, {"items": items})
        
        return render(request, self.template_name, {"items": items})
```

### 4. Add URL

```python
# backend/webnet/ui/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("myfeature/", views.MyFeatureListView.as_view(), name="myfeature-list"),
    path("myfeature/partial/", views.MyFeatureListView.as_view(), name="myfeature-partial"),
]
```

### 5. Add Navigation (Optional)

```html
{# backend/templates/base.html - sidebar #}
<a href="{% url 'myfeature-list' %}" class="nav-link">
  My Feature
</a>
```

## Adding a React Island Component

### 1. Create Component

```tsx
// backend/static/src/components/islands/MyComponent.tsx
import * as React from "react";
import { Button } from "../ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";

interface MyComponentProps {
  items: Array<{ id: number; name: string }>;
  onAction: (id: number) => void;
}

export default function MyComponent({ items, onAction }: MyComponentProps) {
  const htmx = (window as any).htmx;
  
  const handleClick = (id: number) => {
    htmx.ajax('POST', `/api/my-action/${id}/`, {
      target: '#result',
      swap: 'innerHTML'
    });
  };
  
  return (
    <Card>
      <CardHeader>
        <CardTitle>My Component</CardTitle>
      </CardHeader>
      <CardContent>
        {items.map(item => (
          <div key={item.id}>
            {item.name}
            <Button onClick={() => handleClick(item.id)}>Action</Button>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
```

### 2. Register in Islands

```tsx
// backend/static/src/islands.tsx
import MyComponent from "./components/islands/MyComponent";

const islandComponents: Record<string, React.ComponentType<any>> = {
  // ... existing components
  MyComponent,
};
```

### 3. Use in Template

```html
{# backend/templates/myfeature/list.html #}
<div data-island="MyComponent" 
     data-props='{{ component_props_json|escapejs }}'>
</div>
```

### 4. Build JavaScript

```bash
make backend-build-js
```

## Creating a New Compliance Check

### 1. Define Policy YAML

```yaml
# Example compliance policy
- get_interfaces:
    - GigabitEthernet0/0:
        is_enabled: true
        description: "Production Link"
- get_facts:
    - os_version:
        contains: "15.1"
```

### 2. Create Policy via API

```python
# In Django shell or management command
from webnet.compliance.models import CompliancePolicy
from webnet.customers.models import Customer

policy = CompliancePolicy.objects.create(
    customer=customer,
    name="Interface Compliance",
    scope_json={"role": "edge"},
    definition_yaml="""
- get_interfaces:
    - GigabitEthernet0/0:
        is_enabled: true
"""
)
```

### 3. Run Compliance Check

```python
# Via API
POST /api/v1/compliance/run
{
    "policy_id": 1,
    "targets": {"site": "datacenter1"}
}
```

### 4. View Results

```python
# Via API
GET /api/v1/compliance/results?policy_id=1
```

## Adding a New Model

### 1. Create Model

```python
# backend/webnet/myapp/models.py
from django.db import models
from webnet.customers.models import Customer

class MyModel(models.Model):
    customer = models.ForeignKey(
        Customer, 
        on_delete=models.CASCADE, 
        related_name="mymodels"
    )
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, default="active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ("customer", "name")
        indexes = [
            models.Index(fields=["customer"]),
            models.Index(fields=["status"]),
        ]
        ordering = ["-created_at"]
    
    def __str__(self):
        return self.name
```

### 2. Create Migration

```bash
cd backend
python manage.py makemigrations myapp
python manage.py migrate
```

### 3. Create Serializer

```python
# backend/webnet/api/serializers.py
class MyModelSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(
        source="customer.name", 
        read_only=True
    )
    
    class Meta:
        model = MyModel
        fields = [
            "id", 
            "name", 
            "status", 
            "customer", 
            "customer_name",
            "created_at",
            "updated_at"
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
```

### 4. Create ViewSet

```python
# backend/webnet/api/views.py
class MyModelViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = MyModel.objects.all()
    serializer_class = MyModelSerializer
    permission_classes = [
        IsAuthenticated,
        RolePermission,
        ObjectCustomerPermission
    ]
    customer_field = "customer_id"
```

### 5. Register URLs

```python
# backend/webnet/api/urls.py
router.register(r"my-models", views.MyModelViewSet, basename="my-models")
```

### 6. Add Admin (Optional)

```python
# backend/webnet/myapp/admin.py
from django.contrib import admin
from .models import MyModel

@admin.register(MyModel)
class MyModelAdmin(admin.ModelAdmin):
    list_display = ["name", "customer", "status", "created_at"]
    list_filter = ["status", "customer"]
    search_fields = ["name"]
```

### 7. Write Tests

```python
# backend/webnet/tests/test_my_models.py
def test_create_mymodel(operator_user, customer1):
    client = APIClient()
    client.force_authenticate(user=operator_user)
    
    response = client.post("/api/v1/my-models/", {
        "name": "Test Model",
        "customer": customer1.id,
        "status": "active"
    })
    
    assert response.status_code == 201
    assert MyModel.objects.filter(name="Test Model").exists()
```

## Adding a WebSocket Consumer

### 1. Create Consumer

```python
# backend/webnet/api/consumers.py
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async

class MyConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return
        
        self.room_group_name = f"my_feature_{self.scope['url_route']['kwargs']['id']}"
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive_json(self, content):
        if content.get("type") == "ping":
            await self.send_json({"type": "pong"})
    
    async def my_update(self, event):
        await self.send_json(event["data"])
```

### 2. Add Routing

```python
# backend/webnet/routing.py
from django.urls import re_path
from .api.consumers import MyConsumer

websocket_urlpatterns = [
    # ... existing patterns
    re_path(r"ws/my-feature/(?P<id>\d+)/$", MyConsumer.as_asgi()),
]
```

### 3. Broadcast Updates

```python
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

channel_layer = get_channel_layer()
async_to_sync(channel_layer.group_send)(
    f"my_feature_{id}",
    {
        "type": "my_update",
        "data": {"status": "updated", "id": id}
    }
)
```

## Adding a Scheduled Job

### 1. Create Celery Beat Task

```python
# backend/webnet/jobs/tasks.py
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

@shared_task(name="scheduled_backup_job")
def scheduled_backup_job(customer_id: int):
    """Scheduled config backup for all devices."""
    from webnet.jobs.services import JobService
    from webnet.customers.models import Customer
    from webnet.devices.models import Device
    
    customer = Customer.objects.get(pk=customer_id)
    devices = Device.objects.filter(customer=customer, enabled=True)
    
    js = JobService()
    job = js.create_job(
        job_type="config_backup",
        user=None,  # System user
        customer=customer,
        target_summary={"filters": {"customer_id": customer_id}},
        payload={"source_label": "scheduled"}
    )
    
    from webnet.jobs.tasks import config_backup_job
    config_backup_job.delay(job.id, {"customer_id": customer_id}, "scheduled")
```

### 2. Configure Celery Beat

```python
# backend/webnet/core/celery.py
from celery.schedules import crontab

app.conf.beat_schedule = {
    'daily-backup': {
        'task': 'scheduled_backup_job',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
        'args': (1,)  # customer_id
    },
}
```

### 3. Start Celery Beat

```bash
celery -A webnet.core.celery:celery_app beat -l info
```

## Adding a Custom Filter

### 1. Create Filter Backend

```python
# backend/webnet/api/filters.py
from rest_framework.filters import BaseFilterBackend

class DeviceRoleFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        role = request.query_params.get("role")
        if role:
            queryset = queryset.filter(role=role)
        return queryset
```

### 2. Use in ViewSet

```python
from rest_framework import viewsets
from .filters import DeviceRoleFilter

class DeviceViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    filter_backends = [DeviceRoleFilter]
    # ...
```

## Workflow Checklist

When adding a new feature:

- [ ] Model created with customer ForeignKey
- [ ] Migration created and applied
- [ ] Serializer created
- [ ] ViewSet created with tenant scoping
- [ ] URLs registered
- [ ] Permissions configured
- [ ] Tests written
- [ ] Documentation updated
- [ ] UI created (if needed)
- [ ] Tenant isolation verified
- [ ] WebSocket consumer added (if real-time updates needed)
- [ ] Scheduled jobs configured (if needed)

## References

- [Multi-Tenancy Patterns](./multi-tenancy.md)
- [HTMX Patterns](./htmx-patterns.md)
- [Testing Guide](./testing.md)
- [API Development Guide](./api-development.md)
- [Nornir Integration](./nornir-integration.md)
