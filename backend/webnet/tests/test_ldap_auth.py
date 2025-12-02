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
class TestLDAPBackendDirectly:
    """Test WebnetLDAPBackend.authenticate_ldap_user method directly."""

    def test_role_mapping_viewer_default(self):
        """Test that users get viewer role by default when not in any groups."""
        from webnet.core.ldap_backend import WebnetLDAPBackend

        backend = WebnetLDAPBackend()

        user = User.objects.create_user(username="testuser", role="admin")

        ldap_user_mock = Mock()
        ldap_user_mock.attrs = {}
        ldap_user_mock.group_dns = []

        with patch("webnet.core.ldap_backend.LDAPBackend.authenticate_ldap_user") as mock_parent:
            with patch(
                "webnet.ldap_config.LDAP_CONFIG",
                {
                    "VIEWER_GROUPS": [],
                    "OPERATOR_GROUPS": [],
                    "ADMIN_GROUPS": [],
                },
            ):
                mock_parent.return_value = user

                result = backend.authenticate_ldap_user(ldap_user_mock, "password")

                assert result is not None
                assert result.role == "viewer"

    def test_role_mapping_operator(self):
        """Test that LDAP groups are mapped to operator role."""
        from webnet.core.ldap_backend import WebnetLDAPBackend

        backend = WebnetLDAPBackend()

        user = User.objects.create_user(username="operatoruser", role="viewer")

        ldap_user_mock = Mock()
        ldap_user_mock.attrs = {}
        ldap_user_mock.group_dns = ["cn=operators,ou=groups,dc=example,dc=com"]

        with patch("webnet.core.ldap_backend.LDAPBackend.authenticate_ldap_user") as mock_parent:
            with patch(
                "webnet.ldap_config.LDAP_CONFIG",
                {
                    "VIEWER_GROUPS": [],
                    "OPERATOR_GROUPS": ["cn=operators,ou=groups,dc=example,dc=com"],
                    "ADMIN_GROUPS": [],
                },
            ):
                mock_parent.return_value = user

                result = backend.authenticate_ldap_user(ldap_user_mock, "password")

                assert result is not None
                assert result.role == "operator"

    def test_role_mapping_admin_priority(self):
        """Test that admin group has priority over operator group."""
        from webnet.core.ldap_backend import WebnetLDAPBackend

        backend = WebnetLDAPBackend()

        user = User.objects.create_user(username="adminuser", role="viewer")

        ldap_user_mock = Mock()
        ldap_user_mock.attrs = {}
        ldap_user_mock.group_dns = [
            "cn=operators,ou=groups,dc=example,dc=com",
            "cn=admins,ou=groups,dc=example,dc=com",
        ]

        with patch("webnet.core.ldap_backend.LDAPBackend.authenticate_ldap_user") as mock_parent:
            with patch(
                "webnet.ldap_config.LDAP_CONFIG",
                {
                    "VIEWER_GROUPS": [],
                    "OPERATOR_GROUPS": ["cn=operators,ou=groups,dc=example,dc=com"],
                    "ADMIN_GROUPS": ["cn=admins,ou=groups,dc=example,dc=com"],
                },
            ):
                mock_parent.return_value = user

                result = backend.authenticate_ldap_user(ldap_user_mock, "password")

                assert result is not None
                assert result.role == "admin"

    def test_customer_assignment_by_name(self, customer_for_ldap):
        """Test customer assignment from LDAP attribute by name."""
        from webnet.core.ldap_backend import WebnetLDAPBackend

        backend = WebnetLDAPBackend()

        user = User.objects.create_user(username="customeruser", role="viewer")

        ldap_user_mock = Mock()
        ldap_user_mock.attrs = {"department": ["LDAP Test Customer"]}
        ldap_user_mock.group_dns = []

        with patch("webnet.core.ldap_backend.LDAPBackend.authenticate_ldap_user") as mock_parent:
            with patch(
                "webnet.ldap_config.LDAP_CONFIG",
                {
                    "VIEWER_GROUPS": [],
                    "OPERATOR_GROUPS": [],
                    "ADMIN_GROUPS": [],
                    "LDAP_ATTR_CUSTOMER": "department",
                },
            ):
                mock_parent.return_value = user

                result = backend.authenticate_ldap_user(ldap_user_mock, "password")

                assert result is not None
                assert result.customers.filter(id=customer_for_ldap.id).exists()

    def test_customer_assignment_by_id(self, customer_for_ldap):
        """Test customer assignment from LDAP attribute by ID."""
        from webnet.core.ldap_backend import WebnetLDAPBackend

        backend = WebnetLDAPBackend()

        user = User.objects.create_user(username="customeruser2", role="viewer")

        ldap_user_mock = Mock()
        ldap_user_mock.attrs = {"department": [str(customer_for_ldap.id)]}
        ldap_user_mock.group_dns = []

        with patch("webnet.core.ldap_backend.LDAPBackend.authenticate_ldap_user") as mock_parent:
            with patch(
                "webnet.ldap_config.LDAP_CONFIG",
                {
                    "VIEWER_GROUPS": [],
                    "OPERATOR_GROUPS": [],
                    "ADMIN_GROUPS": [],
                    "LDAP_ATTR_CUSTOMER": "department",
                },
            ):
                mock_parent.return_value = user

                result = backend.authenticate_ldap_user(ldap_user_mock, "password")

                assert result is not None
                assert result.customers.filter(id=customer_for_ldap.id).exists()

    def test_handles_missing_group_dns(self):
        """Test that backend handles missing group_dns gracefully."""
        from webnet.core.ldap_backend import WebnetLDAPBackend

        backend = WebnetLDAPBackend()

        user = User.objects.create_user(username="testuser", role="admin")

        # Create a mock that will raise AttributeError when group_dns is accessed
        ldap_user_mock = Mock(spec=["attrs"])
        ldap_user_mock.attrs = {}
        # Accessing group_dns on a spec'd mock without that attribute will raise AttributeError

        with patch("webnet.core.ldap_backend.LDAPBackend.authenticate_ldap_user") as mock_parent:
            with patch(
                "webnet.ldap_config.LDAP_CONFIG",
                {
                    "VIEWER_GROUPS": [],
                    "OPERATOR_GROUPS": [],
                    "ADMIN_GROUPS": [],
                },
            ):
                mock_parent.return_value = user

                result = backend.authenticate_ldap_user(ldap_user_mock, "password")

                assert result is not None
                assert result.role == "viewer"

    def test_auth_failure_returns_none(self):
        """Test that failed LDAP authentication returns None."""
        from webnet.core.ldap_backend import WebnetLDAPBackend

        backend = WebnetLDAPBackend()

        ldap_user_mock = Mock()

        with patch("webnet.core.ldap_backend.LDAPBackend.authenticate_ldap_user") as mock_parent:
            mock_parent.return_value = None

            result = backend.authenticate_ldap_user(ldap_user_mock, "password")

            assert result is None


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
            mock_auth.return_value = None

            User.objects.create_user(username="localuser", password="password123", role="admin")

            user = authenticate(username="localuser", password="password123")

            assert user is not None
            assert user.username == "localuser"
            assert user.role == "admin"

    def test_local_only_authentication(self):
        """Test that local authentication works without LDAP configured."""
        User.objects.create_user(username="localonlyuser", password="password123", role="operator")

        user = authenticate(username="localonlyuser", password="password123")

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
            import importlib

            from webnet import ldap_config

            importlib.reload(ldap_config)

            assert ldap_config.LDAP_ENABLED is True
            assert ldap_config.AUTH_LDAP_SERVER_URI == "ldap://test.example.com"

    def test_ldap_disabled_by_default(self):
        """Test that LDAP is disabled when LDAP_ENABLED is false."""
        with patch.dict("os.environ", {"LDAP_ENABLED": "false"}):
            import importlib

            from webnet import ldap_config

            importlib.reload(ldap_config)

            assert ldap_config.LDAP_ENABLED is False
            assert ldap_config.LDAP_CONFIG == {}
