"""Tests for CustomerService."""

import pytest
from pydantic import BaseModel

from app.db.models import Customer, User
from app.domain.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.services.customer_service import CustomerService


class CustomerCreatePayload(BaseModel):
    """Mock payload for customer creation."""

    name: str


class IPRangeCreatePayload(BaseModel):
    """Mock payload for IP range creation."""

    cidr: str
    description: str | None = None


class TestCustomerService:
    """Tests for customer CRUD operations."""

    def test_create_customer(self, db_session):
        """Test creating a new customer."""
        service = CustomerService(db_session)
        payload = CustomerCreatePayload(name="new_customer")

        customer = service.create_customer(payload)

        assert customer.id is not None
        assert customer.name == "new_customer"

    def test_create_customer_duplicate_name(self, db_session, test_customer):
        """Test creating a customer with duplicate name raises ConflictError."""
        service = CustomerService(db_session)
        payload = CustomerCreatePayload(name=test_customer.name)

        with pytest.raises(ConflictError) as exc_info:
            service.create_customer(payload)

        assert "already exists" in str(exc_info.value.message)

    def test_list_customers_admin(self, db_session, admin_user, test_customer, second_customer):
        """Test admin can list all customers."""
        service = CustomerService(db_session)

        customers = service.list_customers(admin_user)

        assert len(customers) >= 2
        customer_names = [c.name for c in customers]
        assert test_customer.name in customer_names
        assert second_customer.name in customer_names

    def test_list_customers_non_admin(self, db_session, operator_user, test_customer):
        """Test non-admin user sees only their assigned customers."""
        service = CustomerService(db_session)

        customers = service.list_customers(operator_user)

        assert len(customers) == 1
        assert customers[0].id == test_customer.id

    def test_get_customer_success(self, db_session, admin_user, test_customer):
        """Test getting a customer by ID."""
        service = CustomerService(db_session)

        customer = service.get_customer(test_customer.id, admin_user)

        assert customer.id == test_customer.id
        assert customer.name == test_customer.name

    def test_get_customer_not_found(self, db_session, admin_user):
        """Test getting non-existent customer raises NotFoundError."""
        service = CustomerService(db_session)

        with pytest.raises(NotFoundError):
            service.get_customer(99999, admin_user)

    def test_get_customer_forbidden(self, db_session, operator_user, second_customer):
        """Test non-admin cannot access unassigned customer."""
        service = CustomerService(db_session)

        with pytest.raises(ForbiddenError):
            service.get_customer(second_customer.id, operator_user)


class TestCustomerMembership:
    """Tests for customer-user membership operations."""

    def test_add_user_to_customer(self, db_session, second_customer, operator_user):
        """Test adding a user to a customer."""
        service = CustomerService(db_session)

        service.add_user_to_customer(second_customer.id, operator_user.id)

        db_session.refresh(second_customer)
        assert operator_user in second_customer.users

    def test_add_user_to_customer_already_member(self, db_session, test_customer, operator_user):
        """Test adding a user who is already a member is idempotent."""
        service = CustomerService(db_session)

        # Should not raise
        service.add_user_to_customer(test_customer.id, operator_user.id)

    def test_remove_user_from_customer(self, db_session, test_customer, operator_user):
        """Test removing a user from a customer."""
        service = CustomerService(db_session)

        service.remove_user_from_customer(test_customer.id, operator_user.id)

        db_session.refresh(test_customer)
        assert operator_user not in test_customer.users

    def test_remove_user_not_member(self, db_session, second_customer, operator_user):
        """Test removing a user who is not a member is idempotent."""
        service = CustomerService(db_session)

        # Should not raise
        service.remove_user_from_customer(second_customer.id, operator_user.id)

    def test_add_user_to_nonexistent_customer(self, db_session, operator_user):
        """Test adding user to non-existent customer raises NotFoundError."""
        service = CustomerService(db_session)

        with pytest.raises(NotFoundError):
            service.add_user_to_customer(99999, operator_user.id)

    def test_add_nonexistent_user_to_customer(self, db_session, test_customer):
        """Test adding non-existent user raises NotFoundError."""
        service = CustomerService(db_session)

        with pytest.raises(NotFoundError):
            service.add_user_to_customer(test_customer.id, 99999)


class TestIPRanges:
    """Tests for customer IP range operations."""

    def test_list_ip_ranges(self, db_session, admin_user, test_customer):
        """Test listing IP ranges for a customer."""
        service = CustomerService(db_session)

        ranges = service.list_ip_ranges(test_customer.id, admin_user)

        assert isinstance(ranges, (list, tuple))

    def test_create_ip_range(self, db_session, test_customer):
        """Test creating an IP range."""
        service = CustomerService(db_session)
        payload = IPRangeCreatePayload(cidr="10.0.0.0/24", description="Test range")

        ip_range = service.create_ip_range(test_customer.id, payload)

        assert ip_range.id is not None
        assert ip_range.cidr == "10.0.0.0/24"
        assert ip_range.customer_id == test_customer.id

    def test_create_ip_range_duplicate(self, db_session, test_customer):
        """Test creating duplicate IP range raises ConflictError."""
        service = CustomerService(db_session)
        payload = IPRangeCreatePayload(cidr="10.1.0.0/24")

        service.create_ip_range(test_customer.id, payload)

        with pytest.raises(ConflictError):
            service.create_ip_range(test_customer.id, payload)

    def test_create_ip_range_invalid_cidr(self, db_session, test_customer):
        """Test creating IP range with invalid CIDR raises ValidationError."""
        service = CustomerService(db_session)
        payload = IPRangeCreatePayload(cidr="invalid-cidr")

        with pytest.raises(ValidationError):
            service.create_ip_range(test_customer.id, payload)

    def test_delete_ip_range(self, db_session, test_customer):
        """Test deleting an IP range."""
        service = CustomerService(db_session)
        payload = IPRangeCreatePayload(cidr="10.2.0.0/24")
        ip_range = service.create_ip_range(test_customer.id, payload)

        service.delete_ip_range(test_customer.id, ip_range.id)

        # Verify deletion
        with pytest.raises(NotFoundError):
            service.delete_ip_range(test_customer.id, ip_range.id)

    def test_delete_ip_range_not_found(self, db_session, test_customer):
        """Test deleting non-existent IP range raises NotFoundError."""
        service = CustomerService(db_session)

        with pytest.raises(NotFoundError):
            service.delete_ip_range(test_customer.id, 99999)
