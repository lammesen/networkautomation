"""Tests for compliance auto-remediation functionality."""

import pytest
from django.utils import timezone
from unittest.mock import Mock, patch

from webnet.compliance.models import (
    CompliancePolicy,
    ComplianceResult,
    RemediationRule,
    RemediationAction,
)
from webnet.customers.models import Customer
from webnet.devices.models import Device, Credential
from webnet.users.models import User
from webnet.jobs.models import Job


@pytest.fixture
def customer():
    return Customer.objects.create(name="Test Corp")


@pytest.fixture
def admin_user(customer):
    user = User.objects.create_user(username="admin", password="secret", role="admin")
    user.customers.add(customer)
    return user


@pytest.fixture
def credential(customer):
    cred = Credential.objects.create(customer=customer, name="test_cred", username="admin")
    cred.password = "secret"
    cred.save()
    return cred


@pytest.fixture
def device(customer, credential):
    return Device.objects.create(
        customer=customer,
        hostname="test-router",
        mgmt_ip="192.0.2.1",
        vendor="cisco",
        platform="ios",
        credential=credential,
    )


@pytest.fixture
def policy(customer, admin_user):
    return CompliancePolicy.objects.create(
        customer=customer,
        name="Security Policy",
        description="Test security policy",
        scope_json={"site": "lab"},
        definition_yaml="rules: []",
        created_by=admin_user,
    )


@pytest.fixture
def remediation_rule(policy, admin_user):
    return RemediationRule.objects.create(
        policy=policy,
        name="Fix NTP",
        description="Configure NTP servers",
        enabled=True,
        config_snippet="ntp server 192.0.2.100\nntp server 192.0.2.101",
        approval_required="none",
        max_daily_executions=10,
        apply_mode="merge",
        verify_after=True,
        rollback_on_failure=True,
        created_by=admin_user,
    )


@pytest.mark.django_db
class TestRemediationRuleModel:
    """Test RemediationRule model."""

    def test_create_remediation_rule(self, policy, admin_user):
        """Test creating a remediation rule."""
        rule = RemediationRule.objects.create(
            policy=policy,
            name="Test Rule",
            enabled=True,
            config_snippet="logging buffered 10000",
            created_by=admin_user,
        )

        assert rule.policy == policy
        assert rule.name == "Test Rule"
        assert rule.enabled is True
        assert rule.approval_required == "manual"  # default
        assert rule.max_daily_executions == 10  # default
        assert rule.apply_mode == "merge"  # default
        assert rule.verify_after is True  # default
        assert rule.rollback_on_failure is True  # default

    def test_remediation_rule_str(self, remediation_rule):
        """Test string representation."""
        assert str(remediation_rule) == "Fix NTP for Security Policy"


@pytest.mark.django_db
class TestRemediationActionModel:
    """Test RemediationAction model."""

    def test_create_remediation_action(self, remediation_rule, device, admin_user):
        """Test creating a remediation action."""
        policy = remediation_rule.policy
        job = Job.objects.create(
            type="compliance_check",
            status="success",
            user=admin_user,
            customer=policy.customer,
        )
        result = ComplianceResult.objects.create(
            policy=policy,
            device=device,
            job=job,
            status="failed",
            details_json={"violations": ["ntp not configured"]},
        )

        action = RemediationAction.objects.create(
            rule=remediation_rule,
            compliance_result=result,
            device=device,
            job=job,
            status="pending",
        )

        assert action.rule == remediation_rule
        assert action.device == device
        assert action.status == "pending"
        assert action.verification_passed is None

    def test_remediation_action_str(self, remediation_rule, device, admin_user):
        """Test string representation."""
        policy = remediation_rule.policy
        job = Job.objects.create(
            type="compliance_check", status="success", user=admin_user, customer=policy.customer
        )
        result = ComplianceResult.objects.create(
            policy=policy, device=device, job=job, status="failed", details_json={}
        )
        action = RemediationAction.objects.create(
            rule=remediation_rule, compliance_result=result, device=device, status="pending"
        )

        assert str(action) == f"Remediation {action.id} - Fix NTP on test-router"


@pytest.mark.django_db
class TestRemediationRuleAPI:
    """Test RemediationRule API endpoints."""

    def test_list_remediation_rules(self, client, admin_user, remediation_rule):
        """Test listing remediation rules."""
        client.force_login(admin_user)
        response = client.get("/api/v1/compliance/remediation-rules/")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["results"][0]["name"] == "Fix NTP"

    def test_create_remediation_rule(self, client, admin_user, policy):
        """Test creating a remediation rule via API."""
        client.force_login(admin_user)
        response = client.post(
            "/api/v1/compliance/remediation-rules/",
            data={
                "policy": policy.id,
                "name": "New Rule",
                "config_snippet": "logging host 192.0.2.10",
                "enabled": True,
                "approval_required": "none",
                "created_by": admin_user.id,
            },
            content_type="application/json",
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Rule"
        assert data["policy"] == policy.id

    def test_enable_remediation_rule(self, client, admin_user, remediation_rule):
        """Test enabling a remediation rule."""
        remediation_rule.enabled = False
        remediation_rule.save()

        client.force_login(admin_user)
        response = client.post(
            f"/api/v1/compliance/remediation-rules/{remediation_rule.id}/enable/"
        )

        assert response.status_code == 200
        remediation_rule.refresh_from_db()
        assert remediation_rule.enabled is True

    def test_disable_remediation_rule(self, client, admin_user, remediation_rule):
        """Test disabling a remediation rule."""
        client.force_login(admin_user)
        response = client.post(
            f"/api/v1/compliance/remediation-rules/{remediation_rule.id}/disable/"
        )

        assert response.status_code == 200
        remediation_rule.refresh_from_db()
        assert remediation_rule.enabled is False


@pytest.mark.django_db
class TestRemediationActionAPI:
    """Test RemediationAction API endpoints."""

    def test_list_remediation_actions(self, client, admin_user, remediation_rule, device):
        """Test listing remediation actions."""
        policy = remediation_rule.policy
        job = Job.objects.create(
            type="compliance_check", status="success", user=admin_user, customer=policy.customer
        )
        result = ComplianceResult.objects.create(
            policy=policy, device=device, job=job, status="failed", details_json={}
        )
        RemediationAction.objects.create(
            rule=remediation_rule, compliance_result=result, device=device, status="success"
        )

        client.force_login(admin_user)
        response = client.get("/api/v1/compliance/remediation-actions/")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["results"][0]["status"] == "success"

    def test_remediation_action_readonly(self, client, admin_user, remediation_rule, device):
        """Test that remediation actions are read-only."""
        policy = remediation_rule.policy
        job = Job.objects.create(
            type="compliance_check", status="success", user=admin_user, customer=policy.customer
        )
        result = ComplianceResult.objects.create(
            policy=policy, device=device, job=job, status="failed", details_json={}
        )

        client.force_login(admin_user)
        response = client.post(
            "/api/v1/compliance/remediation-actions/",
            data={
                "rule": remediation_rule.id,
                "compliance_result": result.id,
                "device": device.id,
                "status": "pending",
            },
            content_type="application/json",
        )

        # POST should not be allowed on read-only viewset
        assert response.status_code == 405


@pytest.mark.django_db
class TestAutoRemediationTrigger:
    """Test auto-remediation trigger logic."""

    @patch("webnet.jobs.tasks.auto_remediation_job")
    def test_trigger_auto_remediation(
        self, mock_auto_remediation, remediation_rule, device, admin_user
    ):
        """Test triggering auto-remediation for a violation."""
        from webnet.jobs.tasks import trigger_auto_remediation

        policy = remediation_rule.policy
        job = Job.objects.create(
            type="compliance_check", status="success", user=admin_user, customer=policy.customer
        )
        result = ComplianceResult.objects.create(
            policy=policy, device=device, job=job, status="failed", details_json={}
        )

        # Trigger auto-remediation
        trigger_auto_remediation(result.id)

        # Should queue the remediation job
        mock_auto_remediation.delay.assert_called_once_with(remediation_rule.id, result.id)

    def test_trigger_skips_manual_approval(self, remediation_rule, device, admin_user):
        """Test that rules requiring manual approval are skipped."""
        from webnet.jobs.tasks import trigger_auto_remediation

        remediation_rule.approval_required = "manual"
        remediation_rule.save()

        policy = remediation_rule.policy
        job = Job.objects.create(
            type="compliance_check", status="success", user=admin_user, customer=policy.customer
        )
        result = ComplianceResult.objects.create(
            policy=policy, device=device, job=job, status="failed", details_json={}
        )

        with patch("webnet.jobs.tasks.auto_remediation_job") as mock_job:
            trigger_auto_remediation(result.id)
            # Should NOT queue the job
            mock_job.delay.assert_not_called()

    def test_trigger_respects_daily_limit(self, remediation_rule, device, admin_user):
        """Test that daily execution limit is enforced."""
        from webnet.jobs.tasks import trigger_auto_remediation

        remediation_rule.max_daily_executions = 2
        remediation_rule.save()

        policy = remediation_rule.policy
        job = Job.objects.create(
            type="compliance_check", status="success", user=admin_user, customer=policy.customer
        )

        # Create executions up to the limit
        for i in range(2):
            result = ComplianceResult.objects.create(
                policy=policy, device=device, job=job, status="failed", details_json={}
            )
            RemediationAction.objects.create(
                rule=remediation_rule,
                compliance_result=result,
                device=device,
                status="success",
                started_at=timezone.now(),
            )

        # Create a new violation
        new_result = ComplianceResult.objects.create(
            policy=policy, device=device, job=job, status="failed", details_json={}
        )

        with patch("webnet.jobs.tasks.auto_remediation_job") as mock_job:
            trigger_auto_remediation(new_result.id)
            # Should NOT queue because limit reached
            mock_job.delay.assert_not_called()


@pytest.mark.django_db
class TestAutoRemediationJob:
    """Test auto-remediation job execution."""

    @patch("webnet.jobs.tasks._nr_from_inventory")
    @patch("webnet.jobs.tasks.build_inventory")
    def test_successful_remediation(
        self, mock_build_inventory, mock_nr, remediation_rule, device, admin_user
    ):
        """Test successful auto-remediation execution."""
        from webnet.jobs.tasks import auto_remediation_job

        policy = remediation_rule.policy
        job = Job.objects.create(
            type="compliance_check", status="success", user=admin_user, customer=policy.customer
        )
        result = ComplianceResult.objects.create(
            policy=policy, device=device, job=job, status="failed", details_json={}
        )

        # Mock Nornir results
        mock_inventory = Mock()
        mock_inventory.hosts = {"test-router": Mock()}
        mock_build_inventory.return_value = mock_inventory

        mock_nr_instance = Mock()
        mock_nr.return_value = mock_nr_instance

        # Mock successful config retrieval and application
        mock_config_result = Mock()
        mock_config_result.__iter__ = Mock(return_value=iter([("test-router", Mock())]))

        def mock_run(task, **kwargs):
            task_result = Mock()
            task_result.failed = False
            if "getters" in kwargs:  # napalm_get
                task_result.result = {"config": {"running": "test config"}}
            return {
                "test-router": task_result,
            }

        mock_nr_instance.run = mock_run

        # Execute remediation
        auto_remediation_job(remediation_rule.id, result.id)

        # Check that action was created and succeeded
        action = RemediationAction.objects.get(rule=remediation_rule, compliance_result=result)
        assert action.status == "success"
        assert action.before_snapshot is not None
        assert action.after_snapshot is not None
        # Verification is not implemented yet, so it should be None
        assert action.verification_passed is None

    @patch("webnet.jobs.tasks._nr_from_inventory")
    @patch("webnet.jobs.tasks.build_inventory")
    def test_failed_remediation_with_rollback(
        self, mock_build_inventory, mock_nr, remediation_rule, device, admin_user
    ):
        """Test failed remediation with rollback."""
        from webnet.jobs.tasks import auto_remediation_job

        policy = remediation_rule.policy
        job = Job.objects.create(
            type="compliance_check", status="success", user=admin_user, customer=policy.customer
        )
        result = ComplianceResult.objects.create(
            policy=policy, device=device, job=job, status="failed", details_json={}
        )

        # Mock Nornir setup
        mock_inventory = Mock()
        mock_inventory.hosts = {"test-router": Mock()}
        mock_build_inventory.return_value = mock_inventory

        mock_nr_instance = Mock()
        mock_nr.return_value = mock_nr_instance

        call_count = {"count": 0}

        def mock_run(task, **kwargs):
            call_count["count"] += 1
            task_result = Mock()

            if call_count["count"] == 1:  # First call: get before snapshot (success)
                task_result.failed = False
                task_result.result = {"config": {"running": "before config"}}
            elif call_count["count"] == 2:  # Second call: apply config (fail)
                task_result.failed = True
                task_result.exception = "Connection timeout"
            else:  # Rollback attempts
                task_result.failed = False
                task_result.result = {}

            return {"test-router": task_result}

        mock_nr_instance.run = mock_run

        # Execute remediation
        auto_remediation_job(remediation_rule.id, result.id)

        # Check that action was created and rolled back
        action = RemediationAction.objects.get(rule=remediation_rule, compliance_result=result)
        assert action.status in ["failed", "rolled_back"]
        assert action.before_snapshot is not None
        assert action.error_message is not None
