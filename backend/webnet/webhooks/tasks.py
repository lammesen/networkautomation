"""Celery tasks for webhook delivery."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from datetime import timedelta

import httpx
from celery import shared_task
from django.utils import timezone

from webnet.webhooks.models import Webhook, WebhookDelivery

logger = logging.getLogger(__name__)


def generate_signature(payload_bytes: bytes, secret: str) -> str:
    """Generate HMAC-SHA256 signature for webhook payload.

    Args:
        payload_bytes: JSON payload as bytes
        secret: Secret token for signature generation

    Returns:
        Hex-encoded signature string
    """
    return hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()


@shared_task(name="deliver_webhook", bind=True, max_retries=None)
def deliver_webhook(self, delivery_id: int) -> None:
    """Deliver a webhook to its configured URL.

    This task handles the HTTP POST request to the webhook URL, including:
    - HMAC signature generation if secret is configured
    - SSL verification based on webhook settings
    - Retry logic with exponential backoff
    - Response logging and status tracking

    Args:
        delivery_id: ID of the WebhookDelivery to send
    """
    try:
        delivery = WebhookDelivery.objects.select_related("webhook").get(pk=delivery_id)
    except WebhookDelivery.DoesNotExist:
        logger.warning("WebhookDelivery %s not found", delivery_id)
        return

    webhook = delivery.webhook

    # Skip if webhook is disabled
    if not webhook.enabled:
        logger.info("Webhook %s is disabled, skipping delivery %s", webhook.id, delivery_id)
        delivery.status = WebhookDelivery.STATUS_FAILED
        delivery.error_message = "Webhook is disabled"
        delivery.save()
        return

    # Prepare payload as JSON bytes
    payload_str = json.dumps(delivery.payload)
    payload_bytes = payload_str.encode("utf-8")

    # Prepare headers
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "webnet-webhook/1.0",
        **webhook.headers,
    }

    # Add HMAC signature if secret is configured
    if webhook.has_secret():
        signature = generate_signature(payload_bytes, webhook.secret)
        headers["X-Webhook-Signature"] = f"sha256={signature}"

    # Increment attempt counter
    delivery.attempts += 1
    delivery.status = WebhookDelivery.STATUS_RETRYING if delivery.attempts > 1 else delivery.status
    delivery.save()

    # Make HTTP request
    start_time = time.time()
    try:
        with httpx.Client(
            verify=webhook.verify_ssl,
            timeout=webhook.timeout_seconds,
        ) as client:
            response = client.post(
                webhook.url,
                content=payload_bytes,
                headers=headers,
            )
            duration_ms = int((time.time() - start_time) * 1000)

            # Update delivery record
            delivery.http_status = response.status_code
            delivery.duration_ms = duration_ms
            # Truncate response body to 10KB
            delivery.response_body = response.text[:10240]

            # Check if delivery was successful (2xx status code)
            if 200 <= response.status_code < 300:
                delivery.status = WebhookDelivery.STATUS_SUCCESS
                delivery.error_message = None
                delivery.next_retry_at = None
                delivery.save()
                logger.info(
                    "Webhook delivery %s succeeded (HTTP %s) in %sms",
                    delivery_id,
                    response.status_code,
                    duration_ms,
                )
            else:
                # HTTP error - retry if attempts remain
                delivery.error_message = f"HTTP {response.status_code}: {response.text[:500]}"
                delivery.save()
                _retry_delivery(self, delivery, webhook)

    except Exception as exc:
        # Network or other error - retry if attempts remain
        duration_ms = int((time.time() - start_time) * 1000)
        delivery.duration_ms = duration_ms
        delivery.error_message = str(exc)[:1000]
        delivery.save()
        _retry_delivery(self, delivery, webhook)


def _retry_delivery(task, delivery: WebhookDelivery, webhook: Webhook) -> None:
    """Handle retry logic for failed webhook delivery.

    Args:
        task: Celery task instance (for retry)
        delivery: WebhookDelivery record
        webhook: Webhook configuration
    """
    if delivery.attempts >= webhook.max_retries:
        # Max retries reached, mark as failed
        delivery.status = WebhookDelivery.STATUS_FAILED
        delivery.next_retry_at = None
        delivery.save()
        logger.error(
            "Webhook delivery %s failed after %s attempts: %s",
            delivery.id,
            delivery.attempts,
            delivery.error_message,
        )
    else:
        # Schedule retry with exponential backoff
        backoff_seconds = webhook.retry_backoff * (2 ** (delivery.attempts - 1))
        next_retry = timezone.now() + timedelta(seconds=backoff_seconds)
        delivery.status = WebhookDelivery.STATUS_RETRYING
        delivery.next_retry_at = next_retry
        delivery.save()

        logger.info(
            "Webhook delivery %s failed (attempt %s/%s), retrying in %ss",
            delivery.id,
            delivery.attempts,
            webhook.max_retries,
            backoff_seconds,
        )

        # Schedule retry
        task.retry(countdown=backoff_seconds, max_retries=webhook.max_retries)


@shared_task(name="trigger_webhook_event")
def trigger_webhook_event(
    customer_id: int,
    event_type: str,
    event_id: int,
    payload: dict,
) -> None:
    """Trigger webhook deliveries for a specific event.

    Finds all active webhooks subscribed to the event type and creates
    delivery records for each, then dispatches delivery tasks.

    Args:
        customer_id: Customer ID for webhook scoping
        event_type: Type of event (e.g., "job.completed")
        event_id: ID of the entity that triggered the event
        payload: Event data to send to webhook URLs
    """
    # Find all enabled webhooks for this customer subscribed to this event type
    webhooks = Webhook.objects.filter(
        customer_id=customer_id,
        enabled=True,
    )

    triggered_count = 0
    for webhook in webhooks:
        if webhook.subscribes_to(event_type):
            # Create delivery record
            delivery = WebhookDelivery.objects.create(
                webhook=webhook,
                event_type=event_type,
                event_id=event_id,
                payload=payload,
                status=WebhookDelivery.STATUS_PENDING,
            )
            # Dispatch delivery task
            deliver_webhook.delay(delivery.id)
            triggered_count += 1

    if triggered_count > 0:
        logger.info(
            "Triggered %s webhook(s) for event %s (customer %s)",
            triggered_count,
            event_type,
            customer_id,
        )
