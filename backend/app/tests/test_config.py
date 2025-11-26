"""Tests for config API endpoints."""

from unittest.mock import patch, MagicMock

from app.db.models import ConfigSnapshot, Device, Job


class TestConfigBackup:
    """Tests for config backup endpoint."""

    def test_backup_config_requires_auth(self, client):
        """Test that backup requires authentication."""
        response = client.post(
            "/api/v1/config/backup",
            json={"targets": {"hostnames": ["router1"]}, "source_label": "manual"},
        )
        assert response.status_code == 403

    def test_backup_config_viewer_forbidden(self, client, viewer_headers):
        """Test that viewers cannot trigger backup."""
        response = client.post(
            "/api/v1/config/backup",
            json={"targets": {"hostnames": ["router1"]}, "source_label": "manual"},
            headers=viewer_headers,
        )
        assert response.status_code == 403

    @patch("app.api.config.celery_app.send_task")
    def test_backup_config_operator_success(
        self, mock_send_task, client, operator_headers, db_session
    ):
        """Test that operators can trigger config backup."""
        mock_send_task.return_value = MagicMock()

        response = client.post(
            "/api/v1/config/backup",
            json={"targets": {"hostnames": ["router1"]}, "source_label": "manual"},
            headers=operator_headers,
        )

        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "queued"
        mock_send_task.assert_called_once()

    @patch("app.api.config.celery_app.send_task")
    def test_backup_config_creates_job(
        self, mock_send_task, client, operator_headers, db_session, test_customer
    ):
        """Test that backup creates a job record."""
        mock_send_task.return_value = MagicMock()

        response = client.post(
            "/api/v1/config/backup",
            json={"targets": {"vendors": ["cisco"]}, "source_label": "scheduled"},
            headers=operator_headers,
        )

        assert response.status_code == 202
        job_id = response.json()["job_id"]

        # Verify job was created
        job = db_session.query(Job).filter(Job.id == job_id).first()
        assert job is not None
        assert job.type == "config_backup"
        assert job.customer_id == test_customer.id


class TestConfigSnapshots:
    """Tests for config snapshot endpoints."""

    def test_get_snapshot_requires_auth(self, client):
        """Test that getting snapshot requires authentication."""
        response = client.get("/api/v1/config/snapshots/1")
        assert response.status_code == 403

    def test_get_snapshot_success(
        self, client, auth_headers, db_session, test_device, test_customer
    ):
        """Test getting a specific snapshot."""
        snapshot = ConfigSnapshot(
            device_id=test_device.id,
            source="manual",
            config_text="hostname router1\ninterface Gi0/0",
            hash="abc123",
        )
        db_session.add(snapshot)
        db_session.commit()
        db_session.refresh(snapshot)

        response = client.get(f"/api/v1/config/snapshots/{snapshot.id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == snapshot.id
        assert data["device_id"] == test_device.id
        assert data["source"] == "manual"
        assert "hostname router1" in data["config_text"]

    def test_get_snapshot_not_found(self, client, auth_headers):
        """Test getting non-existent snapshot."""
        response = client.get("/api/v1/config/snapshots/99999", headers=auth_headers)
        assert response.status_code == 404

    def test_get_snapshot_wrong_customer(
        self, client, auth_headers, db_session, second_customer, test_credential
    ):
        """Test that users cannot access snapshots from other customers."""
        # Create device in second customer
        device = Device(
            hostname="other-router",
            mgmt_ip="10.0.0.1",
            vendor="cisco",
            platform="ios",
            credentials_ref=test_credential.id,
            customer_id=second_customer.id,
            enabled=True,
        )
        db_session.add(device)
        db_session.commit()
        db_session.refresh(device)

        snapshot = ConfigSnapshot(
            device_id=device.id,
            source="manual",
            config_text="hostname other",
            hash="xyz789",
        )
        db_session.add(snapshot)
        db_session.commit()
        db_session.refresh(snapshot)

        response = client.get(f"/api/v1/config/snapshots/{snapshot.id}", headers=auth_headers)
        assert response.status_code == 404


class TestDeviceSnapshots:
    """Tests for device-specific snapshot endpoints."""

    def test_list_device_snapshots_requires_auth(self, client):
        """Test that listing snapshots requires authentication."""
        response = client.get("/api/v1/config/devices/1/snapshots")
        assert response.status_code == 403

    def test_list_device_snapshots_success(self, client, auth_headers, db_session, test_device):
        """Test listing snapshots for a device."""
        # Create multiple snapshots
        for i in range(3):
            snapshot = ConfigSnapshot(
                device_id=test_device.id,
                source="scheduled",
                config_text=f"config version {i}",
                hash=f"hash{i}",
            )
            db_session.add(snapshot)
        db_session.commit()

        response = client.get(
            f"/api/v1/config/devices/{test_device.id}/snapshots", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert all("id" in s and "source" in s and "hash" in s for s in data)

    def test_list_device_snapshots_with_limit(self, client, auth_headers, db_session, test_device):
        """Test limiting snapshot list."""
        for i in range(5):
            snapshot = ConfigSnapshot(
                device_id=test_device.id,
                source="scheduled",
                config_text=f"config {i}",
                hash=f"h{i}",
            )
            db_session.add(snapshot)
        db_session.commit()

        response = client.get(
            f"/api/v1/config/devices/{test_device.id}/snapshots?limit=2",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_list_device_snapshots_empty(self, client, auth_headers, db_session, test_device):
        """Test listing snapshots for device with none."""
        response = client.get(
            f"/api/v1/config/devices/{test_device.id}/snapshots", headers=auth_headers
        )

        assert response.status_code == 200
        assert response.json() == []


class TestConfigDiff:
    """Tests for config diff endpoint."""

    def test_config_diff_requires_auth(self, client):
        """Test that diff requires authentication."""
        response = client.get("/api/v1/config/devices/1/diff?from=1&to=2")
        assert response.status_code == 403

    def test_config_diff_success(self, client, auth_headers, db_session, test_device):
        """Test getting diff between two snapshots."""
        snap1 = ConfigSnapshot(
            device_id=test_device.id,
            source="manual",
            config_text="hostname router1\ninterface Gi0/0\n ip address 10.0.0.1 255.255.255.0",
            hash="hash1",
        )
        snap2 = ConfigSnapshot(
            device_id=test_device.id,
            source="manual",
            config_text="hostname router1\ninterface Gi0/0\n ip address 10.0.0.2 255.255.255.0",
            hash="hash2",
        )
        db_session.add(snap1)
        db_session.add(snap2)
        db_session.commit()
        db_session.refresh(snap1)
        db_session.refresh(snap2)

        response = client.get(
            f"/api/v1/config/devices/{test_device.id}/diff?from={snap1.id}&to={snap2.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "diff" in data
        assert "from_snapshot" in data
        assert "to_snapshot" in data

    def test_config_diff_missing_params(self, client, auth_headers, test_device):
        """Test diff with missing parameters."""
        response = client.get(f"/api/v1/config/devices/{test_device.id}/diff", headers=auth_headers)
        assert response.status_code == 422  # Validation error


class TestConfigDeploy:
    """Tests for config deploy endpoints."""

    def test_deploy_preview_requires_auth(self, client):
        """Test that deploy preview requires authentication."""
        response = client.post(
            "/api/v1/config/deploy/preview",
            json={
                "targets": {"hostnames": ["router1"]},
                "mode": "merge",
                "snippet": "hostname newname",
            },
        )
        assert response.status_code == 403

    def test_deploy_preview_viewer_forbidden(self, client, viewer_headers):
        """Test that viewers cannot preview deploy."""
        response = client.post(
            "/api/v1/config/deploy/preview",
            json={
                "targets": {"hostnames": ["router1"]},
                "mode": "merge",
                "snippet": "hostname newname",
            },
            headers=viewer_headers,
        )
        assert response.status_code == 403

    @patch("app.api.config.celery_app.send_task")
    def test_deploy_preview_success(self, mock_send_task, client, operator_headers, db_session):
        """Test successful deploy preview."""
        mock_send_task.return_value = MagicMock()

        response = client.post(
            "/api/v1/config/deploy/preview",
            json={
                "targets": {"hostnames": ["router1"]},
                "mode": "merge",
                "snippet": "hostname newname",
            },
            headers=operator_headers,
        )

        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "queued"
        mock_send_task.assert_called_once()

    def test_deploy_commit_requires_auth(self, client):
        """Test that deploy commit requires authentication."""
        response = client.post(
            "/api/v1/config/deploy/commit", json={"previous_job_id": 1, "confirm": True}
        )
        assert response.status_code == 403

    def test_deploy_commit_viewer_forbidden(self, client, viewer_headers):
        """Test that viewers cannot commit deploy."""
        response = client.post(
            "/api/v1/config/deploy/commit",
            json={"previous_job_id": 1, "confirm": True},
            headers=viewer_headers,
        )
        assert response.status_code == 403

    @patch("app.api.config.celery_app.send_task")
    def test_deploy_commit_requires_preview_job(
        self, mock_send_task, client, operator_headers, db_session, operator_user, test_customer
    ):
        """Test that commit requires a successful preview job."""
        # Create a non-preview job
        job = Job(
            type="run_commands",
            status="success",
            user_id=operator_user.id,
            customer_id=test_customer.id,
            target_summary_json={"filters": {"hostnames": ["router1"]}},
            payload_json={"commands": ["show version"]},
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        response = client.post(
            "/api/v1/config/deploy/commit",
            json={"previous_job_id": job.id, "confirm": True},
            headers=operator_headers,
        )

        assert response.status_code == 422
        assert "not a preview job" in response.json()["detail"].lower()

    @patch("app.api.config.celery_app.send_task")
    def test_deploy_commit_requires_successful_preview(
        self, mock_send_task, client, operator_headers, db_session, operator_user, test_customer
    ):
        """Test that commit requires preview job to be successful."""
        # Create a failed preview job
        job = Job(
            type="config_deploy_preview",
            status="failed",
            user_id=operator_user.id,
            customer_id=test_customer.id,
            target_summary_json={"filters": {"hostnames": ["router1"]}},
            payload_json={"mode": "merge", "snippet": "hostname test"},
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        response = client.post(
            "/api/v1/config/deploy/commit",
            json={"previous_job_id": job.id, "confirm": True},
            headers=operator_headers,
        )

        assert response.status_code == 422
        assert "must be successful" in response.json()["detail"].lower()

    @patch("app.api.config.celery_app.send_task")
    def test_deploy_commit_success(
        self, mock_send_task, client, operator_headers, db_session, operator_user, test_customer
    ):
        """Test successful deploy commit."""
        mock_send_task.return_value = MagicMock()

        # Create a successful preview job
        preview_job = Job(
            type="config_deploy_preview",
            status="success",
            user_id=operator_user.id,
            customer_id=test_customer.id,
            target_summary_json={"filters": {"hostnames": ["router1"]}},
            payload_json={"mode": "merge", "snippet": "hostname newname"},
        )
        db_session.add(preview_job)
        db_session.commit()
        db_session.refresh(preview_job)

        response = client.post(
            "/api/v1/config/deploy/commit",
            json={"previous_job_id": preview_job.id, "confirm": True},
            headers=operator_headers,
        )

        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "queued"
        mock_send_task.assert_called_once()


class TestConfigRollback:
    """Tests for config rollback endpoints."""

    def test_rollback_preview_requires_auth(self, client):
        """Test that rollback preview requires authentication."""
        response = client.post("/api/v1/config/rollback/preview", json={"snapshot_id": 1})
        assert response.status_code == 403

    def test_rollback_preview_viewer_forbidden(self, client, viewer_headers):
        """Test that viewers cannot trigger rollback preview."""
        response = client.post(
            "/api/v1/config/rollback/preview",
            json={"snapshot_id": 1},
            headers=viewer_headers,
        )
        assert response.status_code == 403

    def test_rollback_preview_snapshot_not_found(self, client, operator_headers):
        """Test that rollback preview fails with non-existent snapshot."""
        response = client.post(
            "/api/v1/config/rollback/preview",
            json={"snapshot_id": 99999},
            headers=operator_headers,
        )
        assert response.status_code == 404

    @patch("app.api.config.celery_app.send_task")
    def test_rollback_preview_success(
        self, mock_send_task, client, operator_headers, db_session, test_device
    ):
        """Test successful rollback preview."""
        mock_send_task.return_value = MagicMock()

        # Create a snapshot
        snapshot = ConfigSnapshot(
            device_id=test_device.id,
            source="manual",
            config_text="hostname router1\ninterface Gi0/0\n",
            hash="abc123",
        )
        db_session.add(snapshot)
        db_session.commit()
        db_session.refresh(snapshot)

        response = client.post(
            "/api/v1/config/rollback/preview",
            json={"snapshot_id": snapshot.id},
            headers=operator_headers,
        )

        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "queued"
        mock_send_task.assert_called_once()

    def test_rollback_commit_requires_auth(self, client):
        """Test that rollback commit requires authentication."""
        response = client.post(
            "/api/v1/config/rollback/commit", json={"previous_job_id": 1, "confirm": True}
        )
        assert response.status_code == 403

    def test_rollback_commit_viewer_forbidden(self, client, viewer_headers):
        """Test that viewers cannot commit rollback."""
        response = client.post(
            "/api/v1/config/rollback/commit",
            json={"previous_job_id": 1, "confirm": True},
            headers=viewer_headers,
        )
        assert response.status_code == 403

    @patch("app.api.config.celery_app.send_task")
    def test_rollback_commit_requires_preview_job(
        self, mock_send_task, client, operator_headers, db_session, operator_user, test_customer
    ):
        """Test that rollback commit requires a rollback preview job."""
        # Create a non-rollback-preview job
        job = Job(
            type="run_commands",
            status="success",
            user_id=operator_user.id,
            customer_id=test_customer.id,
            target_summary_json={"filters": {"hostnames": ["router1"]}},
            payload_json={"commands": ["show version"]},
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        response = client.post(
            "/api/v1/config/rollback/commit",
            json={"previous_job_id": job.id, "confirm": True},
            headers=operator_headers,
        )

        assert response.status_code == 422
        assert "not a rollback preview job" in response.json()["detail"].lower()

    @patch("app.api.config.celery_app.send_task")
    def test_rollback_commit_requires_successful_preview(
        self, mock_send_task, client, operator_headers, db_session, operator_user, test_customer
    ):
        """Test that rollback commit requires preview to be successful."""
        # Create a failed rollback preview job
        job = Job(
            type="config_rollback_preview",
            status="failed",
            user_id=operator_user.id,
            customer_id=test_customer.id,
            target_summary_json={"snapshot_id": 1, "device_id": 1},
            payload_json={"snapshot_id": 1, "config_text": "hostname test"},
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        response = client.post(
            "/api/v1/config/rollback/commit",
            json={"previous_job_id": job.id, "confirm": True},
            headers=operator_headers,
        )

        assert response.status_code == 422
        assert "must be successful" in response.json()["detail"].lower()

    @patch("app.api.config.celery_app.send_task")
    def test_rollback_commit_requires_confirmation(
        self, mock_send_task, client, operator_headers, db_session, operator_user, test_customer
    ):
        """Test that rollback commit requires explicit confirmation."""
        mock_send_task.return_value = MagicMock()

        # Create a successful rollback preview job
        preview_job = Job(
            type="config_rollback_preview",
            status="success",
            user_id=operator_user.id,
            customer_id=test_customer.id,
            target_summary_json={"snapshot_id": 1, "device_id": 1},
            payload_json={"snapshot_id": 1, "config_text": "hostname test"},
        )
        db_session.add(preview_job)
        db_session.commit()
        db_session.refresh(preview_job)

        response = client.post(
            "/api/v1/config/rollback/commit",
            json={"previous_job_id": preview_job.id, "confirm": False},
            headers=operator_headers,
        )

        assert response.status_code == 422
        assert "confirmation required" in response.json()["detail"].lower()

    @patch("app.api.config.celery_app.send_task")
    def test_rollback_commit_success(
        self, mock_send_task, client, operator_headers, db_session, operator_user, test_customer
    ):
        """Test successful rollback commit."""
        mock_send_task.return_value = MagicMock()

        # Create a successful rollback preview job
        preview_job = Job(
            type="config_rollback_preview",
            status="success",
            user_id=operator_user.id,
            customer_id=test_customer.id,
            target_summary_json={"snapshot_id": 1, "device_id": 1},
            payload_json={"snapshot_id": 1, "config_text": "hostname test"},
        )
        db_session.add(preview_job)
        db_session.commit()
        db_session.refresh(preview_job)

        response = client.post(
            "/api/v1/config/rollback/commit",
            json={"previous_job_id": preview_job.id, "confirm": True},
            headers=operator_headers,
        )

        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "queued"
        mock_send_task.assert_called_once()
