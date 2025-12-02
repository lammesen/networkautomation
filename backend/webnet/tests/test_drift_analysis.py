"""Tests for configuration drift analysis feature."""

import pytest
from webnet.config_mgmt.models import ConfigSnapshot, ConfigDrift
from webnet.config_mgmt.drift_service import DriftService
from webnet.devices.models import Device


@pytest.fixture
def drift_service():
    """Return a DriftService instance."""
    return DriftService()


@pytest.fixture
def device_with_snapshots(db, customer, operator_user, credential):
    """Create a device with multiple snapshots."""
    device = Device.objects.create(
        customer=customer,
        hostname="test-router",
        mgmt_ip="192.168.1.1",
        vendor="cisco",
        platform="ios",
        credential=credential,
    )

    # Create initial snapshot
    snap1 = ConfigSnapshot.objects.create(
        device=device,
        source="manual",
        config_text="interface GigabitEthernet0/1\n ip address 10.0.0.1 255.255.255.0\n!",
    )

    # Create second snapshot with changes
    snap2 = ConfigSnapshot.objects.create(
        device=device,
        source="manual",
        config_text="interface GigabitEthernet0/1\n ip address 10.0.0.2 255.255.255.0\n description WAN\n!",
    )

    # Create third snapshot with more changes
    snap3 = ConfigSnapshot.objects.create(
        device=device,
        source="manual",
        config_text="interface GigabitEthernet0/1\n ip address 10.0.0.2 255.255.255.0\n description WAN-Link\n shutdown\n!",
    )

    return device, [snap1, snap2, snap3]


@pytest.mark.django_db
class TestDriftDetection:
    """Test drift detection functionality."""

    def test_detect_drift_no_changes(self, drift_service, device_with_snapshots, operator_user):
        """Test drift detection when there are no changes."""
        device, snapshots = device_with_snapshots

        # Create identical snapshots
        snap1 = ConfigSnapshot.objects.create(
            device=device,
            source="manual",
            config_text="hostname test-router\n!",
        )
        snap2 = ConfigSnapshot.objects.create(
            device=device,
            source="manual",
            config_text="hostname test-router\n!",
        )

        drift = drift_service.detect_drift(snap1, snap2, operator_user)

        assert drift is not None
        assert drift.has_changes is False
        assert drift.additions == 0
        assert drift.deletions == 0
        assert drift.changes == 0

    def test_detect_drift_with_changes(self, drift_service, device_with_snapshots, operator_user):
        """Test drift detection with actual changes."""
        device, snapshots = device_with_snapshots
        snap1, snap2, snap3 = snapshots

        drift = drift_service.detect_drift(snap1, snap2, operator_user)

        assert drift is not None
        assert drift.has_changes is True
        assert drift.additions > 0
        assert drift.device == device
        assert drift.snapshot_from == snap1
        assert drift.snapshot_to == snap2
        assert drift.triggered_by == operator_user

    def test_detect_drift_idempotent(self, drift_service, device_with_snapshots, operator_user):
        """Test that detecting drift twice returns the same record."""
        device, snapshots = device_with_snapshots
        snap1, snap2, snap3 = snapshots

        drift1 = drift_service.detect_drift(snap1, snap2, operator_user)
        drift2 = drift_service.detect_drift(snap1, snap2, operator_user)

        assert drift1.id == drift2.id

    def test_detect_consecutive_drifts(self, drift_service, device_with_snapshots, operator_user):
        """Test detecting drift for consecutive snapshots."""
        device, snapshots = device_with_snapshots

        drifts = drift_service.detect_consecutive_drifts(device.id, operator_user)

        # Should create 2 drifts (snap1->snap2, snap2->snap3)
        assert len(drifts) == 2
        assert all(isinstance(d, ConfigDrift) for d in drifts)
        assert drifts[0].snapshot_from == snapshots[0]
        assert drifts[0].snapshot_to == snapshots[1]
        assert drifts[1].snapshot_from == snapshots[1]
        assert drifts[1].snapshot_to == snapshots[2]

    def test_change_magnitude(self, drift_service, device_with_snapshots, operator_user):
        """Test change magnitude calculation."""
        device, snapshots = device_with_snapshots
        snap1, snap2, snap3 = snapshots

        # Minor changes
        drift = drift_service.detect_drift(snap1, snap2, operator_user)
        assert drift.get_change_magnitude() in ["No changes", "Minor changes", "Moderate changes"]

        # Create snapshots with many changes for major test
        large_config_1 = "\n".join([f"line {i}" for i in range(100)])
        large_config_2 = "\n".join([f"line {i} modified" for i in range(100)])

        snap_large_1 = ConfigSnapshot.objects.create(
            device=device,
            source="manual",
            config_text=large_config_1,
        )
        snap_large_2 = ConfigSnapshot.objects.create(
            device=device,
            source="manual",
            config_text=large_config_2,
        )

        drift_large = drift_service.detect_drift(snap_large_1, snap_large_2, operator_user)
        assert drift_large.get_change_magnitude() == "Major changes"


@pytest.mark.django_db
class TestDriftAlerts:
    """Test drift alert functionality."""

    def test_analyze_drift_for_alert_minor_changes(
        self, drift_service, device_with_snapshots, operator_user
    ):
        """Test that minor changes don't create alerts."""
        device, snapshots = device_with_snapshots
        snap1, snap2, snap3 = snapshots

        drift = drift_service.detect_drift(snap1, snap2, operator_user)
        alert = drift_service.analyze_drift_for_alert(drift, threshold=50)

        # Minor changes should not create alert
        assert alert is None

    def test_analyze_drift_for_alert_major_changes(
        self, drift_service, device_with_snapshots, operator_user
    ):
        """Test that major changes create alerts."""
        device, snapshots = device_with_snapshots

        # Create snapshots with many changes
        large_config_1 = "\n".join([f"line {i}" for i in range(100)])
        large_config_2 = "\n".join([f"different line {i}" for i in range(100)])

        snap1 = ConfigSnapshot.objects.create(
            device=device,
            source="manual",
            config_text=large_config_1,
        )
        snap2 = ConfigSnapshot.objects.create(
            device=device,
            source="manual",
            config_text=large_config_2,
        )

        drift = drift_service.detect_drift(snap1, snap2, operator_user)
        alert = drift_service.analyze_drift_for_alert(drift, threshold=50)

        assert alert is not None
        assert alert.drift == drift
        assert alert.severity in ["warning", "critical"]
        assert alert.status == "open"

    def test_analyze_drift_for_alert_idempotent(
        self, drift_service, device_with_snapshots, operator_user
    ):
        """Test that analyzing drift twice doesn't create duplicate alerts."""
        device, snapshots = device_with_snapshots

        # Create large change
        large_config_1 = "\n".join([f"line {i}" for i in range(100)])
        large_config_2 = "\n".join([f"different line {i}" for i in range(100)])

        snap1 = ConfigSnapshot.objects.create(
            device=device,
            source="manual",
            config_text=large_config_1,
        )
        snap2 = ConfigSnapshot.objects.create(
            device=device,
            source="manual",
            config_text=large_config_2,
        )

        drift = drift_service.detect_drift(snap1, snap2, operator_user)
        alert1 = drift_service.analyze_drift_for_alert(drift, threshold=50)
        alert2 = drift_service.analyze_drift_for_alert(drift, threshold=50)

        assert alert1.id == alert2.id


@pytest.mark.django_db
class TestDriftTimeline:
    """Test drift timeline and statistics."""

    def test_get_drift_timeline(self, drift_service, device_with_snapshots, operator_user):
        """Test getting drift timeline for a device."""
        device, snapshots = device_with_snapshots

        # Create some drifts
        drift_service.detect_consecutive_drifts(device.id, operator_user)

        timeline = drift_service.get_drift_timeline(device.id, days=30)

        assert len(timeline) >= 2
        assert all(isinstance(d, ConfigDrift) for d in timeline)
        assert all(d.device_id == device.id for d in timeline)

    def test_get_change_frequency(self, drift_service, device_with_snapshots, operator_user):
        """Test change frequency statistics."""
        device, snapshots = device_with_snapshots

        # Create some drifts
        drift_service.detect_consecutive_drifts(device.id, operator_user)

        stats = drift_service.get_change_frequency(device.id, days=30)

        assert "total_changes" in stats
        assert "total_additions" in stats
        assert "total_deletions" in stats
        assert "avg_changes_per_drift" in stats
        assert "days_analyzed" in stats
        assert stats["days_analyzed"] == 30


@pytest.mark.django_db
class TestDriftAPI:
    """Test drift API endpoints."""

    def test_detect_drift_api(self, client, operator_user, device_with_snapshots):
        """Test drift detection API endpoint."""
        device, snapshots = device_with_snapshots
        snap1, snap2, snap3 = snapshots

        client.force_login(operator_user)
        response = client.post(
            "/api/v1/config/drift/detect",
            {
                "snapshot_from_id": snap1.id,
                "snapshot_to_id": snap2.id,
            },
            content_type="application/json",
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["snapshot_from"] == snap1.id
        assert data["snapshot_to"] == snap2.id
        assert "has_changes" in data

    def test_analyze_device_api(self, client, operator_user, device_with_snapshots):
        """Test device drift analysis API endpoint."""
        device, snapshots = device_with_snapshots

        client.force_login(operator_user)
        response = client.post(
            "/api/v1/config/drift/analyze-device",
            {"device_id": device.id},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["device_id"] == device.id
        assert "drifts_analyzed" in data
        assert "drifts" in data

    def test_device_drifts_api(self, client, operator_user, device_with_snapshots):
        """Test getting device drifts API endpoint."""
        device, snapshots = device_with_snapshots

        # Create drifts first
        ds = DriftService()
        ds.detect_consecutive_drifts(device.id, operator_user)

        client.force_login(operator_user)
        response = client.get(f"/api/v1/config/drift/device/{device.id}")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    def test_change_frequency_api(self, client, operator_user, device_with_snapshots):
        """Test change frequency API endpoint."""
        device, snapshots = device_with_snapshots

        # Create drifts first
        ds = DriftService()
        ds.detect_consecutive_drifts(device.id, operator_user)

        client.force_login(operator_user)
        response = client.get(f"/api/v1/config/drift/device/{device.id}/frequency")

        assert response.status_code == 200
        data = response.json()
        assert "total_changes" in data
        assert "total_additions" in data
        assert "total_deletions" in data


@pytest.mark.django_db
class TestDriftUI:
    """Test drift UI views."""

    def test_drift_timeline_view(self, client, operator_user, device_with_snapshots):
        """Test drift timeline UI view."""
        device, snapshots = device_with_snapshots

        # Create drifts first
        ds = DriftService()
        ds.detect_consecutive_drifts(device.id, operator_user)

        client.force_login(operator_user)
        response = client.get(f"/config/drift/timeline?device_id={device.id}")

        assert response.status_code == 200
        assert b"Configuration Drift Timeline" in response.content
        assert device.hostname.encode() in response.content

    def test_drift_detail_view(self, client, operator_user, device_with_snapshots):
        """Test drift detail UI view."""
        device, snapshots = device_with_snapshots

        # Create drift
        ds = DriftService()
        drifts = ds.detect_consecutive_drifts(device.id, operator_user)
        drift = drifts[0]

        client.force_login(operator_user)
        response = client.get(f"/config/drift/{drift.id}/")

        assert response.status_code == 200
        assert b"Configuration Drift Detail" in response.content
        assert device.hostname.encode() in response.content

    def test_drift_alerts_view(self, client, operator_user, device_with_snapshots):
        """Test drift alerts UI view."""
        device, snapshots = device_with_snapshots

        client.force_login(operator_user)
        response = client.get("/config/drift/alerts")

        assert response.status_code == 200
        assert b"Configuration Drift Alerts" in response.content
