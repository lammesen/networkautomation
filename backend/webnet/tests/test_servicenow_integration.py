"""Tests for ServiceNow Integration."""

import pytest
from unittest.mock import patch, MagicMock
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from webnet.devices.models import (
    ServiceNowConfig,
    ServiceNowIncident,
    Device,
)
from webnet.jobs.models import Job


@pytest.fixture
def servicenow_config(db, customer, credential):
    """Create a test ServiceNow configuration."""
    config = ServiceNowConfig(
        customer=customer,
        name="Test ServiceNow",
        instance_url="https://dev12345.service-now.com",
        username="admin",
        sync_frequency="manual",
        auto_sync_enabled=True,
        bidirectional_sync=True,
        cmdb_table="cmdb_ci_netgear",
        default_credential=credential,
        create_incidents_on_failure=True,
        incident_category="Network",
        create_changes_on_deploy=True,
        change_category="Network",
    )
    config.password = "test-password-12345"
    config.save()
    return config


@pytest.fixture
def mock_servicenow_ci_response():
    """Mock ServiceNow API response with CIs."""
    return {
        "result": [
            {
                "sys_id": "abc123",
                "name": "router-1",
                "ip_address": "192.168.1.1",
                "manufacturer": {"display_value": "Cisco"},
                "os": "IOS-XE",
                "location": {"display_value": "Site-A"},
                "u_role": "router",
            },
            {
                "sys_id": "def456",
                "name": "switch-1",
                "ip_address": "192.168.1.2",
                "manufacturer": {"display_value": "Cisco"},
                "os": "IOS",
                "location": {"display_value": "Site-A"},
                "u_role": "switch",
            },
        ]
    }


@pytest.fixture
def mock_servicenow_incident_response():
    """Mock ServiceNow incident creation response."""
    return {"result": {"sys_id": "inc123", "number": "INC0012345"}}


@pytest.fixture
def mock_servicenow_change_response():
    """Mock ServiceNow change request creation response."""
    return {"result": {"sys_id": "chg123", "number": "CHG0012345"}}


class TestServiceNowConfigModel:
    """Tests for ServiceNowConfig model."""

    def test_password_encryption(self, servicenow_config):
        """Test that password is encrypted."""
        # Password should be encrypted in DB
        assert servicenow_config._password != "test-password-12345"
        # But decrypted when accessed
        assert servicenow_config.password == "test-password-12345"

    def test_has_password(self, servicenow_config):
        """Test has_password method."""
        assert servicenow_config.has_password() is True

    def test_config_str(self, servicenow_config):
        """Test string representation."""
        assert str(servicenow_config) == f"{servicenow_config.customer.name} - Test ServiceNow"


class TestServiceNowService:
    """Tests for ServiceNowService."""

    @patch("webnet.devices.servicenow_service.httpx.Client")
    def test_test_connection_success(self, mock_client, servicenow_config):
        """Test successful connection test."""
        from webnet.devices.servicenow_service import ServiceNowService

        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": [{"sys_id": "123"}]}
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = MagicMock()
        mock_client_instance.request.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance

        service = ServiceNowService(servicenow_config)
        result = service.test_connection()

        assert result.success is True
        assert "Successfully connected" in result.message

    @patch("webnet.devices.servicenow_service.httpx.Client")
    def test_test_connection_auth_failure(self, mock_client, servicenow_config):
        """Test connection test with authentication failure."""
        from webnet.devices.servicenow_service import ServiceNowService
        from httpx import HTTPStatusError, Response, Request

        # Mock 401 response
        request = Request("GET", "https://test.service-now.com/api/now/table/sys_user")
        response = Response(401, request=request)
        mock_client_instance = MagicMock()
        mock_client_instance.request.side_effect = HTTPStatusError(
            "Unauthorized", request=request, response=response
        )
        mock_client.return_value.__enter__.return_value = mock_client_instance

        service = ServiceNowService(servicenow_config)
        result = service.test_connection()

        assert result.success is False
        assert "Authentication failed" in result.message

    @patch("webnet.devices.servicenow_service.httpx.Client")
    def test_fetch_cis(self, mock_client, servicenow_config, mock_servicenow_ci_response):
        """Test fetching CIs from ServiceNow."""
        from webnet.devices.servicenow_service import ServiceNowService

        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = mock_servicenow_ci_response
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = MagicMock()
        mock_client_instance.request.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance

        service = ServiceNowService(servicenow_config)
        cis = service.fetch_cis()

        assert len(cis) == 2
        assert cis[0]["name"] == "router-1"
        assert cis[1]["name"] == "switch-1"

    @patch("webnet.devices.servicenow_service.httpx.Client")
    def test_export_device_to_cmdb_create(
        self, mock_client, servicenow_config, device, mock_servicenow_ci_response
    ):
        """Test exporting a device to ServiceNow CMDB (create)."""
        from webnet.devices.servicenow_service import ServiceNowService

        # Mock CI creation response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {"sys_id": "new123", "name": device.hostname}
        }
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = MagicMock()
        mock_client_instance.request.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance

        service = ServiceNowService(servicenow_config)
        result = service.export_device_to_cmdb(device)

        assert result.success is True
        assert result.created == 1
        assert result.updated == 0

        # Check that sys_id was stored in tags
        device.refresh_from_db()
        assert device.tags.get("servicenow_sys_id") == "new123"

    @patch("webnet.devices.servicenow_service.httpx.Client")
    def test_export_device_to_cmdb_update(self, mock_client, servicenow_config, device):
        """Test exporting a device to ServiceNow CMDB (update existing)."""
        from webnet.devices.servicenow_service import ServiceNowService

        # Set existing sys_id
        device.tags = {"servicenow_sys_id": "existing123"}
        device.save()

        # Mock CI update response
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": {"sys_id": "existing123"}}
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = MagicMock()
        mock_client_instance.request.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance

        service = ServiceNowService(servicenow_config)
        result = service.export_device_to_cmdb(device)

        assert result.success is True
        assert result.created == 0
        assert result.updated == 1

    @patch("webnet.devices.servicenow_service.httpx.Client")
    def test_import_ci_to_device_create(
        self, mock_client, servicenow_config, mock_servicenow_ci_response
    ):
        """Test importing a CI from ServiceNow as a new device."""
        from webnet.devices.servicenow_service import ServiceNowService

        service = ServiceNowService(servicenow_config)
        ci = mock_servicenow_ci_response["result"][0]

        result = service.import_ci_to_device(ci)

        assert result.success is True
        assert result.created == 1
        assert result.updated == 0

        # Check device was created
        device = Device.objects.get(customer=servicenow_config.customer, hostname="router-1")
        assert device.mgmt_ip == "192.168.1.1"
        assert device.vendor == "Cisco"
        assert device.platform == "IOS-XE"
        assert device.tags["servicenow_sys_id"] == "abc123"

    @patch("webnet.devices.servicenow_service.httpx.Client")
    def test_import_ci_to_device_skip_existing(
        self, mock_client, servicenow_config, device, mock_servicenow_ci_response
    ):
        """Test importing a CI that already exists as a device."""
        from webnet.devices.servicenow_service import ServiceNowService

        service = ServiceNowService(servicenow_config)
        ci = mock_servicenow_ci_response["result"][0]
        ci["name"] = device.hostname  # Use existing device hostname

        # Disable bidirectional sync to skip updates
        servicenow_config.bidirectional_sync = False
        servicenow_config.save()

        result = service.import_ci_to_device(ci)

        assert result.success is True
        assert result.created == 0
        assert result.updated == 0
        assert result.skipped == 1

    @patch("webnet.devices.servicenow_service.httpx.Client")
    def test_create_incident(
        self, mock_client, servicenow_config, mock_servicenow_incident_response
    ):
        """Test creating an incident in ServiceNow."""
        from webnet.devices.servicenow_service import ServiceNowService

        # Mock incident creation response
        mock_response = MagicMock()
        mock_response.json.return_value = mock_servicenow_incident_response
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = MagicMock()
        mock_client_instance.request.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance

        service = ServiceNowService(servicenow_config)
        result = service.create_incident(
            short_description="Test Incident",
            description="Test incident description",
            impact=2,
            urgency=2,
        )

        assert result.success is True
        assert result.incident_number == "INC0012345"
        assert result.incident_sys_id == "inc123"

    @patch("webnet.devices.servicenow_service.httpx.Client")
    def test_create_change_request(
        self, mock_client, servicenow_config, mock_servicenow_change_response
    ):
        """Test creating a change request in ServiceNow."""
        from webnet.devices.servicenow_service import ServiceNowService

        # Mock change request creation response
        mock_response = MagicMock()
        mock_response.json.return_value = mock_servicenow_change_response
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = MagicMock()
        mock_client_instance.request.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance

        service = ServiceNowService(servicenow_config)
        result = service.create_change_request(
            short_description="Test Change",
            description="Test change description",
            justification="Business need",
            risk=3,
            impact=3,
        )

        assert result.success is True
        assert result.change_number == "CHG0012345"
        assert result.change_sys_id == "chg123"


class TestServiceNowConfigAPI:
    """Tests for ServiceNow configuration API endpoints."""

    @pytest.fixture
    def authenticated_client(self, api_client, admin_user):
        """Create an authenticated API client."""
        api_client.force_authenticate(user=admin_user)
        return api_client

    def test_create_servicenow_config(self, authenticated_client, customer, credential):
        """Test creating a ServiceNow configuration."""
        url = reverse("servicenow-config-list")
        data = {
            "customer": customer.id,
            "name": "Test ServiceNow",
            "instance_url": "https://dev12345.service-now.com",
            "username": "admin",
            "password": "test-password",
            "cmdb_table": "cmdb_ci_netgear",
            "sync_frequency": "manual",
            "auto_sync_enabled": False,
            "default_credential": credential.id,
        }

        response = authenticated_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "Test ServiceNow"
        assert response.data["has_password"] is True

    def test_list_servicenow_configs(self, authenticated_client, servicenow_config):
        """Test listing ServiceNow configurations."""
        url = reverse("servicenow-config-list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    @patch("webnet.devices.servicenow_service.ServiceNowService.test_connection")
    def test_test_connection_endpoint(
        self, mock_test_connection, authenticated_client, servicenow_config
    ):
        """Test the connection test endpoint."""
        from webnet.devices.servicenow_service import ConnectionTestResult

        # Mock successful connection test
        mock_test_connection.return_value = ConnectionTestResult(
            success=True, message="Connection successful", servicenow_version="Xanadu"
        )

        url = reverse("servicenow-config-test-connection", args=[servicenow_config.id])
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert "successful" in response.data["message"].lower()

    @patch("webnet.jobs.tasks.servicenow_sync_job.delay")
    def test_sync_endpoint(self, mock_task, authenticated_client, servicenow_config):
        """Test the manual sync trigger endpoint."""
        url = reverse("servicenow-config-sync", args=[servicenow_config.id])
        data = {"direction": "both"}

        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert "queued" in response.data["detail"].lower()
        mock_task.assert_called_once()


class TestServiceNowIncidentAPI:
    """Tests for ServiceNow incident API endpoints."""

    @pytest.fixture
    def authenticated_client(self, api_client, admin_user):
        """Create an authenticated API client."""
        api_client.force_authenticate(user=admin_user)
        return api_client

    @pytest.fixture
    def job(self, db, customer, admin_user):
        """Create a test job."""
        return Job.objects.create(
            customer=customer,
            user=admin_user,
            type="config_backup",
            status="failed",
            started_at=timezone.now(),
            finished_at=timezone.now(),
        )

    @pytest.fixture
    def incident(self, db, servicenow_config, job):
        """Create a test incident."""
        return ServiceNowIncident.objects.create(
            config=servicenow_config,
            job=job,
            incident_number="INC0012345",
            incident_sys_id="inc123",
            state=ServiceNowIncident.STATE_NEW,
            short_description="Test Incident",
            description="Test incident description",
        )

    def test_list_incidents(self, authenticated_client, incident):
        """Test listing ServiceNow incidents."""
        url = reverse("servicenow-incident-list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    @patch("webnet.devices.servicenow_service.ServiceNowService.update_incident")
    def test_update_incident_state(self, mock_update, authenticated_client, incident):
        """Test updating an incident's state."""
        from webnet.devices.servicenow_service import IncidentResult

        # Mock successful update
        mock_update.return_value = IncidentResult(
            success=True, incident_number="INC0012345", message="Updated"
        )

        url = reverse("servicenow-incident-update-state", args=[incident.id])
        data = {"state": ServiceNowIncident.STATE_RESOLVED, "resolution_notes": "Fixed"}

        response = authenticated_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True

        # Check incident was updated locally
        incident.refresh_from_db()
        assert incident.state == ServiceNowIncident.STATE_RESOLVED
        assert incident.resolved_at is not None


class TestServiceNowTasks:
    """Tests for ServiceNow Celery tasks."""

    @patch("webnet.devices.servicenow_service.ServiceNowService.sync_to_cmdb")
    @patch("webnet.devices.servicenow_service.ServiceNowService.sync_from_cmdb")
    def test_servicenow_sync_job_both_directions(
        self, mock_import, mock_export, servicenow_config
    ):
        """Test ServiceNow sync job with both directions."""
        from webnet.jobs.tasks import servicenow_sync_job
        from webnet.devices.servicenow_service import SyncResult

        # Mock sync results
        mock_export.return_value = SyncResult(
            success=True, message="Exported", created=1, updated=0
        )
        mock_import.return_value = SyncResult(
            success=True, message="Imported", created=1, updated=0
        )

        result = servicenow_sync_job(servicenow_config.id, direction="both")

        assert result["success"] is True
        assert len(result["results"]) == 2
        mock_export.assert_called_once()
        mock_import.assert_called_once()

    @patch("webnet.devices.servicenow_service.ServiceNowService.sync_to_cmdb")
    def test_servicenow_sync_job_export_only(self, mock_export, servicenow_config):
        """Test ServiceNow sync job with export only."""
        from webnet.jobs.tasks import servicenow_sync_job
        from webnet.devices.servicenow_service import SyncResult

        mock_export.return_value = SyncResult(
            success=True, message="Exported", created=1, updated=0
        )

        result = servicenow_sync_job(servicenow_config.id, direction="export")

        assert result["success"] is True
        assert len(result["results"]) == 1
        assert result["results"][0]["direction"] == "export"

    @patch("webnet.devices.servicenow_service.ServiceNowService.create_incident")
    def test_create_servicenow_incident_task(self, mock_create, servicenow_config, admin_user):
        """Test automatic incident creation task."""
        from webnet.jobs.tasks import create_servicenow_incident
        from webnet.jobs.models import Job
        from webnet.devices.servicenow_service import IncidentResult

        # Create a failed job
        job = Job.objects.create(
            customer=servicenow_config.customer,
            user=admin_user,
            type="config_backup",
            status="failed",
            started_at=timezone.now(),
            finished_at=timezone.now(),
            result_summary_json={"error": "Connection timeout"},
        )

        # Mock incident creation
        mock_create.return_value = IncidentResult(
            success=True, incident_number="INC0012345", incident_sys_id="inc123"
        )

        result = create_servicenow_incident(job.id)

        assert result["success"] is True
        assert result["incident_number"] == "INC0012345"

        # Check incident was created locally
        incident = ServiceNowIncident.objects.get(job=job)
        assert incident.incident_number == "INC0012345"
        assert incident.incident_sys_id == "inc123"

    def test_create_incident_no_config(self, db):
        """Test incident creation when no ServiceNow config exists."""
        from webnet.jobs.tasks import create_servicenow_incident
        from webnet.jobs.models import Job
        from webnet.customers.models import Customer
        from webnet.users.models import User

        customer = Customer.objects.create(name="Test Customer")
        user = User.objects.create_user(username="test", password="test")

        job = Job.objects.create(
            customer=customer,
            user=user,
            type="config_backup",
            status="failed",
            started_at=timezone.now(),
            finished_at=timezone.now(),
        )

        result = create_servicenow_incident(job.id)

        assert result["success"] is False
        assert "No incident creation config" in result["error"]
