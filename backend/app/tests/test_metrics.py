"""Tests for Prometheus metrics module."""

import time

import pytest
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from app.core.metrics import (
    AUTH_LOGIN_ATTEMPTS_TOTAL,
    COMPLIANCE_CHECK_TOTAL,
    CONFIG_BACKUPS_TOTAL,
    DEVICES_REACHABLE,
    DEVICES_TOTAL,
    DEVICES_UNREACHABLE,
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_IN_PROGRESS,
    HTTP_REQUESTS_TOTAL,
    JOB_DURATION_SECONDS,
    JOBS_IN_PROGRESS,
    JOBS_TOTAL,
    WEBSOCKET_CONNECTIONS,
    record_compliance_check,
    record_config_backup,
    record_job_completed,
    record_job_created,
    record_login_attempt,
    set_app_info,
    track_request_metrics,
    update_device_counts,
    update_reachability_counts,
    update_websocket_connections,
)
from app.main import app


@pytest.fixture(autouse=True)
def reset_metrics() -> None:
    """Reset metric values before each test.

    Note: Prometheus metrics are singletons, so we can't fully reset them.
    We work around this by using unique label combinations in tests.
    """
    pass


class TestMetricsEndpoint:
    """Tests for the /metrics endpoint."""

    def test_metrics_endpoint_returns_prometheus_format(self, client: TestClient) -> None:
        """Test that /metrics returns Prometheus text format."""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]

    def test_metrics_endpoint_contains_app_info(self, client: TestClient) -> None:
        """Test that metrics include application info."""
        response = client.get("/metrics")
        assert response.status_code == 200
        content = response.text
        assert "netauto_app_info" in content

    def test_metrics_endpoint_contains_http_metrics(self, client: TestClient) -> None:
        """Test that metrics include HTTP request metrics."""
        # Make a request to generate HTTP metrics
        client.get("/health")

        response = client.get("/metrics")
        assert response.status_code == 200
        content = response.text
        assert "netauto_http_requests_total" in content
        assert "netauto_http_request_duration_seconds" in content

    def test_metrics_endpoint_contains_job_metrics(self, client: TestClient) -> None:
        """Test that metrics include job-related metrics."""
        response = client.get("/metrics")
        assert response.status_code == 200
        content = response.text
        # Check metric definitions exist
        assert "netauto_jobs_total" in content or "# HELP netauto_jobs" in content

    def test_metrics_endpoint_contains_device_metrics(self, client: TestClient) -> None:
        """Test that metrics include device-related metrics."""
        response = client.get("/metrics")
        assert response.status_code == 200
        content = response.text
        # Check metric definitions exist
        assert "netauto_devices" in content or "# HELP netauto_devices" in content


class TestAppInfoMetric:
    """Tests for application info metric."""

    def test_set_app_info(self) -> None:
        """Test setting application info metric."""
        set_app_info("1.0.0", "test")

        # Verify the metric was set by checking registry
        sample = REGISTRY.get_sample_value(
            "netauto_app_info", {"version": "1.0.0", "environment": "test"}
        )
        assert sample == 1.0


class TestHTTPRequestMetrics:
    """Tests for HTTP request metrics."""

    @pytest.mark.asyncio
    async def test_track_request_metrics_decorator_async(self) -> None:
        """Test the async request metrics decorator."""

        @track_request_metrics("GET", "/test/async")
        async def async_handler() -> str:
            return "ok"

        # Run the decorated function
        result = await async_handler()
        assert result == "ok"

        # Check metrics were recorded
        sample = REGISTRY.get_sample_value(
            "netauto_http_requests_total",
            {"method": "GET", "endpoint": "/test/async", "status_code": "200"},
        )
        assert sample is not None and sample >= 1

    def test_track_request_metrics_decorator_sync(self) -> None:
        """Test the sync request metrics decorator."""

        @track_request_metrics("POST", "/test/sync")
        def sync_handler() -> str:
            return "ok"

        result = sync_handler()
        assert result == "ok"

        sample = REGISTRY.get_sample_value(
            "netauto_http_requests_total",
            {"method": "POST", "endpoint": "/test/sync", "status_code": "200"},
        )
        assert sample is not None and sample >= 1

    def test_track_request_metrics_records_duration(self) -> None:
        """Test that request duration is recorded."""

        @track_request_metrics("GET", "/test/duration")
        def slow_handler() -> str:
            time.sleep(0.01)  # 10ms
            return "ok"

        slow_handler()

        # Check histogram has observations
        sample = REGISTRY.get_sample_value(
            "netauto_http_request_duration_seconds_count",
            {"method": "GET", "endpoint": "/test/duration"},
        )
        assert sample is not None and sample >= 1

    def test_track_request_metrics_on_exception(self) -> None:
        """Test metrics are recorded even on exceptions."""

        @track_request_metrics("GET", "/test/error")
        def error_handler() -> str:
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            error_handler()

        sample = REGISTRY.get_sample_value(
            "netauto_http_requests_total",
            {"method": "GET", "endpoint": "/test/error", "status_code": "500"},
        )
        assert sample is not None and sample >= 1


class TestAuthenticationMetrics:
    """Tests for authentication metrics."""

    def test_record_login_success(self) -> None:
        """Test recording successful login."""
        initial = (
            REGISTRY.get_sample_value("netauto_auth_login_attempts_total", {"status": "success"})
            or 0
        )

        record_login_attempt(success=True)

        new_value = REGISTRY.get_sample_value(
            "netauto_auth_login_attempts_total", {"status": "success"}
        )
        assert new_value == initial + 1

    def test_record_login_failure(self) -> None:
        """Test recording failed login."""
        initial = (
            REGISTRY.get_sample_value("netauto_auth_login_attempts_total", {"status": "failure"})
            or 0
        )

        record_login_attempt(success=False)

        new_value = REGISTRY.get_sample_value(
            "netauto_auth_login_attempts_total", {"status": "failure"}
        )
        assert new_value == initial + 1


class TestJobMetrics:
    """Tests for job metrics."""

    def test_record_job_created(self) -> None:
        """Test recording job creation."""
        initial_total = (
            REGISTRY.get_sample_value(
                "netauto_jobs_total", {"job_type": "test_job", "status": "created"}
            )
            or 0
        )
        initial_in_progress = (
            REGISTRY.get_sample_value("netauto_jobs_in_progress", {"job_type": "test_job"}) or 0
        )

        record_job_created("test_job")

        new_total = REGISTRY.get_sample_value(
            "netauto_jobs_total", {"job_type": "test_job", "status": "created"}
        )
        new_in_progress = REGISTRY.get_sample_value(
            "netauto_jobs_in_progress", {"job_type": "test_job"}
        )

        assert new_total == initial_total + 1
        assert new_in_progress == initial_in_progress + 1

    def test_record_job_completed_success(self) -> None:
        """Test recording successful job completion."""
        # First create a job
        record_job_created("completed_job")

        initial_success = (
            REGISTRY.get_sample_value(
                "netauto_jobs_total", {"job_type": "completed_job", "status": "success"}
            )
            or 0
        )

        record_job_completed("completed_job", success=True, duration_seconds=5.0)

        new_success = REGISTRY.get_sample_value(
            "netauto_jobs_total", {"job_type": "completed_job", "status": "success"}
        )
        assert new_success == initial_success + 1

        # Check duration was recorded
        duration_count = REGISTRY.get_sample_value(
            "netauto_job_duration_seconds_count",
            {"job_type": "completed_job", "status": "success"},
        )
        assert duration_count is not None and duration_count >= 1

    def test_record_job_completed_failure(self) -> None:
        """Test recording failed job completion."""
        record_job_created("failed_job")

        initial_failure = (
            REGISTRY.get_sample_value(
                "netauto_jobs_total", {"job_type": "failed_job", "status": "failure"}
            )
            or 0
        )

        record_job_completed("failed_job", success=False, duration_seconds=2.0)

        new_failure = REGISTRY.get_sample_value(
            "netauto_jobs_total", {"job_type": "failed_job", "status": "failure"}
        )
        assert new_failure == initial_failure + 1


class TestComplianceMetrics:
    """Tests for compliance metrics."""

    def test_record_compliance_check_pass(self) -> None:
        """Test recording passing compliance check."""
        initial = (
            REGISTRY.get_sample_value(
                "netauto_compliance_checks_total", {"policy": "test_policy", "status": "pass"}
            )
            or 0
        )

        record_compliance_check("test_policy", passed=True)

        new_value = REGISTRY.get_sample_value(
            "netauto_compliance_checks_total", {"policy": "test_policy", "status": "pass"}
        )
        assert new_value == initial + 1

    def test_record_compliance_check_fail(self) -> None:
        """Test recording failing compliance check."""
        initial = (
            REGISTRY.get_sample_value(
                "netauto_compliance_checks_total", {"policy": "test_policy", "status": "fail"}
            )
            or 0
        )

        record_compliance_check("test_policy", passed=False)

        new_value = REGISTRY.get_sample_value(
            "netauto_compliance_checks_total", {"policy": "test_policy", "status": "fail"}
        )
        assert new_value == initial + 1


class TestConfigBackupMetrics:
    """Tests for config backup metrics."""

    def test_record_config_backup_success(self) -> None:
        """Test recording successful config backup."""
        initial = (
            REGISTRY.get_sample_value(
                "netauto_config_backups_total", {"source": "manual", "status": "success"}
            )
            or 0
        )

        record_config_backup("manual", success=True)

        new_value = REGISTRY.get_sample_value(
            "netauto_config_backups_total", {"source": "manual", "status": "success"}
        )
        assert new_value == initial + 1

    def test_record_config_backup_failure(self) -> None:
        """Test recording failed config backup."""
        initial = (
            REGISTRY.get_sample_value(
                "netauto_config_backups_total", {"source": "scheduled", "status": "failure"}
            )
            or 0
        )

        record_config_backup("scheduled", success=False)

        new_value = REGISTRY.get_sample_value(
            "netauto_config_backups_total", {"source": "scheduled", "status": "failure"}
        )
        assert new_value == initial + 1


class TestDeviceMetrics:
    """Tests for device metrics."""

    def test_update_device_counts(self) -> None:
        """Test updating device counts."""
        update_device_counts("test_customer", "cisco", "ios", 10)

        value = REGISTRY.get_sample_value(
            "netauto_devices_total",
            {"customer": "test_customer", "vendor": "cisco", "platform": "ios"},
        )
        assert value == 10

    def test_update_reachability_counts(self) -> None:
        """Test updating device reachability counts."""
        update_reachability_counts("test_customer2", reachable=8, unreachable=2)

        reachable = REGISTRY.get_sample_value(
            "netauto_devices_reachable", {"customer": "test_customer2"}
        )
        unreachable = REGISTRY.get_sample_value(
            "netauto_devices_unreachable", {"customer": "test_customer2"}
        )

        assert reachable == 8
        assert unreachable == 2


class TestWebSocketMetrics:
    """Tests for WebSocket metrics."""

    def test_update_websocket_connections(self) -> None:
        """Test updating WebSocket connection count."""
        update_websocket_connections("ssh", 5)

        value = REGISTRY.get_sample_value("netauto_websocket_connections", {"type": "ssh"})
        assert value == 5

    def test_update_websocket_connections_job_logs(self) -> None:
        """Test updating job logs WebSocket connections."""
        update_websocket_connections("job_logs", 3)

        value = REGISTRY.get_sample_value("netauto_websocket_connections", {"type": "job_logs"})
        assert value == 3
