"""Tests for API key management."""

from datetime import datetime, timedelta, timezone

import pytest

from app.db import APIKey
from app.domain.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.services.api_key_service import APIKeyService


class TestAPIKeyService:
    """Tests for APIKeyService."""

    def test_generate_key_format(self):
        """Generated keys should follow na_<32 chars> format."""
        key = APIKeyService.generate_key()
        assert key.startswith("na_")
        assert len(key) == 3 + 32  # "na_" + 32 chars

    def test_generate_key_uniqueness(self):
        """Each generated key should be unique."""
        keys = [APIKeyService.generate_key() for _ in range(100)]
        assert len(set(keys)) == 100

    def test_hash_key_consistency(self):
        """Hashing the same key should produce the same hash."""
        key = "na_test123456789012345678901234"
        hash1 = APIKeyService.hash_key(key)
        hash2 = APIKeyService.hash_key(key)
        assert hash1 == hash2

    def test_hash_key_different_inputs(self):
        """Different keys should produce different hashes."""
        key1 = "na_test123456789012345678901234"
        key2 = "na_test123456789012345678901235"
        assert APIKeyService.hash_key(key1) != APIKeyService.hash_key(key2)

    def test_get_prefix(self):
        """get_prefix should return first 8 characters."""
        key = "na_abcdefghijklmnopqrstuvwxyz1234"
        prefix = APIKeyService.get_prefix(key)
        assert prefix == "na_abcde"
        assert len(prefix) == 8

    def test_create_api_key(self, db_session, admin_user):
        """Create API key should return key model and plain key."""
        service = APIKeyService(db_session)
        api_key, plain_key = service.create_api_key(
            user=admin_user,
            name="Test Key",
        )

        assert api_key.id is not None
        assert api_key.user_id == admin_user.id
        assert api_key.name == "Test Key"
        assert api_key.is_active is True
        assert api_key.key_prefix == plain_key[:8]
        assert api_key.key_hash == APIKeyService.hash_key(plain_key)
        assert plain_key.startswith("na_")

    def test_create_api_key_with_expiry(self, db_session, admin_user):
        """Create API key with expiration date."""
        service = APIKeyService(db_session)
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)

        api_key, _ = service.create_api_key(
            user=admin_user,
            name="Expiring Key",
            expires_at=expires_at,
        )

        assert api_key.expires_at is not None

    def test_create_api_key_with_scopes(self, db_session, admin_user):
        """Create API key with custom scopes."""
        service = APIKeyService(db_session)
        scopes = {"read": True, "write": False}

        api_key, _ = service.create_api_key(
            user=admin_user,
            name="Scoped Key",
            scopes=scopes,
        )

        assert api_key.scopes == scopes

    def test_create_api_key_empty_name_raises(self, db_session, admin_user):
        """Creating key with empty name should raise ValidationError."""
        service = APIKeyService(db_session)

        with pytest.raises(ValidationError, match="name is required"):
            service.create_api_key(user=admin_user, name="")

        with pytest.raises(ValidationError, match="name is required"):
            service.create_api_key(user=admin_user, name="   ")

    def test_create_api_key_long_name_raises(self, db_session, admin_user):
        """Creating key with name > 100 chars should raise ValidationError."""
        service = APIKeyService(db_session)
        long_name = "x" * 101

        with pytest.raises(ValidationError, match="100 characters or less"):
            service.create_api_key(user=admin_user, name=long_name)

    def test_get_api_key_by_owner(self, db_session, admin_user):
        """Owner should be able to get their own API key."""
        service = APIKeyService(db_session)
        api_key, _ = service.create_api_key(user=admin_user, name="My Key")

        retrieved = service.get_api_key(api_key.id, admin_user)
        assert retrieved.id == api_key.id
        assert retrieved.name == "My Key"

    def test_get_api_key_not_found(self, db_session, admin_user):
        """Getting non-existent key should raise NotFoundError."""
        service = APIKeyService(db_session)

        with pytest.raises(NotFoundError, match="not found"):
            service.get_api_key(99999, admin_user)

    def test_get_api_key_by_other_user_raises(self, db_session, admin_user, operator_user):
        """Non-owner non-admin should not access others' keys."""
        service = APIKeyService(db_session)
        api_key, _ = service.create_api_key(user=admin_user, name="Admin Key")

        with pytest.raises(ForbiddenError, match="Access denied"):
            service.get_api_key(api_key.id, operator_user)

    def test_get_api_key_admin_can_access_any(self, db_session, admin_user, operator_user):
        """Admin should be able to access any user's key."""
        service = APIKeyService(db_session)
        api_key, _ = service.create_api_key(user=operator_user, name="Operator Key")

        retrieved = service.get_api_key(api_key.id, admin_user)
        assert retrieved.id == api_key.id

    def test_list_user_api_keys(self, db_session, admin_user):
        """List should return all keys for a user."""
        service = APIKeyService(db_session)
        service.create_api_key(user=admin_user, name="Key 1")
        service.create_api_key(user=admin_user, name="Key 2")
        service.create_api_key(user=admin_user, name="Key 3")

        keys = service.list_user_api_keys(admin_user)
        assert len(keys) == 3
        names = {k.name for k in keys}
        assert names == {"Key 1", "Key 2", "Key 3"}

    def test_list_user_api_keys_empty(self, db_session, admin_user):
        """List should return empty list for user with no keys."""
        service = APIKeyService(db_session)
        keys = service.list_user_api_keys(admin_user)
        assert len(keys) == 0

    def test_list_user_api_keys_isolation(self, db_session, admin_user, operator_user):
        """Users should only see their own keys."""
        service = APIKeyService(db_session)
        service.create_api_key(user=admin_user, name="Admin Key")
        service.create_api_key(user=operator_user, name="Operator Key")

        admin_keys = service.list_user_api_keys(admin_user)
        operator_keys = service.list_user_api_keys(operator_user)

        assert len(admin_keys) == 1
        assert admin_keys[0].name == "Admin Key"
        assert len(operator_keys) == 1
        assert operator_keys[0].name == "Operator Key"

    def test_validate_api_key_valid(self, db_session, admin_user):
        """Valid API key should return key and user."""
        service = APIKeyService(db_session)
        _, plain_key = service.create_api_key(user=admin_user, name="Valid Key")

        result = service.validate_api_key(plain_key)

        assert result is not None
        api_key, user = result
        assert user.id == admin_user.id
        assert api_key.name == "Valid Key"

    def test_validate_api_key_updates_last_used(self, db_session, admin_user):
        """Validating key should update last_used_at."""
        service = APIKeyService(db_session)
        api_key, plain_key = service.create_api_key(user=admin_user, name="Key")

        assert api_key.last_used_at is None

        service.validate_api_key(plain_key)
        db_session.refresh(api_key)

        assert api_key.last_used_at is not None

    def test_validate_api_key_invalid_returns_none(self, db_session):
        """Invalid API key should return None."""
        service = APIKeyService(db_session)

        assert service.validate_api_key("na_invalid123456789012345678901") is None
        assert service.validate_api_key("invalid_key") is None
        assert service.validate_api_key("") is None
        assert service.validate_api_key(None) is None

    def test_validate_api_key_revoked_returns_none(self, db_session, admin_user):
        """Revoked API key should return None."""
        service = APIKeyService(db_session)
        api_key, plain_key = service.create_api_key(user=admin_user, name="Key")
        service.revoke_api_key(api_key.id, admin_user)

        assert service.validate_api_key(plain_key) is None

    def test_validate_api_key_expired_returns_none(self, db_session, admin_user):
        """Expired API key should return None."""
        service = APIKeyService(db_session)
        expires_at = datetime.now(timezone.utc) - timedelta(hours=1)  # Expired

        api_key, plain_key = service.create_api_key(
            user=admin_user,
            name="Expired Key",
            expires_at=expires_at,
        )

        assert service.validate_api_key(plain_key) is None

    def test_validate_api_key_inactive_user_returns_none(self, db_session, admin_user):
        """API key for inactive user should return None."""
        service = APIKeyService(db_session)
        _, plain_key = service.create_api_key(user=admin_user, name="Key")

        admin_user.is_active = False
        db_session.commit()

        assert service.validate_api_key(plain_key) is None

    def test_revoke_api_key(self, db_session, admin_user):
        """Revoking key should deactivate it."""
        service = APIKeyService(db_session)
        api_key, _ = service.create_api_key(user=admin_user, name="Key")
        assert api_key.is_active is True

        service.revoke_api_key(api_key.id, admin_user)
        db_session.refresh(api_key)

        assert api_key.is_active is False

    def test_revoke_api_key_by_other_user_raises(self, db_session, admin_user, operator_user):
        """Non-owner should not be able to revoke others' keys."""
        service = APIKeyService(db_session)
        api_key, _ = service.create_api_key(user=admin_user, name="Key")

        with pytest.raises(ForbiddenError):
            service.revoke_api_key(api_key.id, operator_user)

    def test_delete_api_key(self, db_session, admin_user):
        """Deleting key should remove it from database."""
        service = APIKeyService(db_session)
        api_key, _ = service.create_api_key(user=admin_user, name="Key")
        key_id = api_key.id

        service.delete_api_key(key_id, admin_user)

        assert db_session.query(APIKey).filter(APIKey.id == key_id).first() is None

    def test_delete_api_key_by_other_user_raises(self, db_session, admin_user, operator_user):
        """Non-owner should not be able to delete others' keys."""
        service = APIKeyService(db_session)
        api_key, _ = service.create_api_key(user=admin_user, name="Key")

        with pytest.raises(ForbiddenError):
            service.delete_api_key(api_key.id, operator_user)


class TestAPIKeyEndpoints:
    """Tests for API key REST endpoints."""

    def test_create_api_key_endpoint(self, client, auth_headers):
        """POST /api-keys should create a new API key."""
        response = client.post(
            "/api/v1/api-keys",
            json={"name": "Test Key"},
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Key"
        assert data["key"].startswith("na_")
        assert data["is_active"] is True
        assert "key_prefix" in data
        assert "id" in data
        assert "created_at" in data

    def test_create_api_key_with_expiry(self, client, auth_headers):
        """POST /api-keys with expiration date."""
        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        response = client.post(
            "/api/v1/api-keys",
            json={"name": "Expiring Key", "expires_at": expires_at},
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["expires_at"] is not None

    def test_create_api_key_unauthenticated(self, client):
        """POST /api-keys without auth should return 401."""
        response = client.post("/api/v1/api-keys", json={"name": "Test Key"})
        assert response.status_code == 401

    def test_list_api_keys_endpoint(self, client, auth_headers):
        """GET /api-keys should list user's API keys."""
        # Create some keys first
        client.post("/api/v1/api-keys", json={"name": "Key 1"}, headers=auth_headers)
        client.post("/api/v1/api-keys", json={"name": "Key 2"}, headers=auth_headers)

        response = client.get("/api/v1/api-keys", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        names = {k["name"] for k in data}
        assert names == {"Key 1", "Key 2"}
        # Plain key should NOT be returned in list
        for key_data in data:
            assert "key" not in key_data or key_data.get("key") is None

    def test_list_api_keys_empty(self, client, auth_headers):
        """GET /api-keys should return empty list if no keys."""
        response = client.get("/api/v1/api-keys", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_get_api_key_endpoint(self, client, auth_headers):
        """GET /api-keys/{id} should return specific key."""
        create_resp = client.post(
            "/api/v1/api-keys",
            json={"name": "My Key"},
            headers=auth_headers,
        )
        key_id = create_resp.json()["id"]

        response = client.get(f"/api/v1/api-keys/{key_id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == key_id
        assert data["name"] == "My Key"
        # Plain key should NOT be returned
        assert "key" not in data or data.get("key") is None

    def test_get_api_key_not_found(self, client, auth_headers):
        """GET /api-keys/{id} for non-existent key should return 404."""
        response = client.get("/api/v1/api-keys/99999", headers=auth_headers)
        assert response.status_code == 404

    def test_revoke_api_key_endpoint(self, client, auth_headers):
        """POST /api-keys/{id}/revoke should deactivate key."""
        create_resp = client.post(
            "/api/v1/api-keys",
            json={"name": "Key to Revoke"},
            headers=auth_headers,
        )
        key_id = create_resp.json()["id"]

        response = client.post(f"/api/v1/api-keys/{key_id}/revoke", headers=auth_headers)
        assert response.status_code == 204

        # Verify it's revoked
        get_resp = client.get(f"/api/v1/api-keys/{key_id}", headers=auth_headers)
        assert get_resp.json()["is_active"] is False

    def test_delete_api_key_endpoint(self, client, auth_headers):
        """DELETE /api-keys/{id} should remove key."""
        create_resp = client.post(
            "/api/v1/api-keys",
            json={"name": "Key to Delete"},
            headers=auth_headers,
        )
        key_id = create_resp.json()["id"]

        response = client.delete(f"/api/v1/api-keys/{key_id}", headers=auth_headers)
        assert response.status_code == 204

        # Verify it's deleted
        get_resp = client.get(f"/api/v1/api-keys/{key_id}", headers=auth_headers)
        assert get_resp.status_code == 404


class TestAPIKeyAuthentication:
    """Tests for API key authentication flow."""

    def test_authenticate_with_api_key(self, client, auth_headers, test_customer):
        """Requests with valid X-API-Key should be authenticated."""
        # Create an API key
        create_resp = client.post(
            "/api/v1/api-keys",
            json={"name": "Auth Test Key"},
            headers=auth_headers,
        )
        plain_key = create_resp.json()["key"]

        # Use the API key to authenticate (without Bearer token)
        response = client.get(
            "/api/v1/devices",
            headers={"X-API-Key": plain_key, "X-Customer-ID": str(test_customer.id)},
        )

        assert response.status_code == 200

    def test_authenticate_with_invalid_api_key(self, client, test_customer):
        """Requests with invalid X-API-Key should return 401."""
        response = client.get(
            "/api/v1/devices",
            headers={
                "X-API-Key": "na_invalidkey12345678901234567890",
                "X-Customer-ID": str(test_customer.id),
            },
        )

        assert response.status_code == 401
        assert "Invalid or expired API key" in response.json()["detail"]

    def test_authenticate_with_revoked_api_key(self, client, auth_headers, test_customer):
        """Requests with revoked API key should return 401."""
        # Create and revoke an API key
        create_resp = client.post(
            "/api/v1/api-keys",
            json={"name": "Revoked Key"},
            headers=auth_headers,
        )
        key_id = create_resp.json()["id"]
        plain_key = create_resp.json()["key"]

        client.post(f"/api/v1/api-keys/{key_id}/revoke", headers=auth_headers)

        # Try to use the revoked key
        response = client.get(
            "/api/v1/devices",
            headers={"X-API-Key": plain_key, "X-Customer-ID": str(test_customer.id)},
        )

        assert response.status_code == 401

    def test_bearer_token_takes_precedence(self, client, auth_headers, test_customer):
        """When both Bearer and X-API-Key are provided, Bearer should not block API key."""
        # Create an API key
        create_resp = client.post(
            "/api/v1/api-keys",
            json={"name": "Test Key"},
            headers=auth_headers,
        )
        plain_key = create_resp.json()["key"]

        # Provide API key - should work even without Bearer
        response = client.get(
            "/api/v1/devices",
            headers={
                "X-API-Key": plain_key,
                "X-Customer-ID": str(test_customer.id),
            },
        )

        assert response.status_code == 200

    def test_no_auth_returns_401(self, client, test_customer):
        """Requests without any authentication should return 401."""
        response = client.get(
            "/api/v1/devices",
            headers={"X-Customer-ID": str(test_customer.id)},
        )

        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]
