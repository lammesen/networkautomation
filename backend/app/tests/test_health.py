"""Tests for health check endpoints."""

from unittest.mock import MagicMock, patch


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_basic(self, client):
        """Test basic /health endpoint returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_health_live(self, client):
        """Test /health/live liveness probe returns healthy status."""
        response = client.get("/health/live")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_health_ready_all_healthy(self, client, db_session):
        """Test /health/ready when all dependencies are healthy."""
        # Mock Redis and Celery since they may not be available in test env
        with (
            patch("redis.from_url") as mock_redis_from_url,
            patch("app.celery_app.celery_app") as mock_celery,
        ):
            # Setup Redis mock
            mock_redis_instance = MagicMock()
            mock_redis_from_url.return_value = mock_redis_instance

            # Setup Celery mock - simulate 2 workers
            mock_inspect = MagicMock()
            mock_inspect.ping.return_value = {
                "celery@worker1": {"ok": "pong"},
                "celery@worker2": {"ok": "pong"},
            }
            mock_celery.control.inspect.return_value = mock_inspect

            response = client.get("/health/ready")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "dependencies" in data
            assert data["dependencies"]["database"]["status"] == "healthy"
            assert data["dependencies"]["redis"]["status"] == "healthy"
            assert data["dependencies"]["celery"]["status"] == "healthy"
            assert data["dependencies"]["celery"]["workers"] == 2

    def test_health_ready_redis_unhealthy(self, client, db_session):
        """Test /health/ready returns 503 when Redis is down."""
        with (
            patch("redis.from_url") as mock_redis_from_url,
            patch("app.celery_app.celery_app") as mock_celery,
        ):
            # Setup Redis mock to fail
            mock_redis_from_url.side_effect = Exception("Connection refused")

            # Setup Celery mock
            mock_inspect = MagicMock()
            mock_inspect.ping.return_value = None
            mock_celery.control.inspect.return_value = mock_inspect

            response = client.get("/health/ready")

            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["dependencies"]["redis"]["status"] == "unhealthy"
            assert "Connection refused" in data["dependencies"]["redis"]["error"]

    def test_health_ready_no_celery_workers(self, client, db_session):
        """Test /health/ready shows degraded celery when no workers available."""
        with (
            patch("redis.from_url") as mock_redis_from_url,
            patch("app.celery_app.celery_app") as mock_celery,
        ):
            # Setup Redis mock
            mock_redis_instance = MagicMock()
            mock_redis_from_url.return_value = mock_redis_instance

            # Setup Celery mock - no workers
            mock_inspect = MagicMock()
            mock_inspect.ping.return_value = None
            mock_celery.control.inspect.return_value = mock_inspect

            response = client.get("/health/ready")

            # Should still be healthy overall since celery is informational
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["dependencies"]["celery"]["status"] == "degraded"
            assert data["dependencies"]["celery"]["workers"] == 0

    def test_health_ready_celery_error(self, client, db_session):
        """Test /health/ready handles celery errors gracefully."""
        with (
            patch("redis.from_url") as mock_redis_from_url,
            patch("app.celery_app.celery_app") as mock_celery,
        ):
            # Setup Redis mock
            mock_redis_instance = MagicMock()
            mock_redis_from_url.return_value = mock_redis_instance

            # Setup Celery mock to throw error
            mock_celery.control.inspect.side_effect = Exception("Celery broker unreachable")

            response = client.get("/health/ready")

            # Should still be healthy overall since celery is informational
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["dependencies"]["celery"]["status"] == "unhealthy"
            assert "Celery broker unreachable" in data["dependencies"]["celery"]["error"]


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Network Automation API"
        assert "version" in data
        assert data["docs"] == "/docs"
