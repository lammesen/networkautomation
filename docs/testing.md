# Testing Guide

This guide covers testing patterns, fixtures, and best practices for the webnet application.

## Table of Contents
- [Test Setup](#test-setup)
- [Fixtures](#fixtures)
- [Testing Patterns](#testing-patterns)
- [Testing Multi-Tenancy](#testing-multi-tenancy)
- [Testing HTMX Views](#testing-htmx-views)
- [Testing WebSocket Consumers](#testing-websocket-consumers)
- [Testing Celery Tasks](#testing-celery-tasks)
- [Mocking Network Devices](#mocking-network-devices)

## Test Setup

### Configuration
Tests use pytest with Django. Configuration is in `conftest.py`:

```python
# backend/webnet/tests/conftest.py
import os
import pytest
from cryptography.fernet import Fernet

os.environ.setdefault("DEBUG", "true")

@pytest.fixture(autouse=True)
def set_encryption_key(settings):
    """Ensure ENCRYPTION_KEY is set for tests."""
    key = Fernet.generate_key().decode()
    settings.ENCRYPTION_KEY = key
    os.environ["ENCRYPTION_KEY"] = key
    settings.CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        }
    }
```

### Running Tests
```bash
# All tests
make backend-test

# Specific test file
backend/venv/bin/python -m pytest backend/webnet/tests/test_devices.py

# Specific test
backend/venv/bin/python -m pytest backend/webnet/tests/test_devices.py::test_create_device

# With coverage
backend/venv/bin/python -m pytest --cov=webnet backend/webnet/tests/
```

## Fixtures

### User Fixtures
```python
import pytest
from webnet.users.models import User
from webnet.customers.models import Customer

@pytest.fixture
def admin_user(db):
    """Admin user with access to all customers."""
    return User.objects.create_user(
        username="admin",
        password="testpass",
        role="admin"
    )

@pytest.fixture
def operator_user(db, customer1):
    """Operator user assigned to customer1."""
    user = User.objects.create_user(
        username="operator",
        password="testpass",
        role="operator"
    )
    user.customers.add(customer1)
    return user

@pytest.fixture
def viewer_user(db, customer1):
    """Viewer user assigned to customer1."""
    user = User.objects.create_user(
        username="viewer",
        password="testpass",
        role="viewer"
    )
    user.customers.add(customer1)
    return user
```

### Customer Fixtures
```python
@pytest.fixture
def customer1(db):
    return Customer.objects.create(name="Customer 1")

@pytest.fixture
def customer2(db):
    return Customer.objects.create(name="Customer 2")
```

### Device Fixtures
```python
@pytest.fixture
def credential1(db, customer1):
    from webnet.devices.models import Credential
    return Credential.objects.create(
        customer=customer1,
        name="test-cred",
        username="admin",
        password="password123"
    )

@pytest.fixture
def device1(db, customer1, credential1):
    from webnet.devices.models import Device
    return Device.objects.create(
        customer=customer1,
        hostname="router1",
        mgmt_ip="192.168.1.1",
        vendor="cisco",
        platform="ios",
        credential=credential1
    )

@pytest.fixture
def device2(db, customer2, credential2):
    from webnet.devices.models import Device
    return Device.objects.create(
        customer=customer2,
        hostname="router2",
        mgmt_ip="192.168.1.2",
        vendor="juniper",
        platform="junos",
        credential=credential2
    )
```

### Job Fixtures
```python
@pytest.fixture
def job1(db, customer1, operator_user):
    from webnet.jobs.models import Job
    return Job.objects.create(
        customer=customer1,
        user=operator_user,
        type="run_commands",
        status="queued"
    )
```

### API Client Fixture
```python
from rest_framework.test import APIClient

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def authenticated_client(api_client, operator_user):
    api_client.force_authenticate(user=operator_user)
    return api_client
```

## Testing Patterns

### Testing API Endpoints
```python
from rest_framework.test import APIClient
from rest_framework import status

def test_list_devices(authenticated_client, device1):
    """Test listing devices."""
    response = authenticated_client.get("/api/v1/devices/")
    
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]["hostname"] == "router1"

def test_create_device(authenticated_client, customer1, credential1):
    """Test creating a device."""
    response = authenticated_client.post("/api/v1/devices/", {
        "customer": customer1.id,
        "hostname": "new-router",
        "mgmt_ip": "192.168.1.10",
        "vendor": "cisco",
        "platform": "ios",
        "credential": credential1.id
    })
    
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["hostname"] == "new-router"

def test_update_device(authenticated_client, device1):
    """Test updating a device."""
    response = authenticated_client.patch(
        f"/api/v1/devices/{device1.id}/",
        {"hostname": "updated-router"}
    )
    
    assert response.status_code == status.HTTP_200_OK
    assert response.data["hostname"] == "updated-router"
    device1.refresh_from_db()
    assert device1.hostname == "updated-router"

def test_delete_device(authenticated_client, device1):
    """Test deleting a device."""
    response = authenticated_client.delete(f"/api/v1/devices/{device1.id}/")
    
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Device.objects.filter(id=device1.id).exists()
```

### Testing Permissions
```python
def test_viewer_cannot_create_device(viewer_user, device1):
    """Viewer role cannot create devices."""
    client = APIClient()
    client.force_authenticate(user=viewer_user)
    
    response = client.post("/api/v1/devices/", {
        "hostname": "test",
        "mgmt_ip": "192.168.1.1",
        # ...
    })
    
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_operator_can_create_device(operator_user, customer1, credential1):
    """Operator role can create devices."""
    client = APIClient()
    client.force_authenticate(user=operator_user)
    
    response = client.post("/api/v1/devices/", {
        "customer": customer1.id,
        "hostname": "test",
        # ...
    })
    
    assert response.status_code == status.HTTP_201_CREATED
```

## Testing Multi-Tenancy

### Test Tenant Scoping
```python
def test_viewset_filters_by_customer(operator_user, customer1, customer2, device1, device2):
    """Non-admin users only see their customer's devices."""
    client = APIClient()
    client.force_authenticate(user=operator_user)
    
    response = client.get("/api/v1/devices/")
    
    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]["hostname"] == "router1"  # device1, not device2

def test_cannot_access_other_customer_device(operator_user, device2):
    """Users cannot access devices from other customers."""
    client = APIClient()
    client.force_authenticate(user=operator_user)
    
    response = client.get(f"/api/v1/devices/{device2.id}/")
    
    # Should be 404 (not found) or 403 (forbidden)
    assert response.status_code in [404, 403]

def test_admin_sees_all_customers(admin_user, device1, device2):
    """Admin users see all customers' data."""
    client = APIClient()
    client.force_authenticate(user=admin_user)
    
    response = client.get("/api/v1/devices/")
    
    assert response.status_code == 200
    assert len(response.data) == 2
    hostnames = [d["hostname"] for d in response.data]
    assert "router1" in hostnames
    assert "router2" in hostnames
```

### Test Cross-Tenant Prevention
```python
def test_cannot_create_device_for_other_customer(operator_user, customer2, credential2):
    """Users cannot create devices for customers they don't have access to."""
    client = APIClient()
    client.force_authenticate(user=operator_user)
    
    response = client.post("/api/v1/devices/", {
        "customer": customer2.id,  # operator_user doesn't have access
        "hostname": "test",
        "mgmt_ip": "192.168.1.1",
        # ...
    })
    
    assert response.status_code in [400, 403]
```

## Testing HTMX Views

### Test HTMX Partial Request
```python
from django.test import Client

def test_htmx_partial_request(operator_user, device1):
    """Test HTMX partial template response."""
    client = Client()
    client.force_login(operator_user)
    
    # Simulate HTMX request
    response = client.get(
        "/devices/",
        HTTP_HX_REQUEST="true"
    )
    
    assert response.status_code == 200
    # Should return partial template
    assert "_table.html" in str(response.templates[0].name)

def test_htmx_full_page_request(operator_user, device1):
    """Test full page template response."""
    client = Client()
    client.force_login(operator_user)
    
    response = client.get("/devices/")
    
    assert response.status_code == 200
    # Should return full page template
    assert "list.html" in str(response.templates[0].name)
```

### Test Form Submission
```python
def test_create_device_form(operator_user, customer1, credential1):
    """Test device creation via form."""
    client = Client()
    client.force_login(operator_user)
    
    response = client.post("/devices/create/", {
        "customer": customer1.id,
        "hostname": "new-router",
        "mgmt_ip": "192.168.1.10",
        "vendor": "cisco",
        "platform": "ios",
        "credential": credential1.id
    })
    
    assert response.status_code == 302  # Redirect after success
    assert Device.objects.filter(hostname="new-router").exists()
```

## Testing WebSocket Consumers

### Test Consumer Connection
```python
from channels.testing import WebsocketCommunicator
from webnet.api.consumers import JobLogsConsumer

@pytest.mark.asyncio
async def test_job_logs_consumer_connect(db, job1):
    """Test WebSocket consumer connection."""
    communicator = WebsocketCommunicator(
        JobLogsConsumer.as_asgi(),
        f"/ws/jobs/{job1.id}/"
    )
    
    connected, subprotocol = await communicator.connect()
    assert connected
    
    await communicator.disconnect()
```

### Test Consumer Messages
```python
@pytest.mark.asyncio
async def test_job_logs_consumer_receives_updates(db, job1):
    """Test consumer receives job updates."""
    communicator = WebsocketCommunicator(
        JobLogsConsumer.as_asgi(),
        f"/ws/jobs/{job1.id}/"
    )
    
    await communicator.connect()
    
    # Send message
    await communicator.send_json_to({
        "type": "ping"
    })
    
    # Receive response
    response = await communicator.receive_json_from()
    assert response["type"] == "pong"
    
    await communicator.disconnect()
```

## Testing Celery Tasks

### Mock Celery Task Execution
```python
from unittest.mock import patch, MagicMock
from webnet.jobs.tasks import run_commands_job

def test_run_commands_job(db, job1, device1):
    """Test command execution task."""
    with patch('webnet.jobs.tasks.build_inventory') as mock_inventory:
        # Mock inventory
        mock_nr = MagicMock()
        mock_inventory.return_value.hosts = {device1.hostname: {}}
        
        with patch('webnet.jobs.tasks.Nornir') as mock_nornir:
            mock_nr_instance = MagicMock()
            mock_nr_instance.run.return_value = {
                device1.hostname: MagicMock(failed=False, result="output")
            }
            mock_nornir.return_value = mock_nr_instance
            
            # Execute task synchronously
            run_commands_job(
                job_id=job1.id,
                targets={"id": device1.id},
                commands=["show version"]
            )
            
            # Verify job status
            job1.refresh_from_db()
            assert job1.status == "success"
```

### Test Job Service
```python
from webnet.jobs.services import JobService

def test_job_service_create_job(db, operator_user, customer1):
    """Test job creation."""
    js = JobService()
    job = js.create_job(
        job_type="run_commands",
        user=operator_user,
        customer=customer1,
        target_summary={"filters": {}},
        payload={"commands": ["show version"]}
    )
    
    assert job.id is not None
    assert job.status == "queued"
    assert job.type == "run_commands"
    assert job.customer == customer1
    assert job.user == operator_user

def test_job_service_append_log(db, job1):
    """Test log appending."""
    js = JobService()
    js.append_log(job1, level="INFO", message="Test log")
    
    from webnet.jobs.models import JobLog
    log = JobLog.objects.get(job=job1)
    assert log.level == "INFO"
    assert log.message == "Test log"
```

## Mocking Network Devices

### Mock Nornir Inventory
```python
from unittest.mock import patch, MagicMock

def test_build_inventory(db, device1):
    """Test inventory building."""
    from webnet.automation import build_inventory
    
    inventory = build_inventory(
        targets={"id": device1.id},
        customer_id=device1.customer_id
    )
    
    assert len(inventory.hosts) == 1
    assert device1.hostname in inventory.hosts
    assert inventory.hosts[device1.hostname]["hostname"] == device1.mgmt_ip
```

### Mock NAPALM/Netmiko
```python
from unittest.mock import patch

def test_config_backup_mocked(db, job1, device1):
    """Test config backup with mocked NAPALM."""
    with patch('nornir_napalm.tasks.napalm_get') as mock_napalm:
        mock_napalm.return_value.result = {
            "get_config": {"running": "hostname router1\n"}
        }
        
        from webnet.jobs.tasks import config_backup_job
        config_backup_job(
            job_id=job1.id,
            targets={"id": device1.id},
            source_label="test"
        )
        
        job1.refresh_from_db()
        assert job1.status == "success"
        
        # Verify config snapshot created
        from webnet.config_mgmt.models import ConfigSnapshot
        assert ConfigSnapshot.objects.filter(device=device1).exists()
```

## Test Best Practices

### 1. Use Descriptive Test Names
```python
# Good
def test_viewer_cannot_create_device_for_other_customer():
    pass

# Bad
def test_viewer():
    pass
```

### 2. One Assertion Per Concept
```python
# Good
def test_device_creation(authenticated_client, customer1):
    response = authenticated_client.post("/api/v1/devices/", {...})
    assert response.status_code == 201
    assert response.data["hostname"] == "router1"
    assert Device.objects.filter(hostname="router1").exists()

# Bad - multiple unrelated assertions
def test_everything(authenticated_client):
    # Tests device creation, job creation, compliance, etc.
    pass
```

### 3. Use Fixtures for Common Setup
```python
# Good - reusable fixtures
@pytest.fixture
def authenticated_operator_client(operator_user):
    client = APIClient()
    client.force_authenticate(user=operator_user)
    return client

# Bad - duplicate setup in each test
def test_something():
    client = APIClient()
    user = User.objects.create_user(...)
    client.force_authenticate(user=user)
    # ...
```

### 4. Test Edge Cases
```python
def test_empty_device_list(authenticated_client):
    """Test listing devices when none exist."""
    response = authenticated_client.get("/api/v1/devices/")
    assert response.status_code == 200
    assert response.data == []

def test_invalid_device_id(authenticated_client):
    """Test accessing non-existent device."""
    response = authenticated_client.get("/api/v1/devices/99999/")
    assert response.status_code == 404
```

### 5. Test Tenant Isolation Thoroughly
```python
def test_tenant_isolation_comprehensive(operator_user, customer1, customer2):
    """Comprehensive tenant isolation test."""
    # Create devices for both customers
    device1 = Device.objects.create(customer=customer1, ...)
    device2 = Device.objects.create(customer=customer2, ...)
    
    client = APIClient()
    client.force_authenticate(user=operator_user)
    
    # Should only see customer1's device
    response = client.get("/api/v1/devices/")
    assert len(response.data) == 1
    assert response.data[0]["id"] == device1.id
    
    # Cannot access customer2's device
    response = client.get(f"/api/v1/devices/{device2.id}/")
    assert response.status_code in [403, 404]
```

## References

- [pytest-django Documentation](https://pytest-django.readthedocs.io/)
- [DRF Testing](https://www.django-rest-framework.org/api-guide/testing/)
- [Channels Testing](https://channels.readthedocs.io/en/stable/testing.html)
- [Multi-Tenancy Patterns](./multi-tenancy.md)
