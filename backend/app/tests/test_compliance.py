"""Tests for Compliance API endpoints."""

from unittest.mock import MagicMock, patch

import pytest

from app.db.models import CompliancePolicy


@pytest.fixture
def test_policy(db_session, test_customer, admin_user):
    """Create a test compliance policy."""
    policy = CompliancePolicy(
        name="api_test_policy",
        description="Test policy for API tests",
        scope_json={"vendor": "cisco"},
        definition_yaml="---\n- get_facts:\n    hostname: test",
        created_by=admin_user.id,
        customer_id=test_customer.id,
    )
    db_session.add(policy)
    db_session.commit()
    db_session.refresh(policy)
    return policy


class TestCompliancePolicyAPI:
    """Tests for compliance policy endpoints."""

    def test_list_policies(self, client, auth_headers, test_policy):
        """Test listing compliance policies."""
        response = client.get("/api/v1/compliance/policies", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_list_policies_unauthorized(self, client):
        """Test listing policies without auth fails."""
        response = client.get("/api/v1/compliance/policies")

        assert response.status_code in (401, 403)

    def test_list_policies_pagination(self, client, auth_headers, test_policy):
        """Test listing policies with pagination."""
        response = client.get(
            "/api/v1/compliance/policies?skip=0&limit=1",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 1

    def test_get_policy(self, client, auth_headers, test_policy):
        """Test getting a specific policy."""
        response = client.get(
            f"/api/v1/compliance/policies/{test_policy.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_policy.id
        assert data["name"] == test_policy.name

    def test_get_policy_not_found(self, client, auth_headers):
        """Test getting non-existent policy returns 404."""
        response = client.get(
            "/api/v1/compliance/policies/99999",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_create_policy(self, client, auth_headers):
        """Test creating a new policy (admin)."""
        response = client.post(
            "/api/v1/compliance/policies",
            headers=auth_headers,
            json={
                "name": "new_api_policy",
                "definition_yaml": "---\n- get_config:\n    running: true",
                "scope_json": {"platform": "ios"},
                "description": "Created via API",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "new_api_policy"

    def test_create_policy_duplicate_name(self, client, auth_headers, test_policy):
        """Test creating policy with duplicate name fails."""
        response = client.post(
            "/api/v1/compliance/policies",
            headers=auth_headers,
            json={
                "name": test_policy.name,
                "definition_yaml": "---",
                "scope_json": {},
            },
        )

        assert response.status_code == 400

    def test_create_policy_non_admin(self, client, operator_headers):
        """Test non-admin cannot create policies."""
        response = client.post(
            "/api/v1/compliance/policies",
            headers=operator_headers,
            json={
                "name": "should_fail",
                "definition_yaml": "---",
                "scope_json": {},
            },
        )

        assert response.status_code == 403

    def test_update_policy(self, client, auth_headers, test_policy):
        """Test updating a policy (admin)."""
        response = client.put(
            f"/api/v1/compliance/policies/{test_policy.id}",
            headers=auth_headers,
            json={
                "name": "updated_policy_name",
                "description": "Updated description",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "updated_policy_name"
        assert data["description"] == "Updated description"

    def test_update_policy_partial(self, client, auth_headers, test_policy):
        """Test partial policy update."""
        original_name = test_policy.name
        response = client.put(
            f"/api/v1/compliance/policies/{test_policy.id}",
            headers=auth_headers,
            json={"scope_json": {"vendor": "arista"}},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == original_name
        assert data["scope_json"] == {"vendor": "arista"}

    def test_update_policy_not_found(self, client, auth_headers):
        """Test updating non-existent policy fails."""
        response = client.put(
            "/api/v1/compliance/policies/99999",
            headers=auth_headers,
            json={"name": "should_fail"},
        )

        assert response.status_code == 404

    def test_update_policy_non_admin(self, client, operator_headers, test_policy):
        """Test non-admin cannot update policies."""
        response = client.put(
            f"/api/v1/compliance/policies/{test_policy.id}",
            headers=operator_headers,
            json={"name": "should_fail"},
        )

        assert response.status_code == 403

    def test_update_policy_duplicate_name(
        self, client, auth_headers, test_policy, db_session, test_customer, admin_user
    ):
        """Test updating policy to duplicate name fails."""
        # Create another policy
        other_policy = CompliancePolicy(
            name="other_policy",
            scope_json={},
            definition_yaml="---",
            created_by=admin_user.id,
            customer_id=test_customer.id,
        )
        db_session.add(other_policy)
        db_session.commit()

        response = client.put(
            f"/api/v1/compliance/policies/{test_policy.id}",
            headers=auth_headers,
            json={"name": "other_policy"},
        )

        assert response.status_code == 400

    def test_delete_policy(self, client, auth_headers, db_session, test_customer, admin_user):
        """Test deleting a policy (admin)."""
        # Create a policy to delete
        policy = CompliancePolicy(
            name="policy_to_delete",
            scope_json={},
            definition_yaml="---",
            created_by=admin_user.id,
            customer_id=test_customer.id,
        )
        db_session.add(policy)
        db_session.commit()
        db_session.refresh(policy)
        policy_id = policy.id

        response = client.delete(
            f"/api/v1/compliance/policies/{policy_id}",
            headers=auth_headers,
        )

        assert response.status_code == 204

        # Verify it's gone
        get_response = client.get(
            f"/api/v1/compliance/policies/{policy_id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404

    def test_delete_policy_not_found(self, client, auth_headers):
        """Test deleting non-existent policy fails."""
        response = client.delete(
            "/api/v1/compliance/policies/99999",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_delete_policy_non_admin(self, client, operator_headers, test_policy):
        """Test non-admin cannot delete policies."""
        response = client.delete(
            f"/api/v1/compliance/policies/{test_policy.id}",
            headers=operator_headers,
        )

        assert response.status_code == 403


class TestComplianceRunAPI:
    """Tests for compliance run endpoint."""

    @patch("app.api.compliance.celery_app")
    def test_run_compliance(self, mock_celery, client, auth_headers, test_policy):
        """Test running a compliance check."""
        mock_celery.send_task = MagicMock()

        response = client.post(
            "/api/v1/compliance/run",
            headers=auth_headers,
            json={"policy_id": test_policy.id},
        )

        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "queued"
        mock_celery.send_task.assert_called_once()

    def test_run_compliance_policy_not_found(self, client, auth_headers):
        """Test running compliance with invalid policy fails."""
        response = client.post(
            "/api/v1/compliance/run",
            headers=auth_headers,
            json={"policy_id": 99999},
        )

        assert response.status_code == 404


class TestComplianceResultsAPI:
    """Tests for compliance results endpoints."""

    def test_list_results(self, client, auth_headers):
        """Test listing compliance results."""
        response = client.get("/api/v1/compliance/results", headers=auth_headers)

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_list_results_with_filters(self, client, auth_headers, test_policy):
        """Test listing results with policy filter."""
        response = client.get(
            f"/api/v1/compliance/results?policy_id={test_policy.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200

    def test_get_device_compliance_summary(self, client, auth_headers, test_device):
        """Test getting device compliance summary."""
        response = client.get(
            f"/api/v1/compliance/devices/{test_device.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["device_id"] == test_device.id
        assert "policies" in data

    def test_get_device_compliance_not_found(self, client, auth_headers):
        """Test getting compliance for non-existent device fails."""
        response = client.get(
            "/api/v1/compliance/devices/99999",
            headers=auth_headers,
        )

        assert response.status_code == 404


def test_compliance_overview(
    client, auth_headers, db_session, admin_user, test_customer, test_credential
):
    """Ensure overview returns policy stats and recent results with names."""
    from app.db.models import CompliancePolicy, ComplianceResult, Device, Job

    device = Device(
        hostname="ov-dev1",
        mgmt_ip="192.0.2.200",
        vendor="cisco",
        platform="ios",
        credentials_ref=test_credential.id,
        customer_id=test_customer.id,
        enabled=True,
    )
    policy = CompliancePolicy(
        name="overview-policy",
        scope_json={},
        definition_yaml="---",
        created_by=admin_user.id,
        customer_id=test_customer.id,
    )
    job = Job(
        type="compliance_check",
        status="success",
        user_id=admin_user.id,
        customer_id=test_customer.id,
    )
    db_session.add_all([device, policy, job])
    db_session.commit()
    db_session.refresh(device)
    db_session.refresh(policy)
    db_session.refresh(job)

    result = ComplianceResult(
        policy_id=policy.id,
        device_id=device.id,
        job_id=job.id,
        status="pass",
        details_json={"complies": True},
    )
    db_session.add(result)
    db_session.commit()

    response = client.get("/api/v1/compliance/overview", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "policies" in data and "recent_results" in data

    policy_entry = next((p for p in data["policies"] if p["policy_id"] == policy.id), None)
    assert policy_entry is not None
    assert policy_entry["total"] == 1
    assert policy_entry["pass_count"] == 1

    recent = data["recent_results"][0]
    assert recent["policy_name"] == policy.name
    assert recent["device_hostname"] == device.hostname
    assert data["latest_by_policy"]
    assert any(entry["policy_id"] == policy.id for entry in data["latest_by_policy"])


def test_compliance_result_detail_and_filters(
    client, auth_headers, db_session, admin_user, test_customer, test_credential
):
    """Detail endpoint should enforce tenant scope and filters should apply."""
    from datetime import datetime, timedelta

    from app.db.models import CompliancePolicy, ComplianceResult, Device, Job

    device = Device(
        hostname="filter-dev1",
        mgmt_ip="192.0.2.201",
        vendor="cisco",
        platform="ios",
        credentials_ref=test_credential.id,
        customer_id=test_customer.id,
        enabled=True,
    )
    policy = CompliancePolicy(
        name="filter-policy",
        scope_json={},
        definition_yaml="---",
        created_by=admin_user.id,
        customer_id=test_customer.id,
    )
    job = Job(
        type="compliance_check",
        status="success",
        user_id=admin_user.id,
        customer_id=test_customer.id,
    )
    db_session.add_all([device, policy, job])
    db_session.commit()
    db_session.refresh(device)
    db_session.refresh(policy)
    db_session.refresh(job)

    ts = datetime.utcnow()
    result = ComplianceResult(
        policy_id=policy.id,
        device_id=device.id,
        job_id=job.id,
        status="fail",
        ts=ts,
        details_json={"complies": False},
    )
    db_session.add(result)
    db_session.commit()
    db_session.refresh(result)

    detail_resp = client.get(f"/api/v1/compliance/results/{result.id}", headers=auth_headers)
    assert detail_resp.status_code == 200
    assert detail_resp.json()["policy_id"] == policy.id

    start = (ts - timedelta(minutes=1)).isoformat()
    end = (ts + timedelta(minutes=1)).isoformat()
    filter_resp = client.get(
        f"/api/v1/compliance/results?policy_id={policy.id}&start={start}&end={end}",
        headers=auth_headers,
    )
    assert filter_resp.status_code == 200
    filtered = filter_resp.json()
    assert any(r["id"] == result.id for r in filtered)
