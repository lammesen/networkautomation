"""Tests for CredentialService."""

import pytest
from pydantic import BaseModel

from app.domain.context import TenantRequestContext
from app.domain.exceptions import ConflictError, NotFoundError
from app.services.credential_service import CredentialService


class CredentialCreatePayload(BaseModel):
    """Mock payload for credential creation."""

    name: str
    username: str
    password: str


class TestCredentialService:
    """Tests for credential CRUD operations."""

    def test_list_credentials(self, db_session, test_customer, test_credential, admin_user):
        """Test listing credentials for a customer."""
        service = CredentialService(db_session)
        context = TenantRequestContext(user=admin_user, customer=test_customer)

        credentials = service.list_credentials(context)

        assert len(credentials) >= 1
        assert any(c.id == test_credential.id for c in credentials)

    def test_get_credential_success(self, db_session, test_customer, test_credential, admin_user):
        """Test getting a credential by ID."""
        service = CredentialService(db_session)
        context = TenantRequestContext(user=admin_user, customer=test_customer)

        credential = service.get_credential(test_credential.id, context)

        assert credential.id == test_credential.id
        assert credential.name == test_credential.name

    def test_get_credential_not_found(self, db_session, test_customer, admin_user):
        """Test getting non-existent credential raises NotFoundError."""
        service = CredentialService(db_session)
        context = TenantRequestContext(user=admin_user, customer=test_customer)

        with pytest.raises(NotFoundError):
            service.get_credential(99999, context)

    def test_get_credential_wrong_customer(
        self, db_session, second_customer, test_credential, admin_user
    ):
        """Test getting credential from wrong customer raises NotFoundError."""
        service = CredentialService(db_session)
        context = TenantRequestContext(user=admin_user, customer=second_customer)

        with pytest.raises(NotFoundError):
            service.get_credential(test_credential.id, context)

    def test_create_credential(self, db_session, test_customer, admin_user):
        """Test creating a new credential."""
        service = CredentialService(db_session)
        context = TenantRequestContext(user=admin_user, customer=test_customer)
        payload = CredentialCreatePayload(
            name="new_cred",
            username="newuser",
            password="newpass",
        )

        credential = service.create_credential(payload, context)

        assert credential.id is not None
        assert credential.name == "new_cred"
        assert credential.username == "newuser"
        assert credential.customer_id == test_customer.id

    def test_create_credential_duplicate_name(
        self, db_session, test_customer, test_credential, admin_user
    ):
        """Test creating credential with duplicate name raises ConflictError."""
        service = CredentialService(db_session)
        context = TenantRequestContext(user=admin_user, customer=test_customer)
        payload = CredentialCreatePayload(
            name=test_credential.name,
            username="anotheruser",
            password="anotherpass",
        )

        with pytest.raises(ConflictError) as exc_info:
            service.create_credential(payload, context)

        assert "already exists" in str(exc_info.value.message)

    def test_create_credential_same_name_different_customer(
        self, db_session, second_customer, test_credential, admin_user
    ):
        """Test same credential name is allowed for different customers."""
        service = CredentialService(db_session)
        context = TenantRequestContext(user=admin_user, customer=second_customer)
        payload = CredentialCreatePayload(
            name=test_credential.name,
            username="user2",
            password="pass2",
        )

        credential = service.create_credential(payload, context)

        assert credential.id is not None
        assert credential.customer_id == second_customer.id
