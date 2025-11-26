"""Tests for Customer API endpoints."""

import pytest


class TestCustomerAPI:
    """Tests for customer CRUD endpoints."""

    def test_list_customers(self, client, auth_headers):
        """Test listing customers."""
        response = client.get("/api/v1/customers", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_list_customers_unauthorized(self, client):
        """Test listing customers without auth fails."""
        response = client.get("/api/v1/customers")

        assert response.status_code in (401, 403)

    def test_get_customer(self, client, auth_headers, test_customer):
        """Test getting a specific customer."""
        response = client.get(
            f"/api/v1/customers/{test_customer.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_customer.id
        assert data["name"] == test_customer.name

    def test_get_customer_not_found(self, client, auth_headers):
        """Test getting non-existent customer returns 404."""
        response = client.get("/api/v1/customers/99999", headers=auth_headers)

        assert response.status_code == 404

    def test_create_customer(self, client, auth_headers):
        """Test creating a new customer (admin)."""
        response = client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "new_api_customer"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "new_api_customer"
        assert "id" in data

    def test_create_customer_duplicate_name(self, client, auth_headers, test_customer):
        """Test creating customer with duplicate name fails."""
        response = client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": test_customer.name},
        )

        assert response.status_code == 400

    def test_create_customer_non_admin(self, client, operator_headers):
        """Test non-admin cannot create customers."""
        response = client.post(
            "/api/v1/customers",
            headers=operator_headers,
            json={"name": "should_fail"},
        )

        assert response.status_code == 403


class TestCustomerMembershipAPI:
    """Tests for customer membership endpoints."""

    def test_add_user_to_customer(self, client, auth_headers, second_customer, operator_user):
        """Test adding a user to a customer."""
        response = client.post(
            f"/api/v1/customers/{second_customer.id}/users/{operator_user.id}",
            headers=auth_headers,
        )

        assert response.status_code == 204

    def test_remove_user_from_customer(self, client, auth_headers, test_customer, operator_user):
        """Test removing a user from a customer."""
        response = client.delete(
            f"/api/v1/customers/{test_customer.id}/users/{operator_user.id}",
            headers=auth_headers,
        )

        assert response.status_code == 204

    def test_add_user_non_admin(self, client, operator_headers, test_customer, viewer_user):
        """Test non-admin cannot add users."""
        response = client.post(
            f"/api/v1/customers/{test_customer.id}/users/{viewer_user.id}",
            headers=operator_headers,
        )

        assert response.status_code == 403


class TestCustomerIPRangesAPI:
    """Tests for customer IP range endpoints."""

    def test_list_ip_ranges(self, client, auth_headers, test_customer):
        """Test listing IP ranges for a customer."""
        response = client.get(
            f"/api/v1/customers/{test_customer.id}/ranges",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_create_ip_range(self, client, auth_headers, test_customer):
        """Test creating an IP range."""
        response = client.post(
            f"/api/v1/customers/{test_customer.id}/ranges",
            headers=auth_headers,
            json={"cidr": "192.168.0.0/24", "description": "Test range"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["cidr"] == "192.168.0.0/24"

    def test_create_ip_range_invalid_cidr(self, client, auth_headers, test_customer):
        """Test creating IP range with invalid CIDR fails."""
        response = client.post(
            f"/api/v1/customers/{test_customer.id}/ranges",
            headers=auth_headers,
            json={"cidr": "not-a-cidr"},
        )

        assert response.status_code == 422

    def test_create_ip_range_non_admin(self, client, operator_headers, test_customer):
        """Test non-admin cannot create IP ranges."""
        response = client.post(
            f"/api/v1/customers/{test_customer.id}/ranges",
            headers=operator_headers,
            json={"cidr": "10.0.0.0/8"},
        )

        assert response.status_code == 403

    def test_delete_ip_range(self, client, auth_headers, test_customer, db_session):
        """Test deleting an IP range."""
        # First create a range
        create_response = client.post(
            f"/api/v1/customers/{test_customer.id}/ranges",
            headers=auth_headers,
            json={"cidr": "172.16.0.0/16"},
        )
        range_id = create_response.json()["id"]

        # Delete it
        response = client.delete(
            f"/api/v1/customers/{test_customer.id}/ranges/{range_id}",
            headers=auth_headers,
        )

        assert response.status_code == 204

    def test_delete_ip_range_not_found(self, client, auth_headers, test_customer):
        """Test deleting non-existent IP range fails."""
        response = client.delete(
            f"/api/v1/customers/{test_customer.id}/ranges/99999",
            headers=auth_headers,
        )

        assert response.status_code == 404
