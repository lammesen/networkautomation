"""Tests for ConfigService."""

import pytest
import hashlib

from app.db.models import ConfigSnapshot
from app.domain.context import TenantRequestContext
from app.domain.exceptions import NotFoundError, ValidationError
from app.services.config_service import ConfigService


@pytest.fixture
def test_snapshot(db_session, test_device):
    """Create a test configuration snapshot."""
    config_text = "hostname test-router\ninterface Ethernet1\n  ip address 10.0.0.1/24"
    snapshot = ConfigSnapshot(
        device_id=test_device.id,
        source="manual",
        config_text=config_text,
        hash=hashlib.sha256(config_text.encode()).hexdigest(),
    )
    db_session.add(snapshot)
    db_session.commit()
    db_session.refresh(snapshot)
    return snapshot


@pytest.fixture
def second_snapshot(db_session, test_device):
    """Create a second configuration snapshot for diff tests."""
    config_text = "hostname test-router\ninterface Ethernet1\n  ip address 10.0.0.2/24\ninterface Ethernet2\n  ip address 10.0.1.1/24"
    snapshot = ConfigSnapshot(
        device_id=test_device.id,
        source="manual",
        config_text=config_text,
        hash=hashlib.sha256(config_text.encode()).hexdigest(),
    )
    db_session.add(snapshot)
    db_session.commit()
    db_session.refresh(snapshot)
    return snapshot


class TestConfigService:
    """Tests for configuration snapshot operations."""

    def test_get_snapshot_success(self, db_session, test_customer, test_snapshot, admin_user):
        """Test getting a snapshot by ID."""
        service = ConfigService(db_session)
        context = TenantRequestContext(user=admin_user, customer=test_customer)

        snapshot = service.get_snapshot(test_snapshot.id, context)

        assert snapshot.id == test_snapshot.id
        assert snapshot.config_text == test_snapshot.config_text

    def test_get_snapshot_not_found(self, db_session, test_customer, admin_user):
        """Test getting non-existent snapshot raises NotFoundError."""
        service = ConfigService(db_session)
        context = TenantRequestContext(user=admin_user, customer=test_customer)

        with pytest.raises(NotFoundError):
            service.get_snapshot(99999, context)

    def test_get_snapshot_wrong_customer(
        self, db_session, second_customer, test_snapshot, admin_user
    ):
        """Test getting snapshot from wrong customer raises NotFoundError."""
        service = ConfigService(db_session)
        context = TenantRequestContext(user=admin_user, customer=second_customer)

        with pytest.raises(NotFoundError):
            service.get_snapshot(test_snapshot.id, context)

    def test_list_device_snapshots(
        self, db_session, test_customer, test_device, test_snapshot, admin_user
    ):
        """Test listing snapshots for a device."""
        service = ConfigService(db_session)
        context = TenantRequestContext(user=admin_user, customer=test_customer)

        snapshots = service.list_device_snapshots(test_device.id, context)

        assert len(snapshots) >= 1
        assert any(s.id == test_snapshot.id for s in snapshots)

    def test_list_device_snapshots_device_not_found(self, db_session, test_customer, admin_user):
        """Test listing snapshots for non-existent device raises NotFoundError."""
        service = ConfigService(db_session)
        context = TenantRequestContext(user=admin_user, customer=test_customer)

        with pytest.raises(NotFoundError):
            service.list_device_snapshots(99999, context)

    def test_list_device_snapshots_wrong_customer(
        self, db_session, second_customer, test_device, admin_user
    ):
        """Test listing snapshots for device in wrong customer raises NotFoundError."""
        service = ConfigService(db_session)
        context = TenantRequestContext(user=admin_user, customer=second_customer)

        with pytest.raises(NotFoundError):
            service.list_device_snapshots(test_device.id, context)

    def test_list_device_snapshots_with_limit(
        self, db_session, test_customer, test_device, test_snapshot, second_snapshot, admin_user
    ):
        """Test listing snapshots with limit."""
        service = ConfigService(db_session)
        context = TenantRequestContext(user=admin_user, customer=test_customer)

        snapshots = service.list_device_snapshots(test_device.id, context, limit=1)

        assert len(snapshots) == 1


class TestConfigDiff:
    """Tests for configuration diff functionality."""

    def test_get_config_diff(
        self, db_session, test_customer, test_device, test_snapshot, second_snapshot, admin_user
    ):
        """Test getting diff between two snapshots."""
        service = ConfigService(db_session)
        context = TenantRequestContext(user=admin_user, customer=test_customer)

        diff = service.get_config_diff(
            test_device.id,
            test_snapshot.id,
            second_snapshot.id,
            context,
        )

        assert diff["device_id"] == test_device.id
        assert diff["from_snapshot"] == test_snapshot.id
        assert diff["to_snapshot"] == second_snapshot.id
        assert "diff" in diff
        assert isinstance(diff["diff"], str)
        # Should contain diff markers
        assert "10.0.0.1" in diff["diff"] or "10.0.0.2" in diff["diff"]

    def test_get_config_diff_device_not_found(
        self, db_session, test_customer, test_snapshot, second_snapshot, admin_user
    ):
        """Test getting diff for non-existent device raises NotFoundError."""
        service = ConfigService(db_session)
        context = TenantRequestContext(user=admin_user, customer=test_customer)

        with pytest.raises(NotFoundError):
            service.get_config_diff(99999, test_snapshot.id, second_snapshot.id, context)

    def test_get_config_diff_snapshot_not_found(
        self, db_session, test_customer, test_device, test_snapshot, admin_user
    ):
        """Test getting diff with non-existent snapshot raises NotFoundError."""
        service = ConfigService(db_session)
        context = TenantRequestContext(user=admin_user, customer=test_customer)

        with pytest.raises(NotFoundError):
            service.get_config_diff(test_device.id, test_snapshot.id, 99999, context)

    def test_get_config_diff_wrong_device(
        self, db_session, test_customer, test_device, test_snapshot, test_credential, admin_user
    ):
        """Test getting diff with snapshots from wrong device raises ValidationError."""
        from app.db.models import Device
        import hashlib

        service = ConfigService(db_session)
        context = TenantRequestContext(user=admin_user, customer=test_customer)

        # Create another device and its snapshot
        device2 = Device(
            hostname="other-router",
            mgmt_ip="192.168.1.100",
            vendor="cisco",
            platform="ios",
            credentials_ref=test_credential.id,
            customer_id=test_customer.id,
            enabled=True,
        )
        db_session.add(device2)
        db_session.commit()

        config_text = "hostname other-router"
        other_snapshot = ConfigSnapshot(
            device_id=device2.id,
            source="manual",
            config_text=config_text,
            hash=hashlib.sha256(config_text.encode()).hexdigest(),
        )
        db_session.add(other_snapshot)
        db_session.commit()

        with pytest.raises(ValidationError):
            service.get_config_diff(
                test_device.id,
                test_snapshot.id,
                other_snapshot.id,
                context,
            )
