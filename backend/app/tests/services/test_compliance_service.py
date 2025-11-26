"""Tests for ComplianceService."""

import pytest

from app.db.models import CompliancePolicy, ComplianceResult
from app.domain.context import TenantRequestContext
from app.domain.exceptions import ConflictError, NotFoundError
from app.services.compliance_service import ComplianceService


@pytest.fixture
def test_policy(db_session, test_customer, admin_user):
    """Create a test compliance policy."""
    policy = CompliancePolicy(
        name="test_policy",
        description="Test policy description",
        scope_json={"vendor": "cisco"},
        definition_yaml="---\n- get_facts:\n    hostname: test",
        created_by=admin_user.id,
        customer_id=test_customer.id,
    )
    db_session.add(policy)
    db_session.commit()
    db_session.refresh(policy)
    return policy


@pytest.fixture
def test_compliance_result(db_session, test_policy, test_device, test_job):
    """Create a test compliance result."""
    from datetime import datetime

    result = ComplianceResult(
        policy_id=test_policy.id,
        device_id=test_device.id,
        job_id=test_job.id,
        status="pass",
        ts=datetime.utcnow(),
        details_json={"checks": []},
    )
    db_session.add(result)
    db_session.commit()
    db_session.refresh(result)
    return result


class TestCompliancePolicies:
    """Tests for compliance policy operations."""

    def test_list_policies(self, db_session, test_customer, test_policy, admin_user):
        """Test listing compliance policies."""
        service = ComplianceService(db_session)
        context = TenantRequestContext(user=admin_user, customer=test_customer)

        policies = service.list_policies(context)

        assert len(policies) >= 1
        assert any(p.id == test_policy.id for p in policies)

    def test_list_policies_pagination(self, db_session, test_customer, test_policy, admin_user):
        """Test listing policies with pagination."""
        service = ComplianceService(db_session)
        context = TenantRequestContext(user=admin_user, customer=test_customer)

        policies = service.list_policies(context, skip=0, limit=1)

        assert len(policies) <= 1

    def test_get_policy_success(self, db_session, test_customer, test_policy, admin_user):
        """Test getting a policy by ID."""
        service = ComplianceService(db_session)
        context = TenantRequestContext(user=admin_user, customer=test_customer)

        policy = service.get_policy(test_policy.id, context)

        assert policy.id == test_policy.id
        assert policy.name == test_policy.name

    def test_get_policy_not_found(self, db_session, test_customer, admin_user):
        """Test getting non-existent policy raises NotFoundError."""
        service = ComplianceService(db_session)
        context = TenantRequestContext(user=admin_user, customer=test_customer)

        with pytest.raises(NotFoundError):
            service.get_policy(99999, context)

    def test_get_policy_wrong_customer(self, db_session, second_customer, test_policy, admin_user):
        """Test getting policy from wrong customer raises NotFoundError."""
        service = ComplianceService(db_session)
        context = TenantRequestContext(user=admin_user, customer=second_customer)

        with pytest.raises(NotFoundError):
            service.get_policy(test_policy.id, context)

    def test_create_policy(self, db_session, test_customer, admin_user):
        """Test creating a new policy."""
        service = ComplianceService(db_session)
        context = TenantRequestContext(user=admin_user, customer=test_customer)

        policy = service.create_policy(
            name="new_policy",
            definition_yaml="---\n- get_config:\n    running: true",
            scope_json={"platform": "ios"},
            user=admin_user,
            context=context,
            description="New test policy",
        )

        assert policy.id is not None
        assert policy.name == "new_policy"
        assert policy.customer_id == test_customer.id
        assert policy.created_by == admin_user.id

    def test_create_policy_duplicate_name(self, db_session, test_customer, test_policy, admin_user):
        """Test creating policy with duplicate name raises ConflictError."""
        service = ComplianceService(db_session)
        context = TenantRequestContext(user=admin_user, customer=test_customer)

        with pytest.raises(ConflictError):
            service.create_policy(
                name=test_policy.name,
                definition_yaml="---\n- get_facts:\n    hostname: test",
                scope_json={},
                user=admin_user,
                context=context,
            )

    def test_create_policy_same_name_different_customer(
        self, db_session, second_customer, test_policy, admin_user
    ):
        """Test same policy name is allowed for different customers."""
        service = ComplianceService(db_session)
        context = TenantRequestContext(user=admin_user, customer=second_customer)

        policy = service.create_policy(
            name=test_policy.name,
            definition_yaml="---\n- get_facts:\n    hostname: test",
            scope_json={},
            user=admin_user,
            context=context,
        )

        assert policy.id is not None
        assert policy.customer_id == second_customer.id


class TestComplianceResults:
    """Tests for compliance result operations."""

    def test_list_results(self, db_session, test_customer, test_compliance_result, admin_user):
        """Test listing compliance results."""
        service = ComplianceService(db_session)
        context = TenantRequestContext(user=admin_user, customer=test_customer)

        results = service.list_results(context)

        assert len(results) >= 1
        assert any(r.id == test_compliance_result.id for r in results)

    def test_list_results_with_policy_filter(
        self, db_session, test_customer, test_policy, test_compliance_result, admin_user
    ):
        """Test listing results with policy filter."""
        service = ComplianceService(db_session)
        context = TenantRequestContext(user=admin_user, customer=test_customer)

        results = service.list_results(context, policy_id=test_policy.id)

        assert all(r.policy_id == test_policy.id for r in results)

    def test_list_results_with_device_filter(
        self, db_session, test_customer, test_device, test_compliance_result, admin_user
    ):
        """Test listing results with device filter."""
        service = ComplianceService(db_session)
        context = TenantRequestContext(user=admin_user, customer=test_customer)

        results = service.list_results(context, device_id=test_device.id)

        assert all(r.device_id == test_device.id for r in results)

    def test_get_device_compliance_summary(
        self, db_session, test_customer, test_device, test_compliance_result, admin_user
    ):
        """Test getting compliance summary for a device."""
        service = ComplianceService(db_session)
        context = TenantRequestContext(user=admin_user, customer=test_customer)

        summary = service.get_device_compliance_summary(test_device.id, context)

        assert summary["device_id"] == test_device.id
        assert "policies" in summary
        assert isinstance(summary["policies"], list)

    def test_get_device_compliance_summary_not_found(self, db_session, test_customer, admin_user):
        """Test getting summary for non-existent device raises NotFoundError."""
        service = ComplianceService(db_session)
        context = TenantRequestContext(user=admin_user, customer=test_customer)

        with pytest.raises(NotFoundError):
            service.get_device_compliance_summary(99999, context)
