"""Tests for DeviceService."""

import pytest
from pydantic import BaseModel
from typing import Optional

from app.db.models import Device
from app.domain.context import TenantRequestContext
from app.domain.devices import DeviceFilters
from app.domain.exceptions import ConflictError, NotFoundError, ValidationError
from app.services.device_service import DeviceService


class DeviceCreatePayload(BaseModel):
    """Mock payload for device creation."""

    hostname: str
    mgmt_ip: str
    vendor: str
    platform: str
    credentials_ref: int
    role: Optional[str] = None
    site: Optional[str] = None
    enabled: bool = True


class DeviceUpdatePayload(BaseModel):
    """Mock payload for device update."""

    hostname: Optional[str] = None
    mgmt_ip: Optional[str] = None
    vendor: Optional[str] = None
    platform: Optional[str] = None
    credentials_ref: Optional[int] = None
    role: Optional[str] = None
    site: Optional[str] = None
    enabled: Optional[bool] = None


class TestDeviceService:
    """Tests for device CRUD operations."""

    def test_list_devices(self, db_session, test_customer, test_device, admin_user):
        """Test listing devices for a customer."""
        service = DeviceService(db_session)
        context = TenantRequestContext(user=admin_user, customer=test_customer)
        filters = DeviceFilters()

        total, devices = service.list_devices(filters, context)

        assert total >= 1
        assert any(d.id == test_device.id for d in devices)

    def test_list_devices_with_filters(self, db_session, test_customer, test_device, admin_user):
        """Test listing devices with vendor filter."""
        service = DeviceService(db_session)
        context = TenantRequestContext(user=admin_user, customer=test_customer)
        filters = DeviceFilters(vendor="cisco")

        total, devices = service.list_devices(filters, context)

        assert total >= 1
        assert all(d.vendor == "cisco" for d in devices)

    def test_get_device_success(self, db_session, test_customer, test_device, admin_user):
        """Test getting a device by ID."""
        service = DeviceService(db_session)
        context = TenantRequestContext(user=admin_user, customer=test_customer)

        device = service.get_device(test_device.id, context)

        assert device.id == test_device.id
        assert device.hostname == test_device.hostname

    def test_get_device_not_found(self, db_session, test_customer, admin_user):
        """Test getting non-existent device raises NotFoundError."""
        service = DeviceService(db_session)
        context = TenantRequestContext(user=admin_user, customer=test_customer)

        with pytest.raises(NotFoundError):
            service.get_device(99999, context)

    def test_get_device_wrong_customer(self, db_session, second_customer, test_device, admin_user):
        """Test getting device from wrong customer raises NotFoundError."""
        service = DeviceService(db_session)
        context = TenantRequestContext(user=admin_user, customer=second_customer)

        with pytest.raises(NotFoundError):
            service.get_device(test_device.id, context)

    def test_create_device(self, db_session, test_customer, test_credential, admin_user):
        """Test creating a new device."""
        service = DeviceService(db_session)
        context = TenantRequestContext(user=admin_user, customer=test_customer)
        payload = DeviceCreatePayload(
            hostname="new-router",
            mgmt_ip="192.168.100.1",
            vendor="cisco",
            platform="ios",
            credentials_ref=test_credential.id,
        )

        device = service.create_device(payload, context)

        assert device.id is not None
        assert device.hostname == "new-router"
        assert device.customer_id == test_customer.id

    def test_create_device_duplicate_hostname(
        self, db_session, test_customer, test_device, test_credential, admin_user
    ):
        """Test creating device with duplicate hostname raises ConflictError."""
        service = DeviceService(db_session)
        context = TenantRequestContext(user=admin_user, customer=test_customer)
        payload = DeviceCreatePayload(
            hostname=test_device.hostname,
            mgmt_ip="192.168.100.2",
            vendor="cisco",
            platform="ios",
            credentials_ref=test_credential.id,
        )

        with pytest.raises(ConflictError):
            service.create_device(payload, context)

    def test_create_device_invalid_credential(self, db_session, test_customer, admin_user):
        """Test creating device with invalid credential raises NotFoundError."""
        service = DeviceService(db_session)
        context = TenantRequestContext(user=admin_user, customer=test_customer)
        payload = DeviceCreatePayload(
            hostname="another-router",
            mgmt_ip="192.168.100.3",
            vendor="cisco",
            platform="ios",
            credentials_ref=99999,
        )

        with pytest.raises(NotFoundError):
            service.create_device(payload, context)

    def test_update_device(self, db_session, test_customer, test_device, admin_user):
        """Test updating a device."""
        service = DeviceService(db_session)
        context = TenantRequestContext(user=admin_user, customer=test_customer)
        payload = DeviceUpdatePayload(role="core", site="datacenter-1")

        updated = service.update_device(test_device.id, payload, context)

        assert updated.role == "core"
        assert updated.site == "datacenter-1"

    def test_update_device_hostname(self, db_session, test_customer, test_device, admin_user):
        """Test updating device hostname."""
        service = DeviceService(db_session)
        context = TenantRequestContext(user=admin_user, customer=test_customer)
        payload = DeviceUpdatePayload(hostname="renamed-router")

        updated = service.update_device(test_device.id, payload, context)

        assert updated.hostname == "renamed-router"

    def test_update_device_duplicate_hostname(
        self, db_session, test_customer, test_device, test_credential, admin_user
    ):
        """Test updating device with duplicate hostname raises ConflictError."""
        service = DeviceService(db_session)
        context = TenantRequestContext(user=admin_user, customer=test_customer)

        # Create another device first
        device2 = Device(
            hostname="second-router",
            mgmt_ip="192.168.1.2",
            vendor="cisco",
            platform="ios",
            credentials_ref=test_credential.id,
            customer_id=test_customer.id,
            enabled=True,
        )
        db_session.add(device2)
        db_session.commit()

        payload = DeviceUpdatePayload(hostname="second-router")

        with pytest.raises(ConflictError):
            service.update_device(test_device.id, payload, context)

    def test_disable_device(self, db_session, test_customer, test_device, admin_user):
        """Test disabling a device."""
        service = DeviceService(db_session)
        context = TenantRequestContext(user=admin_user, customer=test_customer)

        service.disable_device(test_device.id, context)

        db_session.refresh(test_device)
        assert test_device.enabled is False


class TestDeviceImport:
    """Tests for device import functionality."""

    def test_import_devices_success(self, db_session, test_customer, test_credential, admin_user):
        """Test importing devices from CSV data."""
        service = DeviceService(db_session)
        context = TenantRequestContext(user=admin_user, customer=test_customer)

        rows = [
            {
                "hostname": "import-router-1",
                "mgmt_ip": "10.0.0.1",
                "vendor": "cisco",
                "platform": "ios",
                "credential_name": test_credential.name,
            },
            {
                "hostname": "import-router-2",
                "mgmt_ip": "10.0.0.2",
                "vendor": "juniper",
                "platform": "junos",
                "credential_name": test_credential.name,
            },
        ]

        summary = service.import_devices(rows, context)

        assert summary["created"] == 2
        assert summary["skipped"] == 0
        assert summary["failed"] == 0

    def test_import_devices_skip_duplicate(
        self, db_session, test_customer, test_device, test_credential, admin_user
    ):
        """Test importing skips devices with duplicate hostname."""
        service = DeviceService(db_session)
        context = TenantRequestContext(user=admin_user, customer=test_customer)

        rows = [
            {
                "hostname": test_device.hostname,
                "mgmt_ip": "10.0.0.5",
                "vendor": "cisco",
                "platform": "ios",
                "credential_name": test_credential.name,
            },
        ]

        summary = service.import_devices(rows, context)

        assert summary["created"] == 0
        assert summary["skipped"] == 1

    def test_import_devices_missing_fields(self, db_session, test_customer, admin_user):
        """Test importing fails for rows with missing required fields."""
        service = DeviceService(db_session)
        context = TenantRequestContext(user=admin_user, customer=test_customer)

        rows = [
            {
                "hostname": "incomplete-router",
                # Missing mgmt_ip, vendor, platform, credential_name
            },
        ]

        summary = service.import_devices(rows, context)

        assert summary["created"] == 0
        assert summary["failed"] == 1
        assert any("Missing required fields" in e for e in summary["errors"])

    def test_import_devices_invalid_credential(self, db_session, test_customer, admin_user):
        """Test importing fails for rows with invalid credential."""
        service = DeviceService(db_session)
        context = TenantRequestContext(user=admin_user, customer=test_customer)

        rows = [
            {
                "hostname": "new-router",
                "mgmt_ip": "10.0.0.10",
                "vendor": "cisco",
                "platform": "ios",
                "credential_name": "nonexistent_credential",
            },
        ]

        summary = service.import_devices(rows, context)

        assert summary["created"] == 0
        assert summary["failed"] == 1
