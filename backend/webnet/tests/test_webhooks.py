"""Tests for webhook functionality."""

from unittest.mock import patch, Mock

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from webnet.customers.models import Customer
from webnet.devices.models import Device, Credential
from webnet.jobs.models import Job
from webnet.webhooks.models import Webhook, WebhookDelivery
from webnet.webhooks.tasks import generate_signature, trigger_webhook_event

User = get_user_model()


@pytest.fixture
def customer():
    """Create a test customer."""
    return Customer.objects.create(name="Acme Corp")


@pytest.fixture
def user(customer):
    """Create a test user."""
    user = User.objects.create_user(username="admin", password="secret123", role="admin")
    user.customers.add(customer)
    return user


@pytest.fixture
def api_client(user):
    """Create authenticated API client."""
    client = APIClient()
    client.login(username="admin", password="secret123")
    return client


@pytest.fixture
def webhook(customer, user):
    """Create a test webhook."""
    webhook = Webhook.objects.create(
        customer=customer,
        name="Test Webhook",
        url="https://example.com/webhook",
        event_types=["job.completed", "device.created"],
        enabled=True,
        created_by=user,
    )
    webhook.secret = "test-secret-key"
    webhook.save()
    return webhook


@pytest.mark.django_db
class TestWebhookAPI:
    """Test webhook API endpoints."""

    def test_list_webhooks(self, api_client, webhook):
        """Test listing webhooks."""
        response = api_client.get("/api/v1/webhooks/")
        assert response.status_code == 200
        data = response.json()
        # DRF paginated response
        assert data["count"] == 1
        assert data["results"][0]["name"] == "Test Webhook"
        assert data["results"][0]["has_secret"] is True
        # Secret should not be exposed
        assert "secret" not in data["results"][0]

    def test_create_webhook(self, api_client, customer):
        """Test creating a webhook."""
        data = {
            "customer": customer.id,
            "name": "New Webhook",
            "url": "https://example.com/new",
            "event_types": ["job.failed"],
            "secret": "my-secret",
        }
        response = api_client.post("/api/v1/webhooks/", data, format="json")
        assert response.status_code == 201

        # Verify webhook was created
        webhook = Webhook.objects.get(name="New Webhook")
        assert webhook.customer_id == customer.id
        assert webhook.secret == "my-secret"
        assert webhook.has_secret()

    def test_update_webhook(self, api_client, webhook):
        """Test updating a webhook."""
        data = {
            "name": "Updated Webhook",
            "enabled": False,
        }
        response = api_client.patch(f"/api/v1/webhooks/{webhook.id}/", data, format="json")
        assert response.status_code == 200

        webhook.refresh_from_db()
        assert webhook.name == "Updated Webhook"
        assert webhook.enabled is False

    def test_delete_webhook(self, api_client, webhook):
        """Test deleting a webhook."""
        response = api_client.delete(f"/api/v1/webhooks/{webhook.id}/")
        assert response.status_code == 204
        assert not Webhook.objects.filter(id=webhook.id).exists()

    def test_test_webhook(self, api_client, webhook):
        """Test webhook test action."""
        with patch("webnet.webhooks.tasks.deliver_webhook.delay") as mock_deliver:
            response = api_client.post(f"/api/v1/webhooks/{webhook.id}/test/")
            assert response.status_code == 202
            assert "delivery_id" in response.json()

            # Verify delivery task was dispatched
            mock_deliver.assert_called_once()

    def test_customer_scoping(self, customer):
        """Test that webhooks are properly scoped to customers."""
        customer2 = Customer.objects.create(name="Beta Corp")
        user2 = User.objects.create_user(username="user2", password="secret123", role="operator")
        user2.customers.add(customer2)

        # Create webhooks for different customers
        Webhook.objects.create(
            customer=customer,
            name="Acme Webhook",
            url="https://acme.example.com/webhook",
            event_types=["job.completed"],
        )
        Webhook.objects.create(
            customer=customer2,
            name="Beta Webhook",
            url="https://beta.example.com/webhook",
            event_types=["job.completed"],
        )

        # User2 should only see their customer's webhooks
        client = APIClient()
        client.login(username="user2", password="secret123")
        response = client.get("/api/v1/webhooks/")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["results"][0]["name"] == "Beta Webhook"


@pytest.mark.django_db
class TestWebhookDeliveryAPI:
    """Test webhook delivery API endpoints."""

    def test_list_deliveries(self, api_client, webhook):
        """Test listing webhook deliveries."""
        delivery = WebhookDelivery.objects.create(
            webhook=webhook,
            event_type="job.completed",
            event_id=123,
            payload={"test": "data"},
            status=WebhookDelivery.STATUS_SUCCESS,
        )

        response = api_client.get("/api/v1/webhook-deliveries/")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["results"][0]["id"] == delivery.id
        assert data["results"][0]["event_type"] == "job.completed"

    def test_retry_failed_delivery(self, api_client, webhook):
        """Test retrying a failed webhook delivery."""
        delivery = WebhookDelivery.objects.create(
            webhook=webhook,
            event_type="job.failed",
            event_id=456,
            payload={"test": "data"},
            status=WebhookDelivery.STATUS_FAILED,
            error_message="Connection timeout",
        )

        with patch("webnet.webhooks.tasks.deliver_webhook.delay") as mock_deliver:
            response = api_client.post(f"/api/v1/webhook-deliveries/{delivery.id}/retry/")
            assert response.status_code == 202

            # Verify delivery was reset and dispatched
            delivery.refresh_from_db()
            assert delivery.status == WebhookDelivery.STATUS_PENDING
            mock_deliver.assert_called_once()

    def test_cannot_retry_successful_delivery(self, api_client, webhook):
        """Test that successful deliveries cannot be retried."""
        delivery = WebhookDelivery.objects.create(
            webhook=webhook,
            event_type="job.completed",
            event_id=789,
            payload={"test": "data"},
            status=WebhookDelivery.STATUS_SUCCESS,
        )

        response = api_client.post(f"/api/v1/webhook-deliveries/{delivery.id}/retry/")
        assert response.status_code == 400


@pytest.mark.django_db
class TestWebhookDelivery:
    """Test webhook delivery logic."""

    def test_generate_signature(self):
        """Test HMAC signature generation."""
        payload = b'{"test": "data"}'
        secret = "test-secret"

        signature = generate_signature(payload, secret)
        assert len(signature) == 64  # SHA256 hex digest length

        # Same payload and secret should produce same signature
        signature2 = generate_signature(payload, secret)
        assert signature == signature2

        # Different secret should produce different signature
        signature3 = generate_signature(payload, "different-secret")
        assert signature != signature3

    @patch("httpx.Client")
    def test_successful_delivery(self, mock_client_class, webhook):
        """Test successful webhook delivery."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client.post = Mock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        delivery = WebhookDelivery.objects.create(
            webhook=webhook,
            event_type="job.completed",
            event_id=1,
            payload={"test": "data"},
        )

        # Import and call delivery task
        from webnet.webhooks.tasks import deliver_webhook

        deliver_webhook(delivery.id)

        # Verify delivery was marked successful
        delivery.refresh_from_db()
        assert delivery.status == WebhookDelivery.STATUS_SUCCESS
        assert delivery.http_status == 200
        assert delivery.attempts == 1

    @patch("httpx.Client")
    def test_failed_delivery_with_retry(self, mock_client_class, webhook):
        """Test failed webhook delivery triggers retry."""
        # Mock HTTP error
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client.post = Mock(side_effect=Exception("Connection error"))
        mock_client_class.return_value = mock_client

        delivery = WebhookDelivery.objects.create(
            webhook=webhook,
            event_type="job.failed",
            event_id=2,
            payload={"test": "data"},
        )

        # Import task
        from webnet.webhooks.tasks import deliver_webhook

        # Mock the retry method
        with patch.object(deliver_webhook, "retry") as mock_retry:
            deliver_webhook(delivery.id)

            # Verify retry was scheduled
            delivery.refresh_from_db()
            assert delivery.status == WebhookDelivery.STATUS_RETRYING
            assert delivery.attempts == 1
            assert "Connection error" in delivery.error_message
            mock_retry.assert_called_once()

    def test_disabled_webhook_not_delivered(self, webhook):
        """Test that disabled webhooks are not delivered."""
        webhook.enabled = False
        webhook.save()

        delivery = WebhookDelivery.objects.create(
            webhook=webhook,
            event_type="job.completed",
            event_id=3,
            payload={"test": "data"},
        )

        from webnet.webhooks.tasks import deliver_webhook

        deliver_webhook(delivery.id)

        delivery.refresh_from_db()
        assert delivery.status == WebhookDelivery.STATUS_FAILED
        assert "disabled" in delivery.error_message.lower()


@pytest.mark.django_db
class TestWebhookSignals:
    """Test webhook signal triggers."""

    def test_job_completed_triggers_webhook(self, customer, user, webhook):
        """Test that job completion triggers webhook."""
        with patch("webnet.webhooks.tasks.trigger_webhook_event.delay") as mock_trigger:
            job = Job.objects.create(
                customer=customer,
                user=user,
                type="run_commands",
                status="queued",
            )

            # Update job to completed
            job.status = "success"
            job.save()

            # Verify webhook was triggered
            assert mock_trigger.call_count > 0
            call_args = mock_trigger.call_args_list[-1][1]
            assert call_args["customer_id"] == customer.id
            assert call_args["event_type"] == "job.completed"
            assert call_args["event_id"] == job.id

    def test_device_created_triggers_webhook(self, customer, user, webhook):
        """Test that device creation triggers webhook."""
        credential = Credential.objects.create(
            customer=customer,
            name="cred1",
            username="admin",
        )
        credential.password = "password"
        credential.save()

        with patch("webnet.webhooks.tasks.trigger_webhook_event.delay") as mock_trigger:
            device = Device.objects.create(
                customer=customer,
                hostname="switch1",
                mgmt_ip="10.0.0.1",
                vendor="cisco",
                platform="ios",
                credential=credential,
            )

            # Verify webhook was triggered
            mock_trigger.assert_called_once()
            call_args = mock_trigger.call_args[1]
            assert call_args["event_type"] == "device.created"
            assert call_args["event_id"] == device.id

    def test_trigger_webhook_event_filters_by_subscription(self, customer, webhook):
        """Test that only subscribed webhooks are triggered."""
        # Create another webhook not subscribed to job.completed
        Webhook.objects.create(
            customer=customer,
            name="Other Webhook",
            url="https://other.example.com/webhook",
            event_types=["device.deleted"],
            enabled=True,
        )

        with patch("webnet.webhooks.tasks.deliver_webhook.delay") as mock_deliver:
            trigger_webhook_event(
                customer_id=customer.id,
                event_type="job.completed",
                event_id=1,
                payload={"test": "data"},
            )

            # Only one webhook should be triggered (the one subscribed to job.completed)
            assert mock_deliver.call_count == 1

            # Verify delivery was created for correct webhook
            delivery = WebhookDelivery.objects.get()
            assert delivery.webhook.name == "Test Webhook"
            assert delivery.event_type == "job.completed"


@pytest.mark.django_db
class TestWebhookRetryLogic:
    """Test webhook retry logic."""

    def test_exponential_backoff(self, webhook):
        """Test that retry backoff increases exponentially."""
        delivery = WebhookDelivery.objects.create(
            webhook=webhook,
            event_type="job.failed",
            event_id=1,
            payload={"test": "data"},
        )

        # Simulate multiple failed attempts
        from webnet.webhooks.tasks import deliver_webhook, _retry_delivery

        # First retry: 60 seconds
        delivery.attempts = 1
        with patch.object(deliver_webhook, "retry") as mock_retry:
            _retry_delivery(deliver_webhook, delivery, webhook)
            mock_retry.assert_called_once_with(countdown=60, max_retries=webhook.max_retries)

        # Second retry: 120 seconds
        delivery.attempts = 2
        with patch.object(deliver_webhook, "retry") as mock_retry:
            _retry_delivery(deliver_webhook, delivery, webhook)
            mock_retry.assert_called_once_with(countdown=120, max_retries=webhook.max_retries)

        # Third attempt would reach max_retries (3) so it should not retry anymore
        delivery.attempts = 3
        with patch.object(deliver_webhook, "retry") as mock_retry:
            _retry_delivery(deliver_webhook, delivery, webhook)
            # Should not retry because max_retries reached
            mock_retry.assert_not_called()

            # Verify delivery is marked as failed
            delivery.refresh_from_db()
            assert delivery.status == WebhookDelivery.STATUS_FAILED

    def test_max_retries_reached(self, webhook):
        """Test that delivery fails after max retries."""
        delivery = WebhookDelivery.objects.create(
            webhook=webhook,
            event_type="job.failed",
            event_id=1,
            payload={"test": "data"},
        )

        # Set attempts to max retries
        delivery.attempts = webhook.max_retries

        from webnet.webhooks.tasks import deliver_webhook, _retry_delivery

        with patch.object(deliver_webhook, "retry") as mock_retry:
            _retry_delivery(deliver_webhook, delivery, webhook)

            # Should not retry anymore
            mock_retry.assert_not_called()

            # Delivery should be marked as failed
            delivery.refresh_from_db()
            assert delivery.status == WebhookDelivery.STATUS_FAILED
            assert delivery.next_retry_at is None
