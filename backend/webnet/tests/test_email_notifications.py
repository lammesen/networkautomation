"""Tests for email notifications."""

import pytest
from django.core import mail
from django.conf import settings

from webnet.users.models import User
from webnet.customers.models import Customer
from webnet.jobs.models import Job
from webnet.compliance.models import CompliancePolicy, ComplianceResult
from webnet.devices.models import Device, Credential
from webnet.notifications.models import SMTPConfig, NotificationPreference, NotificationEvent
from webnet.notifications.services import notify_job_event, notify_compliance_violation, EmailService


@pytest.fixture
def customer():
    return Customer.objects.create(name="Test Corp")


@pytest.fixture
def user(customer):
    user = User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
        role="admin",
    )
    user.customers.add(customer)
    return user


@pytest.fixture
def smtp_config(customer):
    return SMTPConfig.objects.create(
        customer=customer,
        host="smtp.example.com",
        port=587,
        use_tls=True,
        from_email="webnet@example.com",
        enabled=True,
    )


@pytest.fixture
def notification_preference(user, customer):
    return NotificationPreference.objects.create(
        user=user,
        customer=customer,
        event_type="job_success",
        enabled=True,
    )


@pytest.mark.django_db
class TestEmailNotifications:
    """Test email notification system."""

    def test_smtp_config_creation(self, smtp_config, customer):
        """Test SMTP configuration creation."""
        assert smtp_config.customer == customer
        assert smtp_config.host == "smtp.example.com"
        assert smtp_config.enabled is True

    def test_notification_preference_creation(self, notification_preference, user, customer):
        """Test notification preference creation."""
        assert notification_preference.user == user
        assert notification_preference.customer == customer
        assert notification_preference.event_type == "job_success"
        assert notification_preference.enabled is True

    def test_send_test_email(self, smtp_config):
        """Test sending a test email."""
        # Use console backend for testing
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        
        email_service = EmailService(smtp_config)
        success, error_msg = email_service.send_test_email("recipient@example.com")
        
        assert success is True
        assert error_msg is None
        assert len(mail.outbox) == 1
        assert mail.outbox[0].subject == "Webnet Email Test"
        assert "recipient@example.com" in mail.outbox[0].to

    def test_job_success_notification(self, user, customer, smtp_config, notification_preference):
        """Test job success notification."""
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        
        # Create a completed job
        job = Job.objects.create(
            customer=customer,
            user=user,
            type="config_backup",
            status="success",
        )
        
        # Send notification
        notify_job_event(job, "job_success")
        
        # Check email was sent
        assert len(mail.outbox) == 1
        assert "Job Success" in mail.outbox[0].subject or "Job Completed Successfully" in mail.outbox[0].subject
        assert user.email in mail.outbox[0].to
        
        # Check notification event was logged
        events = NotificationEvent.objects.filter(job=job)
        assert events.count() == 1
        assert events.first().status == "sent"

    def test_job_failed_notification(self, user, customer, smtp_config):
        """Test job failed notification."""
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        
        # Create notification preference for failed jobs
        NotificationPreference.objects.create(
            user=user,
            customer=customer,
            event_type="job_failed",
            enabled=True,
        )
        
        # Create a failed job
        job = Job.objects.create(
            customer=customer,
            user=user,
            type="config_backup",
            status="failed",
            result_summary_json={"error": "Connection timeout"},
        )
        
        # Send notification
        notify_job_event(job, "job_failed")
        
        # Check email was sent
        assert len(mail.outbox) == 1
        assert "Job Failed" in mail.outbox[0].subject

    def test_compliance_violation_notification(self, user, customer, smtp_config):
        """Test compliance violation notification."""
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        
        # Create notification preference
        NotificationPreference.objects.create(
            user=user,
            customer=customer,
            event_type="compliance_violation",
            enabled=True,
        )
        
        # Create compliance policy and result
        policy = CompliancePolicy.objects.create(
            customer=customer,
            name="Test Policy",
            scope_json={},
            definition_yaml="rules: []",
            created_by=user,
        )
        
        credential = Credential.objects.create(
            customer=customer,
            name="test-cred",
            username="admin",
        )
        
        device = Device.objects.create(
            customer=customer,
            hostname="test-router",
            mgmt_ip="192.168.1.1",
            vendor="cisco",
            platform="ios",
            credential=credential,
        )
        
        job = Job.objects.create(
            customer=customer,
            user=user,
            type="compliance_check",
            status="success",
        )
        
        result = ComplianceResult.objects.create(
            policy=policy,
            device=device,
            job=job,
            status="failed",
            details_json={"error": "Configuration mismatch"},
        )
        
        # Send notification
        notify_compliance_violation(result)
        
        # Check email was sent
        assert len(mail.outbox) == 1
        assert "Compliance Violation" in mail.outbox[0].subject

    def test_no_smtp_config_no_notification(self, user, customer):
        """Test that no notification is sent when SMTP is not configured."""
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        
        # Create notification preference but no SMTP config
        NotificationPreference.objects.create(
            user=user,
            customer=customer,
            event_type="job_success",
            enabled=True,
        )
        
        job = Job.objects.create(
            customer=customer,
            user=user,
            type="config_backup",
            status="success",
        )
        
        # Send notification
        notify_job_event(job, "job_success")
        
        # No email should be sent
        assert len(mail.outbox) == 0

    def test_disabled_preference_no_notification(self, user, customer, smtp_config):
        """Test that no notification is sent when preference is disabled."""
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        
        # Create disabled preference
        NotificationPreference.objects.create(
            user=user,
            customer=customer,
            event_type="job_success",
            enabled=False,
        )
        
        job = Job.objects.create(
            customer=customer,
            user=user,
            type="config_backup",
            status="success",
        )
        
        # Send notification
        notify_job_event(job, "job_success")
        
        # No email should be sent
        assert len(mail.outbox) == 0

    def test_job_type_filter(self, user, customer, smtp_config):
        """Test that notifications can be filtered by job type."""
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        
        # Create preference only for config_backup jobs
        NotificationPreference.objects.create(
            user=user,
            customer=customer,
            event_type="job_success",
            enabled=True,
            job_types=["config_backup"],
        )
        
        # Test with matching job type
        job1 = Job.objects.create(
            customer=customer,
            user=user,
            type="config_backup",
            status="success",
        )
        notify_job_event(job1, "job_success")
        assert len(mail.outbox) == 1
        
        # Test with non-matching job type
        mail.outbox.clear()
        job2 = Job.objects.create(
            customer=customer,
            user=user,
            type="run_commands",
            status="success",
        )
        notify_job_event(job2, "job_success")
        assert len(mail.outbox) == 0

    def test_custom_email_address(self, user, customer, smtp_config):
        """Test using custom email address in preferences."""
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        
        custom_email = "custom@example.com"
        NotificationPreference.objects.create(
            user=user,
            customer=customer,
            event_type="job_success",
            enabled=True,
            email_address=custom_email,
        )
        
        job = Job.objects.create(
            customer=customer,
            user=user,
            type="config_backup",
            status="success",
        )
        
        notify_job_event(job, "job_success")
        
        assert len(mail.outbox) == 1
        assert custom_email in mail.outbox[0].to
        assert user.email not in mail.outbox[0].to
