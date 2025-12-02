"""Email notification service for webnet."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.utils import timezone

if TYPE_CHECKING:
    from webnet.compliance.models import ComplianceResult
    from webnet.jobs.models import Job
    from webnet.notifications.models import SMTPConfig

logger = logging.getLogger(__name__)


@dataclass
class EmailContext:
    """Context for rendering email templates."""

    job: Job | None = None
    compliance_result: ComplianceResult | None = None
    event_type: str = ""
    customer_name: str = ""
    webnet_url: str = ""


class EmailService:
    """Service for sending email notifications."""

    def __init__(self, smtp_config: SMTPConfig | None = None):
        """Initialize email service.

        Args:
            smtp_config: SMTP configuration to use. If None, uses Django settings.
        """
        self.smtp_config = smtp_config

    def _get_connection(self):
        """Get email connection using SMTP config or Django settings."""
        if self.smtp_config:
            # Check if we're in a test environment with locmem backend
            from django.conf import settings

            if hasattr(settings, "EMAIL_BACKEND") and "locmem" in settings.EMAIL_BACKEND:
                # Use locmem backend for testing
                return get_connection(backend=settings.EMAIL_BACKEND)

            return get_connection(
                backend="django.core.mail.backends.smtp.EmailBackend",
                host=self.smtp_config.host,
                port=self.smtp_config.port,
                username=self.smtp_config.username or "",
                password=self.smtp_config.password or "",
                use_tls=self.smtp_config.use_tls,
                use_ssl=self.smtp_config.use_ssl,
                fail_silently=False,
            )
        return get_connection()

    def _get_from_email(self) -> str:
        """Get from email address."""
        if self.smtp_config:
            return self.smtp_config.from_email
        return settings.DEFAULT_FROM_EMAIL

    def _get_reply_to(self) -> list[str]:
        """Get reply-to email addresses."""
        if self.smtp_config and self.smtp_config.reply_to_email:
            return [self.smtp_config.reply_to_email]
        return []

    def _get_webnet_url(self) -> str:
        """Get base webnet URL."""
        # Try to get from settings, fallback to localhost
        return getattr(settings, "WEBNET_BASE_URL", "http://localhost:8000")

    def send_notification(
        self,
        recipient_email: str,
        subject: str,
        context: EmailContext,
        event_type: str,
    ) -> tuple[bool, str | None]:
        """Send email notification.

        Args:
            recipient_email: Recipient email address
            subject: Email subject
            context: Context for rendering template
            event_type: Type of notification event

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Render templates
            template_base = f"emails/{event_type}"
            html_content = render_to_string(f"{template_base}.html", {"ctx": context})
            text_content = render_to_string(f"{template_base}.txt", {"ctx": context})

            # Create email message
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=self._get_from_email(),
                to=[recipient_email],
                reply_to=self._get_reply_to(),
                connection=self._get_connection(),
            )
            msg.attach_alternative(html_content, "text/html")

            # Send email
            msg.send()

            logger.info(f"Email sent to {recipient_email}: {subject}")
            return True, None

        except Exception as e:
            error_msg = f"Failed to send email: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg

    def send_test_email(self, recipient_email: str) -> tuple[bool, str | None]:
        """Send test email to verify SMTP configuration.

        Args:
            recipient_email: Email address to send test email to

        Returns:
            Tuple of (success, error_message)
        """
        try:
            context = EmailContext(
                event_type="test",
                customer_name=self.smtp_config.customer.name if self.smtp_config else "Test",
                webnet_url=self._get_webnet_url(),
            )

            html_content = render_to_string("emails/test.html", {"ctx": context})
            text_content = render_to_string("emails/test.txt", {"ctx": context})

            msg = EmailMultiAlternatives(
                subject="Webnet Email Test",
                body=text_content,
                from_email=self._get_from_email(),
                to=[recipient_email],
                reply_to=self._get_reply_to(),
                connection=self._get_connection(),
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send()

            logger.info(f"Test email sent to {recipient_email}")
            return True, None

        except Exception as e:
            error_msg = f"Failed to send test email: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg


def notify_job_event(job: Job, event_type: str) -> None:
    """Send notifications for job events.

    Args:
        job: Job object
        event_type: Type of event (job_success, job_failed, job_partial)
    """
    from webnet.notifications.models import NotificationEvent, NotificationPreference, SMTPConfig

    # Check if SMTP is configured for customer
    try:
        smtp_config = SMTPConfig.objects.get(customer=job.customer, enabled=True)
    except SMTPConfig.DoesNotExist:
        logger.debug(f"No SMTP config for customer {job.customer_id}")
        return

    # Get users who should be notified
    preferences = NotificationPreference.objects.filter(
        customer=job.customer,
        event_type=event_type,
        enabled=True,
    ).select_related("user")

    # Filter by job type if specified
    preferences = [pref for pref in preferences if not pref.job_types or job.type in pref.job_types]

    if not preferences:
        logger.debug(f"No notification preferences for {event_type} in customer {job.customer_id}")
        return

    # Prepare context
    webnet_url = getattr(settings, "WEBNET_BASE_URL", "http://localhost:8000")
    context = EmailContext(
        job=job,
        event_type=event_type,
        customer_name=job.customer.name,
        webnet_url=webnet_url,
    )

    # Generate subject
    status_text = event_type.replace("job_", "").replace("_", " ").title()
    subject = f"[Webnet] Job {status_text}: {job.get_type_display()}"

    # Send notifications
    email_service = EmailService(smtp_config)

    for pref in preferences:
        recipient = pref.email_address or pref.user.email
        if not recipient:
            logger.warning(f"User {pref.user.username} has no email address")
            continue

        # Create notification event record
        event = NotificationEvent.objects.create(
            customer=job.customer,
            recipient_email=recipient,
            event_type=event_type,
            subject=subject,
            job=job,
        )

        # Send email
        success, error_msg = email_service.send_notification(
            recipient_email=recipient,
            subject=subject,
            context=context,
            event_type=event_type,
        )

        # Update event status
        if success:
            event.status = "sent"
            event.sent_at = timezone.now()
        else:
            event.status = "failed"
            event.error_message = error_msg

        event.save()


def notify_compliance_violation(compliance_result: ComplianceResult) -> None:
    """Send notifications for compliance violations.

    Args:
        compliance_result: ComplianceResult object with violation
    """
    from webnet.notifications.models import NotificationEvent, NotificationPreference, SMTPConfig

    customer = compliance_result.policy.customer

    # Check if SMTP is configured for customer
    try:
        smtp_config = SMTPConfig.objects.get(customer=customer, enabled=True)
    except SMTPConfig.DoesNotExist:
        logger.debug(f"No SMTP config for customer {customer.id}")
        return

    # Get users who should be notified
    preferences = NotificationPreference.objects.filter(
        customer=customer,
        event_type="compliance_violation",
        enabled=True,
    ).select_related("user")

    if not preferences:
        logger.debug(
            f"No notification preferences for compliance_violation in customer {customer.id}"
        )
        return

    # Prepare context
    webnet_url = getattr(settings, "WEBNET_BASE_URL", "http://localhost:8000")
    context = EmailContext(
        compliance_result=compliance_result,
        event_type="compliance_violation",
        customer_name=customer.name,
        webnet_url=webnet_url,
    )

    # Generate subject
    subject = f"[Webnet] Compliance Violation: {compliance_result.policy.name}"

    # Send notifications
    email_service = EmailService(smtp_config)

    for pref in preferences:
        recipient = pref.email_address or pref.user.email
        if not recipient:
            logger.warning(f"User {pref.user.username} has no email address")
            continue

        # Create notification event record
        event = NotificationEvent.objects.create(
            customer=customer,
            recipient_email=recipient,
            event_type="compliance_violation",
            subject=subject,
            compliance_result=compliance_result,
        )

        # Send email
        success, error_msg = email_service.send_notification(
            recipient_email=recipient,
            subject=subject,
            context=context,
            event_type="compliance_violation",
        )

        # Update event status
        if success:
            event.status = "sent"
            event.sent_at = timezone.now()
        else:
            event.status = "failed"
            event.error_message = error_msg

        event.save()
