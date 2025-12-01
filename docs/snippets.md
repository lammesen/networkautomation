# Code Snippets Library

Quick reference for common code patterns used throughout the webnet application.

## Table of Contents
- [Django ORM Queries](#django-orm-queries)
- [DRF Serializers](#drf-serializers)
- [HTMX Templates](#htmx-templates)
- [Celery Tasks](#celery-tasks)
- [Permission Checks](#permission-checks)
- [WebSocket Consumers](#websocket-consumers)
- [Form Handling](#form-handling)

## Django ORM Queries

### Basic Tenant-Scoped Query
```python
from webnet.devices.models import Device

# Filter by customer
devices = Device.objects.filter(customer_id=customer_id)

# With related objects
devices = Device.objects.select_related("customer", "credential").filter(
    customer_id=customer_id
)
```

### Filtering with Multiple Conditions
```python
from django.db.models import Q

devices = Device.objects.filter(
    Q(customer_id=customer_id) &
    Q(enabled=True) &
    (Q(vendor="cisco") | Q(vendor="juniper"))
)
```

### Aggregations
```python
from django.db.models import Count, Avg, Max

# Count devices by vendor
vendor_counts = Device.objects.filter(
    customer_id=customer_id
).values("vendor").annotate(
    count=Count("id")
).order_by("-count")

# Average devices per site
avg_per_site = Device.objects.filter(
    customer_id=customer_id
).values("site").annotate(
    count=Count("id")
).aggregate(
    avg=Avg("count")
)
```

### Date Filtering
```python
from django.utils import timezone
from datetime import timedelta

# Devices added in last 7 days
week_ago = timezone.now() - timedelta(days=7)
recent_devices = Device.objects.filter(
    customer_id=customer_id,
    created_at__gte=week_ago
)

# Jobs in last 24 hours
last_24h = timezone.now() - timedelta(hours=24)
recent_jobs = Job.objects.filter(
    customer_id=customer_id,
    requested_at__gte=last_24h
)
```

### Exists Check
```python
# Efficient existence check
if Device.objects.filter(customer_id=customer_id, hostname="router1").exists():
    # Device exists
    pass
```

### Values List
```python
# Get list of hostnames
hostnames = Device.objects.filter(
    customer_id=customer_id
).values_list("hostname", flat=True)

# Get list of tuples
device_data = Device.objects.filter(
    customer_id=customer_id
).values_list("id", "hostname", "mgmt_ip")
```

### Bulk Operations
```python
# Bulk update
Device.objects.filter(
    customer_id=customer_id,
    vendor="cisco"
).update(platform="ios")

# Bulk create
devices = [
    Device(customer=customer, hostname=f"router{i}", mgmt_ip=f"192.168.1.{i}")
    for i in range(10)
]
Device.objects.bulk_create(devices)
```

## DRF Serializers

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

### Custom Validation
```python
class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ["hostname", "mgmt_ip", "customer"]
    
    def validate_hostname(self, value):
        if not value:
            raise serializers.ValidationError("Hostname required")
        if Device.objects.filter(
            customer=self.initial_data.get("customer"),
            hostname=value
        ).exists():
            raise serializers.ValidationError("Hostname already exists")
        return value
    
    def validate(self, data):
        # Cross-field validation
        if data.get("vendor") == "cisco" and not data.get("platform"):
            raise serializers.ValidationError("Platform required for Cisco devices")
        return data
```

### Write-Only Fields
```python
class DeviceSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = Device
        fields = ["hostname", "password"]
    
    def create(self, validated_data):
        password = validated_data.pop("password")
        device = super().create(validated_data)
        # Use password for something
        return device
```

## HTMX Templates

### Basic Table Partial
```html
{# _table.html #}
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
        <td class="table-cell">
          <span class="badge badge-{{ item.status }}">
            {{ item.status }}
          </span>
        </td>
      </tr>
      {% empty %}
      <tr>
        <td colspan="2" class="table-cell text-center text-muted">
          No items found
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
```

### Form with HTMX
```html
<form hx-post="/api/devices/create/"
      hx-target="#devices-table"
      hx-swap="innerHTML"
      hx-indicator="#loading">
  {% csrf_token %}
  <div class="form-group">
    <label>Hostname</label>
    <input type="text" name="hostname" required>
  </div>
  <button type="submit">Create</button>
</form>
<div id="loading" class="htmx-indicator">Creating...</div>
```

### Filter Form
```html
<form hx-get="/devices/"
      hx-target="#devices-table"
      hx-swap="innerHTML"
      hx-trigger="change">
  <select name="vendor">
    <option value="">All Vendors</option>
    <option value="cisco">Cisco</option>
    <option value="juniper">Juniper</option>
  </select>
  <input type="search" 
         name="search"
         placeholder="Search..."
         hx-trigger="keyup changed delay:500ms">
</form>
```

### Modal Dialog
```html
{# _modal.html #}
<div id="device-modal" class="modal">
  <div class="modal-content">
    <h2>Create Device</h2>
    <form hx-post="/devices/create/"
          hx-target="#devices-table"
          hx-swap="innerHTML"
          hx-on::after-request="
            if (event.detail.xhr.status === 201) {
              document.getElementById('device-modal').close();
            }
          ">
      {% csrf_token %}
      <!-- form fields -->
      <button type="submit">Create</button>
    </form>
  </div>
</div>
```

## Celery Tasks

### Basic Task Pattern
```python
from celery import shared_task
from webnet.jobs.models import Job
from webnet.jobs.services import JobService

@shared_task(name="my_task")
def my_task(job_id: int, **kwargs) -> None:
    js = JobService()
    try:
        job = Job.objects.get(pk=job_id)
    except Job.DoesNotExist:
        logger.warning("Job %s not found", job_id)
        return
    
    js.set_status(job, "running")
    
    try:
        # Task logic
        result = execute_task(**kwargs)
        js.set_status(job, "success", result_summary=result)
    except Exception as exc:
        js.append_log(job, level="ERROR", message=str(exc))
        js.set_status(job, "failed", result_summary={"error": str(exc)})
```

### Task with Logging
```python
@shared_task(name="my_task")
def my_task(job_id: int, targets: dict) -> None:
    js = JobService()
    job = Job.objects.get(pk=job_id)
    js.set_status(job, "running")
    
    # Log progress
    js.append_log(job, level="INFO", message="Starting task")
    
    for item in items:
        js.append_log(job, level="INFO", host=item.hostname, message=f"Processing {item.hostname}")
        # Process item
    
    js.append_log(job, level="INFO", message="Task completed")
    js.set_status(job, "success")
```

### Task with Nornir
```python
from webnet.automation import build_inventory
from nornir.core import Nornir

@shared_task(name="run_commands_job")
def run_commands_job(job_id: int, targets: dict, commands: list[str]) -> None:
    js = JobService()
    job = Job.objects.get(pk=job_id)
    js.set_status(job, "running")
    
    # Build inventory
    inventory = build_inventory(targets, customer_id=job.customer_id)
    if not inventory.hosts:
        js.append_log(job, level="ERROR", message="No devices matched")
        js.set_status(job, "failed")
        return
    
    nr = Nornir(inventory=inventory)
    results = nr.run(task=some_nornir_task)
    
    # Process results
    for host, result in results.items():
        if result.failed:
            js.append_log(job, level="ERROR", host=host, message=str(result.exception))
        else:
            js.append_log(job, level="INFO", host=host, message=str(result.result))
    
    js.set_status(job, "success")
```

## Permission Checks

### Check Customer Access
```python
from webnet.api.permissions import user_has_customer_access

def my_view(request, device_id):
    device = get_object_or_404(Device, pk=device_id)
    
    if not user_has_customer_access(request.user, device.customer_id):
        return Response(
            {"detail": "Access denied"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Proceed
```

### Resolve Customer from Request
```python
from webnet.api.permissions import resolve_customer_for_request

def my_view(request):
    customer = resolve_customer_for_request(request)
    if not customer:
        return Response(
            {"detail": "Customer required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Use customer
```

### Check Role
```python
def my_view(request):
    user = request.user
    if getattr(user, "role", "viewer") not in {"operator", "admin"}:
        return Response(
            {"detail": "Insufficient permissions"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Proceed
```

## WebSocket Consumers

### Basic Consumer Pattern
```python
from channels.generic.websocket import AsyncWebsocketConsumer
import json

class MyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = f"job_{self.scope['url_route']['kwargs']['job_id']}"
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
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        # Handle message
        await self.send(text_data=json.dumps({"status": "ok"}))
    
    async def job_update(self, event):
        await self.send(text_data=json.dumps(event))
```

### Broadcasting Updates
```python
from webnet.core.broadcasts import broadcast_job_update

# In view or task
broadcast_job_update(job, action="updated")
```

## Form Handling

### ModelForm with Customer Filtering
```python
from django import forms
from webnet.devices.models import Device

class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = ["customer", "hostname", "mgmt_ip", "vendor", "credential"]
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        
        if user and getattr(user, "role", "viewer") != "admin":
            self.fields["customer"].queryset = user.customers.all()
            self.fields["credential"].queryset = Credential.objects.filter(
                customer__in=user.customers.all()
            )
```

### Form Validation
```python
class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = ["hostname", "mgmt_ip"]
    
    def clean_hostname(self):
        hostname = self.cleaned_data["hostname"]
        if Device.objects.filter(
            customer=self.cleaned_data.get("customer"),
            hostname=hostname
        ).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise forms.ValidationError("Hostname already exists")
        return hostname
```

## View Patterns

### Tenant-Scoped List View
```python
from webnet.ui.views import TenantScopedView

class MyListView(TenantScopedView):
    template_name = "myapp/list.html"
    partial_name = "myapp/_table.html"
    customer_field = "customer_id"
    
    def get(self, request):
        items = self.filter_by_customer(MyModel.objects.all())
        
        # Apply filters
        search = request.GET.get("search", "")
        if search:
            items = items.filter(name__icontains=search)
        
        # HTMX partial request
        if request.headers.get('HX-Request'):
            return render(request, self.partial_name, {"items": items})
        
        # Full page request
        return render(request, self.template_name, {"items": items})
```

### Create View with Permission Check
```python
class MyCreateView(TenantScopedView):
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
        
        # Create object
        form = MyForm(request.POST, user=request.user)
        if form.is_valid():
            obj = form.save()
            return redirect("myapp-detail", pk=obj.id)
        
        return render(request, "myapp/form.html", {"form": form})
```

## Job Service Patterns

### Create Job
```python
from webnet.jobs.services import JobService

js = JobService()
job = js.create_job(
    job_type="run_commands",
    user=request.user,
    customer=customer,
    target_summary={"filters": {"site": "datacenter1"}},
    payload={"commands": ["show version"]}
)
```

### Update Job Status
```python
js = JobService()
js.set_status(job, "running")
js.set_status(job, "success", result_summary={"devices": 10})
```

### Append Logs
```python
js = JobService()
js.append_log(job, level="INFO", message="Starting task")
js.append_log(job, level="INFO", host="router1", message="Command executed")
js.append_log(job, level="ERROR", host="router2", message="Connection failed")
```

## React Island Integration

### Component with HTMX
```tsx
import { Button } from "../ui/button";

interface MyIslandProps {
  items: Array<{ id: number; name: string }>;
  actionUrl: string;
}

export default function MyIsland({ items, actionUrl }: MyIslandProps) {
  const htmx = (window as any).htmx;
  
  const handleAction = (id: number) => {
    htmx.ajax('POST', `${actionUrl}${id}/`, {
      target: '#result',
      swap: 'innerHTML'
    });
  };
  
  return (
    <div>
      {items.map(item => (
        <Button key={item.id} onClick={() => handleAction(item.id)}>
          {item.name}
        </Button>
      ))}
    </div>
  );
}
```

### Use in Template
```html
<div data-island="MyIsland" 
     data-props='{{ island_props_json|escapejs }}'>
</div>
```

## Broadcasting Updates

### Broadcast Job Update
```python
from webnet.core.broadcasts import broadcast_job_update

# After job status change
broadcast_job_update(job, action="updated")

# With custom data
broadcast_job_update(
    job,
    action="created",
    data={"custom": "data"}
)
```

### Broadcast Device Update
```python
from webnet.core.broadcasts import broadcast_device_update

# After device modification
broadcast_device_update(device, action="updated")

# After device creation
broadcast_device_update(device, action="created")
```

### Broadcast Entity Update
```python
from webnet.core.broadcasts import broadcast_entity_update

# Generic entity broadcast
broadcast_entity_update(
    entity_type="config",
    entity_id=snapshot.id,
    action="created",
    customer_id=customer.id
)
```

## Job Service Patterns

### Create Job
```python
from webnet.jobs.services import JobService

js = JobService()
job = js.create_job(
    job_type="run_commands",
    user=request.user,
    customer=customer,
    target_summary={"filters": {"site": "datacenter1"}},
    payload={"commands": ["show version"]}
)
```

### Update Job Status
```python
js = JobService()

# Set status
js.set_status(job, "running")
js.set_status(job, "success", result_summary={"devices": 10})
js.set_status(job, "failed", result_summary={"error": "timeout"})
```

### Append Logs
```python
js = JobService()

# Basic log
js.append_log(job, level="INFO", message="Starting task")

# Host-specific log
js.append_log(job, level="INFO", host="router1", message="Command executed")

# Error log
js.append_log(job, level="ERROR", host="router2", message="Connection failed")

# Log with extra data
js.append_log(
    job,
    level="INFO",
    host="router1",
    message="Config backed up",
    extra={"size": 1024, "lines": 50}
)
```

### Get Job Logs
```python
from webnet.jobs.models import JobLog

# Recent logs
logs = JobLog.objects.filter(job=job).order_by("-ts")[:100]

# Logs by level
error_logs = JobLog.objects.filter(job=job, level="ERROR")

# Logs by host
host_logs = JobLog.objects.filter(job=job, host="router1")
```

## References

- [Django ORM Documentation](https://docs.djangoproject.com/en/stable/topics/db/queries/)
- [DRF Serializers](https://www.django-rest-framework.org/api-guide/serializers/)
- [HTMX Documentation](https://htmx.org/docs/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [Channels Documentation](https://channels.readthedocs.io/)
