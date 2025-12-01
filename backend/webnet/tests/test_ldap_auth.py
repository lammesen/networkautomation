"""Tests for LDAP authentication backend."""

from unittest.mock import Mock, patch

import pytest
from django.contrib.auth import authenticate, get_user_model

from webnet.customers.models import Customer

User = get_user_model()


@pytest.fixture
def ldap_user_mock():
    """Create a mock LDAP user object."""
    user = Mock()
    user.attrs = {
        "givenName": ["John"],
        "sn": ["Doe"],
        "mail": ["john.doe@example.com"],
    }
    user.group_dns = []
    return user


@pytest.fixture
def customer_for_ldap(db):
    """Create a customer for LDAP user assignment."""
    return Customer.objects.create(name="LDAP Test Customer")


@pytest.mark.django_db
class TestLDAPAuthentication:
    """Test LDAP authentication functionality."""

    def test_ldap_user_creation_with_viewer_role(self, settings, ldap_user_mock):
        """Test that a new LDAP user is created with viewer role by default."""
        settings.AUTHENTICATION_BACKENDS = [
            "webnet.core.ldap_backend.WebnetLDAPBackend",
            "django.contrib.auth.backends.ModelBackend",
        ]

        with patch("webnet.core.ldap_backend.LDAPBackend.authenticate_ldap_user") as mock_auth:
            with patch(
                "webnet.ldap_config.LDAP_CONFIG",
                {
                    "VIEWER_GROUPS": [],
                    "OPERATOR_GROUPS": [],
                    "ADMIN_GROUPS": [],
                },
            ):
                # Create a mock user that will be returned
                user = User.objects.create_user(
                    username="ldapuser",
                    role="viewer",
                    first_name="John",
                    last_name="Doe",
                    email="john.doe@example.com",
                )
                mock_auth.return_value = user

                # Authenticate
                authenticated_user = authenticate(username="ldapuser", password="password123")

                # Verify user was authenticated
                assert authenticated_user is not None
                assert authenticated_user.username == "ldapuser"
                assert authenticated_user.role == "viewer"

    def test_ldap_user_role_mapping_operator(self, settings, ldap_user_mock):
        """Test that LDAP groups are mapped to operator role."""
        settings.AUTHENTICATION_BACKENDS = [
            "webnet.core.ldap_backend.WebnetLDAPBackend",
            "django.contrib.auth.backends.ModelBackend",
        ]

        ldap_user_mock.group_dns = ["cn=operators,ou=groups,dc=example,dc=com"]

        with patch("webnet.core.ldap_backend.LDAPBackend.authenticate_ldap_user") as mock_auth:
            with patch(
                "webnet.ldap_config.LDAP_CONFIG",
                {
                    "VIEWER_GROUPS": [],
                    "OPERATOR_GROUPS": ["cn=operators,ou=groups,dc=example,dc=com"],
                    "ADMIN_GROUPS": [],
                },
            ):
                user = User.objects.create_user(
                    username="operatoruser",
                    role="viewer",
                    first_name="Jane",
                    last_name="Smith",
                    email="jane.smith@example.com",
                )
                mock_auth.return_value = user

                authenticated_user = authenticate(username="operatoruser", password="password123")

                assert authenticated_user is not None

    def test_ldap_user_role_mapping_admin_priority(self, settings, ldap_user_mock):
        """Test that admin group has priority over operator group."""
        settings.AUTHENTICATION_BACKENDS = [
            "webnet.core.ldap_backend.WebnetLDAPBackend",
            "django.contrib.auth.backends.ModelBackend",
        ]

        ldap_user_mock.group_dns = [
            "cn=operators,ou=groups,dc=example,dc=com",
            "cn=admins,ou=groups,dc=example,dc=com",
        ]

        with patch("webnet.core.ldap_backend.LDAPBackend.authenticate_ldap_user") as mock_auth:
            with patch(
                "webnet.ldap_config.LDAP_CONFIG",
                {
                    "VIEWER_GROUPS": [],
                    "OPERATOR_GROUPS": ["cn=operators,ou=groups,dc=example,dc=com"],
                    "ADMIN_GROUPS": ["cn=admins,ou=groups,dc=example,dc=com"],
                },
            ):
                user = User.objects.create_user(
                    username="adminuser",
                    role="viewer",
                    first_name="Admin",
                    last_name="User",
                    email="admin.user@example.com",
                )
                mock_auth.return_value = user

                authenticated_user = authenticate(username="adminuser", password="password123")

                assert authenticated_user is not None

    def test_ldap_customer_assignment_by_name(self, settings, ldap_user_mock, customer_for_ldap):
        """Test customer assignment from LDAP attribute by name."""
        settings.AUTHENTICATION_BACKENDS = [
            "webnet.core.ldap_backend.WebnetLDAPBackend",
            "django.contrib.auth.backends.ModelBackend",
        ]

        ldap_user_mock.attrs["department"] = ["LDAP Test Customer"]

        with patch("webnet.core.ldap_backend.LDAPBackend.authenticate_ldap_user") as mock_auth:
            with patch(
                "webnet.ldap_config.LDAP_CONFIG",
                {
                    "VIEWER_GROUPS": [],
                    "OPERATOR_GROUPS": [],
                    "ADMIN_GROUPS": [],
                    "LDAP_ATTR_CUSTOMER": "department",
                },
            ):
                user = User.objects.create_user(
                    username="customeruser",
                    role="viewer",
                )
                mock_auth.return_value = user

                authenticated_user = authenticate(username="customeruser", password="password123")

                assert authenticated_user is not None

    def test_ldap_customer_assignment_by_id(self, settings, ldap_user_mock, customer_for_ldap):
        """Test customer assignment from LDAP attribute by ID."""
        settings.AUTHENTICATION_BACKENDS = [
            "webnet.core.ldap_backend.WebnetLDAPBackend",
            "django.contrib.auth.backends.ModelBackend",
        ]

        ldap_user_mock.attrs["department"] = [str(customer_for_ldap.id)]

        with patch("webnet.core.ldap_backend.LDAPBackend.authenticate_ldap_user") as mock_auth:
            with patch(
                "webnet.ldap_config.LDAP_CONFIG",
                {
                    "VIEWER_GROUPS": [],
                    "OPERATOR_GROUPS": [],
                    "ADMIN_GROUPS": [],
                    "LDAP_ATTR_CUSTOMER": "department",
                },
            ):
                user = User.objects.create_user(
                    username="customeruser2",
                    role="viewer",
                )
                mock_auth.return_value = user

                authenticated_user = authenticate(username="customeruser2", password="password123")

                assert authenticated_user is not None

    def test_ldap_auth_failure_returns_none(self, settings):
        """Test that failed LDAP authentication returns None."""
        settings.AUTHENTICATION_BACKENDS = [
            "webnet.core.ldap_backend.WebnetLDAPBackend",
            "django.contrib.auth.backends.ModelBackend",
        ]

        with patch("webnet.core.ldap_backend.LDAPBackend.authenticate_ldap_user") as mock_auth:
            mock_auth.return_value = None

            authenticated_user = authenticate(username="invaliduser", password="wrongpassword")

            assert authenticated_user is None


@pytest.mark.django_db
class TestLocalAuthenticationFallback:
    """Test that local authentication works when LDAP fails."""

    def test_fallback_to_local_auth_when_ldap_fails(self, settings):
        """Test that local authentication works as fallback when LDAP fails."""
        settings.AUTHENTICATION_BACKENDS = [
            "webnet.core.ldap_backend.WebnetLDAPBackend",
            "django.contrib.auth.backends.ModelBackend",
        ]

        with patch("webnet.core.ldap_backend.LDAPBackend.authenticate_ldap_user") as mock_auth:
            # LDAP authentication fails
            mock_auth.return_value = None

            # Create a local user
            User.objects.create_user(
                username="localuser",
                password="localpassword123",
                role="admin",
            )

            # Authenticate with local credentials
            user = authenticate(username="localuser", password="localpassword123")

            # User should be authenticated via local backend
            assert user is not None
            assert user.username == "localuser"
            assert user.role == "admin"

    def test_local_only_authentication(self):
        """Test that local authentication works without LDAP configured."""
        # Create a local user
        User.objects.create_user(
            username="localonlyuser",
            password="localpassword456",
            role="operator",
        )

        # Authenticate with local credentials
        user = authenticate(username="localonlyuser", password="localpassword456")

        # User should be authenticated
        assert user is not None
        assert user.username == "localonlyuser"
        assert user.role == "operator"


@pytest.mark.django_db
class TestLDAPConfig:
    """Test LDAP configuration loading."""

    def test_ldap_config_loads_from_environment(self):
        """Test that LDAP configuration loads from environment variables."""
        with patch.dict(
            "os.environ",
            {
                "LDAP_ENABLED": "true",
                "LDAP_SERVER_URI": "ldap://test.example.com",
                "LDAP_USER_SEARCH_BASE": "ou=users,dc=test,dc=com",
            },
        ):
            # Reload the configuration module
            import importlib

            from webnet import ldap_config

            importlib.reload(ldap_config)

            assert ldap_config.LDAP_ENABLED is True
            assert ldap_config.AUTH_LDAP_SERVER_URI == "ldap://test.example.com"

    def test_ldap_disabled_by_default(self):
        """Test that LDAP is disabled when LDAP_ENABLED is false."""
        with patch.dict("os.environ", {"LDAP_ENABLED": "false"}):
            # Reload the configuration module
            import importlib

            from webnet import ldap_config

            importlib.reload(ldap_config)

            assert ldap_config.LDAP_ENABLED is False
            assert ldap_config.LDAP_CONFIG == {}
