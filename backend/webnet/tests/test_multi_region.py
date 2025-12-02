"""Tests for multi-region deployment support."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from webnet.customers.models import Customer
from webnet.core.models import Region
from webnet.devices.models import Device, Credential
from webnet.jobs.services import JobService

User = get_user_model()


@pytest.fixture
def customer():
    return Customer.objects.create(name="Test Corp")


@pytest.fixture
def user(customer):
    user = User.objects.create_user(username="testuser", password="testpass", role="admin")
    user.customers.add(customer)
    return user


@pytest.fixture
def credential(customer):
    cred = Credential.objects.create(customer=customer, name="test-creds", username="admin")
    cred.password = "secret"
    cred.save()
    return cred


@pytest.fixture
def region_us_east(customer):
    return Region.objects.create(
        customer=customer,
        name="US East",
        identifier="us-east-1",
        priority=100,
        enabled=True,
        health_status=Region.STATUS_HEALTHY,
    )


@pytest.fixture
def region_us_west(customer):
    return Region.objects.create(
        customer=customer,
        name="US West",
        identifier="us-west-1",
        priority=90,
        enabled=True,
        health_status=Region.STATUS_HEALTHY,
    )


@pytest.fixture
def device_in_us_east(customer, credential, region_us_east):
    return Device.objects.create(
        customer=customer,
        hostname="router-east-1",
        mgmt_ip="10.1.1.1",
        vendor="cisco",
        platform="ios",
        credential=credential,
        region=region_us_east,
        site="us-east-datacenter",
    )


@pytest.fixture
def device_in_us_west(customer, credential, region_us_west):
    return Device.objects.create(
        customer=customer,
        hostname="router-west-1",
        mgmt_ip="10.2.1.1",
        vendor="cisco",
        platform="ios",
        credential=credential,
        region=region_us_west,
        site="us-west-datacenter",
    )


@pytest.mark.django_db
class TestRegionModel:
    """Test Region model functionality."""

    def test_region_creation(self, customer):
        """Test creating a region."""
        region = Region.objects.create(
            customer=customer,
            name="Europe West",
            identifier="eu-west-1",
            priority=80,
            enabled=True,
        )
        assert region.name == "Europe West"
        assert region.identifier == "eu-west-1"
        assert region.queue_name == "region_eu-west-1"
        assert region.is_available() is True

    def test_region_queue_name(self, region_us_east):
        """Test queue name generation."""
        assert region_us_east.queue_name == "region_us-east-1"

    def test_region_is_available_when_healthy(self, region_us_east):
        """Test region is available when healthy."""
        assert region_us_east.is_available() is True

    def test_region_not_available_when_offline(self, region_us_east):
        """Test region is not available when offline."""
        region_us_east.health_status = Region.STATUS_OFFLINE
        region_us_east.save()
        assert region_us_east.is_available() is False

    def test_region_not_available_when_disabled(self, region_us_east):
        """Test region is not available when disabled."""
        region_us_east.enabled = False
        region_us_east.save()
        assert region_us_east.is_available() is False

    def test_update_health_status(self, region_us_east):
        """Test updating region health status."""
        region_us_east.update_health_status(Region.STATUS_DEGRADED, "High load")
        region_us_east.refresh_from_db()
        assert region_us_east.health_status == Region.STATUS_DEGRADED
        assert region_us_east.last_health_check is not None


@pytest.mark.django_db
class TestRegionAPI:
    """Test Region API endpoints."""

    def test_list_regions(self, user, customer, region_us_east, region_us_west):
        """Test listing regions."""
        client = APIClient()
        client.force_login(user)
        response = client.get("/api/v1/regions/")
        assert response.status_code == 200
        data = response.json()
        # API may return paginated results
        if "results" in data:
            assert len(data["results"]) == 2
        else:
            assert len(data) == 2

    def test_create_region(self, user, customer):
        """Test creating a region via API."""
        client = APIClient()
        client.force_login(user)
        data = {
            "customer": customer.id,
            "name": "Asia Pacific",
            "identifier": "ap-southeast-1",
            "priority": 70,
            "enabled": True,
        }
        response = client.post("/api/v1/regions/", data, format="json")
        assert response.status_code == 201
        assert response.json()["name"] == "Asia Pacific"
        assert response.json()["queue_name"] == "region_ap-southeast-1"

    def test_get_region(self, user, region_us_east):
        """Test getting a specific region."""
        client = APIClient()
        client.force_login(user)
        response = client.get(f"/api/v1/regions/{region_us_east.id}/")
        assert response.status_code == 200
        assert response.json()["identifier"] == "us-east-1"

    def test_update_region(self, user, region_us_east):
        """Test updating a region."""
        client = APIClient()
        client.force_login(user)
        data = {"priority": 110}
        response = client.patch(f"/api/v1/regions/{region_us_east.id}/", data, format="json")
        assert response.status_code == 200
        assert response.json()["priority"] == 110

    def test_update_health_endpoint(self, user, region_us_east):
        """Test updating region health via API endpoint."""
        client = APIClient()
        client.force_login(user)
        data = {"health_status": "degraded", "message": "High latency"}
        response = client.post(
            f"/api/v1/regions/{region_us_east.id}/update_health/", data, format="json"
        )
        assert response.status_code == 200
        assert response.json()["health_status"] == "degraded"

    def test_get_region_devices(self, user, region_us_east, device_in_us_east):
        """Test getting devices assigned to a region."""
        client = APIClient()
        client.force_login(user)
        response = client.get(f"/api/v1/regions/{region_us_east.id}/devices/")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["hostname"] == "router-east-1"

    def test_unauthorized_access(self, region_us_east):
        """Test that unauthenticated users cannot access regions."""
        client = APIClient()
        response = client.get("/api/v1/regions/")
        assert response.status_code in {401, 403}


@pytest.mark.django_db
class TestJobRegionRouting:
    """Test job routing to regional queues."""

    def test_job_routed_to_device_region(
        self, customer, user, device_in_us_east, region_us_east
    ):
        """Test that jobs are routed to the device's region."""
        dispatched_tasks = []

        def mock_dispatcher(task_name, args=None, queue=None):
            dispatched_tasks.append({"task": task_name, "args": args, "queue": queue})

        service = JobService(dispatcher=mock_dispatcher)
        job = service.create_job(
            job_type="run_commands",
            user=user,
            customer=customer,
            target_summary={"filters": {"site": "us-east-datacenter"}},
            payload={"commands": ["show version"]},
        )

        # Verify job was assigned to the correct region
        job.refresh_from_db()
        assert job.region == region_us_east
        assert len(dispatched_tasks) == 1
        assert dispatched_tasks[0]["queue"] == "region_us-east-1"

    def test_job_routed_to_highest_priority_region(
        self, customer, user, credential, region_us_east, region_us_west
    ):
        """Test that jobs are routed to highest priority region when multiple match."""
        # Create devices in both regions with same site
        Device.objects.create(
            customer=customer,
            hostname="router-a",
            mgmt_ip="10.1.1.2",
            vendor="cisco",
            platform="ios",
            credential=credential,
            region=region_us_east,
            site="multi-region-site",
        )
        Device.objects.create(
            customer=customer,
            hostname="router-b",
            mgmt_ip="10.2.1.2",
            vendor="cisco",
            platform="ios",
            credential=credential,
            region=region_us_west,
            site="multi-region-site",
        )

        dispatched_tasks = []

        def mock_dispatcher(task_name, args=None, queue=None):
            dispatched_tasks.append({"task": task_name, "args": args, "queue": queue})

        service = JobService(dispatcher=mock_dispatcher)
        job = service.create_job(
            job_type="run_commands",
            user=user,
            customer=customer,
            target_summary={"filters": {"site": "multi-region-site"}},
            payload={"commands": ["show version"]},
        )

        # Verify job was routed to higher priority region
        job.refresh_from_db()
        assert job.region == region_us_east  # priority 100 > 90
        assert dispatched_tasks[0]["queue"] == "region_us-east-1"

    def test_job_uses_default_queue_when_no_region(self, customer, user, credential):
        """Test that jobs use default queue when devices have no region."""
        Device.objects.create(
            customer=customer,
            hostname="router-no-region",
            mgmt_ip="10.3.1.1",
            vendor="cisco",
            platform="ios",
            credential=credential,
            region=None,
            site="no-region-site",
        )

        dispatched_tasks = []

        def mock_dispatcher(task_name, args=None, queue=None):
            dispatched_tasks.append({"task": task_name, "args": args, "queue": queue})

        service = JobService(dispatcher=mock_dispatcher)
        job = service.create_job(
            job_type="run_commands",
            user=user,
            customer=customer,
            target_summary={"filters": {"site": "no-region-site"}},
            payload={"commands": ["show version"]},
        )

        # Verify job uses default queue (None)
        job.refresh_from_db()
        assert job.region is None
        assert dispatched_tasks[0]["queue"] is None

    def test_job_fallback_when_region_offline(
        self, customer, user, device_in_us_east, region_us_east
    ):
        """Test that jobs fall back to default queue when region is offline."""
        # Mark region as offline
        region_us_east.health_status = Region.STATUS_OFFLINE
        region_us_east.save()

        dispatched_tasks = []

        def mock_dispatcher(task_name, args=None, queue=None):
            dispatched_tasks.append({"task": task_name, "args": args, "queue": queue})

        service = JobService(dispatcher=mock_dispatcher)
        job = service.create_job(
            job_type="run_commands",
            user=user,
            customer=customer,
            target_summary={"filters": {"site": "us-east-datacenter"}},
            payload={"commands": ["show version"]},
        )

        # Verify job falls back to default queue
        job.refresh_from_db()
        assert job.region is None
        assert dispatched_tasks[0]["queue"] is None

    def test_job_specific_device_routing(self, customer, user, device_in_us_east, region_us_east):
        """Test routing when targeting specific device IDs."""
        dispatched_tasks = []

        def mock_dispatcher(task_name, args=None, queue=None):
            dispatched_tasks.append({"task": task_name, "args": args, "queue": queue})

        service = JobService(dispatcher=mock_dispatcher)
        job = service.create_job(
            job_type="run_commands",
            user=user,
            customer=customer,
            target_summary={"filters": {"device_ids": [device_in_us_east.id]}},
            payload={"commands": ["show version"]},
        )

        # Verify job was routed to device's region
        job.refresh_from_db()
        assert job.region == region_us_east
        assert dispatched_tasks[0]["queue"] == "region_us-east-1"


@pytest.mark.django_db
class TestDeviceRegionAssignment:
    """Test device region assignment."""

    def test_device_with_region(self, device_in_us_east, region_us_east):
        """Test device with assigned region."""
        assert device_in_us_east.region == region_us_east

    def test_device_without_region(self, customer, credential):
        """Test device without assigned region."""
        device = Device.objects.create(
            customer=customer,
            hostname="router-no-region",
            mgmt_ip="10.5.1.1",
            vendor="cisco",
            platform="ios",
            credential=credential,
        )
        assert device.region is None

    def test_update_device_region(self, device_in_us_east, region_us_west):
        """Test updating device region."""
        device_in_us_east.region = region_us_west
        device_in_us_east.save()
        device_in_us_east.refresh_from_db()
        assert device_in_us_east.region == region_us_west

    def test_device_api_includes_region(self, user, device_in_us_east):
        """Test that device API response includes region."""
        client = APIClient()
        client.force_login(user)
        response = client.get(f"/api/v1/devices/{device_in_us_east.id}/")
        assert response.status_code == 200
        assert response.json()["region"] == device_in_us_east.region.id
