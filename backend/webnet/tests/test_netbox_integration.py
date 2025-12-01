"""Tests for NetBox Integration (Issue #9)."""

import pytest
from unittest.mock import patch, MagicMock
from django.urls import reverse
from rest_framework import status

from webnet.devices.models import NetBoxConfig, NetBoxSyncLog, Device


@pytest.fixture
def netbox_config(db, customer, credential):
    """Create a test NetBox configuration."""
    config = NetBoxConfig(
        customer=customer,
        name="Test NetBox",
        api_url="https://netbox.example.com/api",
        sync_frequency="manual",
        enabled=True,
        status_filter="active",
        default_credential=credential,
    )
    config.api_token = "test-api-token-12345"
    config.save()
    return config


@pytest.fixture
def mock_netbox_response():
    """Mock NetBox API response with devices."""
    return {
        "count": 2,
        "next": None,
        "previous": None,
        "results": [
            {
                "id": 1,
                "name": "router-1",
                "device_type": {"manufacturer": {"name": "Cisco"}},
                "platform": {"name": "cisco_ios"},
                "role": {"name": "router"},
                "site": {"name": "Site-A"},
                "primary_ip4": {"address": "192.168.1.1/24"},
                "url": "https://netbox.example.com/api/dcim/devices/1/",
            },
            {
                "id": 2,
                "name": "switch-1",
                "device_type": {"manufacturer": {"name": "Cisco"}},
                "platform": {"name": "cisco_ios"},
                "role": {"name": "switch"},
                "site": {"name": "Site-A"},
                "primary_ip4": {"address": "192.168.1.2/24"},
                "url": "https://netbox.example.com/api/dcim/devices/2/",
            },
        ],
    }


class TestNetBoxConfigModel:
    """Tests for NetBoxConfig model."""

    def test_api_token_encryption(self, netbox_config):
        """Test that API token is encrypted."""
        # Token should be encrypted in DB
        assert netbox_config._api_token != "test-api-token-12345"
        # But decrypted when accessed
        assert netbox_config.api_token == "test-api-token-12345"

    def test_has_api_token(self, netbox_config):
        """Test has_api_token method."""
        assert netbox_config.has_api_token() is True

    def test_get_site_filters(self, db, customer, credential):
        """Test parsing site filters."""
        config = NetBoxConfig(
            customer=customer,
            api_url="https://netbox.example.com/api",
            site_filter="site-a, site-b, site-c",
            default_credential=credential,
        )
        config.api_token = "token"
        config.save()

        filters = config.get_site_filters()
        assert len(filters) == 3
        assert "site-a" in filters
        assert "site-b" in filters

    def test_get_empty_filters(self, netbox_config):
        """Test getting empty filters returns empty list."""
        assert netbox_config.get_site_filters() == []
        assert netbox_config.get_tenant_filters() == []
        assert netbox_config.get_role_filters() == []


class TestNetBoxService:
    """Tests for NetBoxService."""

    @patch("webnet.devices.netbox_service.httpx.Client")
    def test_test_connection_success(self, mock_client, netbox_config):
        """Test successful connection test."""
        from webnet.devices.netbox_service import NetBoxService

        mock_response = MagicMock()
        mock_response.json.return_value = {"version": "3.5.0"}
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = MagicMock()
        mock_client_instance.get.return_value = mock_response
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_client.return_value = mock_client_instance

        service = NetBoxService(netbox_config)
        result = service.test_connection()

        assert result.success is True
        assert "successfully" in result.message.lower()

    @patch("webnet.devices.netbox_service.httpx.Client")
    def test_map_device(self, mock_client, netbox_config, mock_netbox_response):
        """Test mapping NetBox device to webnet format."""
        from webnet.devices.netbox_service import NetBoxService

        service = NetBoxService(netbox_config)
        nb_device = mock_netbox_response["results"][0]
        mapped = service._map_device(nb_device)

        assert mapped["hostname"] == "router-1"
        assert mapped["vendor"] == "Cisco"
        assert mapped["platform"] == "cisco_ios"
        assert mapped["role"] == "router"
        assert mapped["site"] == "Site-A"
        assert mapped["mgmt_ip"] == "192.168.1.1"  # CIDR stripped
        assert mapped["netbox_id"] == 1

    @patch("webnet.devices.netbox_service.httpx.Client")
    def test_preview_sync(self, mock_client, netbox_config, mock_netbox_response):
        """Test preview sync operation."""
        from webnet.devices.netbox_service import NetBoxService

        mock_response = MagicMock()
        mock_response.json.return_value = mock_netbox_response
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = MagicMock()
        mock_client_instance.get.return_value = mock_response
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_client.return_value = mock_client_instance

        service = NetBoxService(netbox_config)
        result = service.preview_sync()

        assert result.total == 2
        assert result.would_create == 2
        assert result.would_update == 0
        assert len(result.devices) == 2

    @patch("webnet.devices.netbox_service.httpx.Client")
    def test_sync_devices_creates_new(self, mock_client, netbox_config, mock_netbox_response):
        """Test sync creates new devices."""
        from webnet.devices.netbox_service import NetBoxService

        mock_response = MagicMock()
        mock_response.json.return_value = mock_netbox_response
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = MagicMock()
        mock_client_instance.get.return_value = mock_response
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_client.return_value = mock_client_instance

        service = NetBoxService(netbox_config)
        result = service.sync_devices()

        assert result.success is True
        assert result.created == 2
        assert result.updated == 0

        # Check devices were created
        assert Device.objects.filter(customer=netbox_config.customer, hostname="router-1").exists()
        assert Device.objects.filter(customer=netbox_config.customer, hostname="switch-1").exists()

        # Check sync log was created
        assert NetBoxSyncLog.objects.filter(config=netbox_config).exists()


@pytest.mark.django_db
class TestNetBoxAPI:
    """Tests for NetBox API endpoints."""

    def test_list_configs(self, api_client, admin_user, netbox_config):
        """Test listing NetBox configurations."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.get(reverse("netbox-config-list"))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_create_config(self, api_client, admin_user, customer, credential):
        """Test creating a new NetBox configuration."""
        api_client.force_authenticate(user=admin_user)
        data = {
            "customer": customer.id,
            "name": "New NetBox",
            "api_url": "https://netbox2.example.com/api",
            "api_token": "new-token-12345",
            "sync_frequency": "daily",
            "enabled": True,
            "default_credential": credential.id,
        }
        response = api_client.post(reverse("netbox-config-list"), data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "New NetBox"
        assert response.data["has_api_token"] is True

    def test_update_config(self, api_client, admin_user, netbox_config):
        """Test updating a NetBox configuration."""
        api_client.force_authenticate(user=admin_user)
        data = {"name": "Updated NetBox", "sync_frequency": "hourly"}
        response = api_client.patch(
            reverse("netbox-config-detail", args=[netbox_config.id]),
            data,
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Updated NetBox"
        assert response.data["sync_frequency"] == "hourly"

    def test_delete_config(self, api_client, admin_user, netbox_config):
        """Test deleting a NetBox configuration."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.delete(reverse("netbox-config-detail", args=[netbox_config.id]))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not NetBoxConfig.objects.filter(id=netbox_config.id).exists()

    @patch("webnet.devices.netbox_service.NetBoxService.test_connection")
    def test_test_connection_endpoint(self, mock_test, api_client, admin_user, netbox_config):
        """Test the test-connection action endpoint."""
        from webnet.devices.netbox_service import ConnectionTestResult

        mock_test.return_value = ConnectionTestResult(
            success=True,
            message="Successfully connected",
            netbox_version="3.5.0",
        )

        api_client.force_authenticate(user=admin_user)
        response = api_client.post(
            reverse("netbox-config-test-connection", args=[netbox_config.id])
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True

    @patch("webnet.jobs.tasks.netbox_sync_job.delay")
    def test_sync_endpoint(self, mock_delay, api_client, admin_user, netbox_config):
        """Test the sync action endpoint."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.post(
            reverse("netbox-config-sync", args=[netbox_config.id]),
            {"full_sync": False},
            format="json",
        )
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert "queued" in response.data["detail"].lower()
        mock_delay.assert_called_once_with(netbox_config.id, full_sync=False)

    def test_sync_disabled_config(self, api_client, admin_user, netbox_config):
        """Test syncing a disabled configuration returns error."""
        netbox_config.enabled = False
        netbox_config.save()

        api_client.force_authenticate(user=admin_user)
        response = api_client.post(reverse("netbox-config-sync", args=[netbox_config.id]))
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "disabled" in response.data["detail"].lower()

    def test_logs_endpoint(self, api_client, admin_user, netbox_config):
        """Test the logs action endpoint."""
        # Create some sync logs
        NetBoxSyncLog.objects.create(
            config=netbox_config,
            status="success",
            devices_created=5,
            message="Sync completed",
        )

        api_client.force_authenticate(user=admin_user)
        response = api_client.get(reverse("netbox-config-logs", args=[netbox_config.id]))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
        assert response.data[0]["devices_created"] == 5

    def test_tenant_isolation(self, api_client, operator_user, netbox_config, other_customer):
        """Test that operators can't see other customer's configs."""
        from webnet.devices.models import Credential

        # Create credential for other customer
        other_cred = Credential(
            customer=other_customer,
            name="Other Cred",
            username="user",
        )
        other_cred.password = "pass"
        other_cred.save()

        # Create config for other customer
        other_config = NetBoxConfig(
            customer=other_customer,
            name="Other NetBox",
            api_url="https://other.example.com/api",
            default_credential=other_cred,
        )
        other_config.api_token = "other-token"
        other_config.save()

        api_client.force_authenticate(user=operator_user)
        response = api_client.get(reverse("netbox-config-list"))
        assert response.status_code == status.HTTP_200_OK

        # Handle paginated and non-paginated responses
        results = response.data.get("results", response.data)
        if isinstance(results, dict):
            results = [results]

        # Should not see the other customer's config
        config_ids = [c["id"] for c in results]
        assert other_config.id not in config_ids
