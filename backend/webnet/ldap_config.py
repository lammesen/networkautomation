"""LDAP/Active Directory authentication configuration."""

from __future__ import annotations

import logging
import os

import ldap
from django_auth_ldap.config import (
    ActiveDirectoryGroupType,
    GroupOfNamesType,
    LDAPSearch,
)

logger = logging.getLogger("django_auth_ldap")


def env(key: str, default: str | None = None) -> str:
    """Get environment variable value."""
    val = os.getenv(key, default)
    return "" if val is None else str(val)


def env_bool(key: str, default: bool = False) -> bool:
    """Get boolean environment variable value."""
    return env(key, str(default)).lower() in ("true", "1", "yes")


# Enable LDAP authentication
LDAP_ENABLED = env_bool("LDAP_ENABLED", False)

if LDAP_ENABLED:
    # LDAP Server Configuration
    AUTH_LDAP_SERVER_URI = env("LDAP_SERVER_URI", "")
    if not AUTH_LDAP_SERVER_URI:
        raise ValueError("LDAP_SERVER_URI is required when LDAP_ENABLED=true")

    # Connection Options
    AUTH_LDAP_CONNECTION_OPTIONS = {
        ldap.OPT_DEBUG_LEVEL: int(env("LDAP_DEBUG_LEVEL", "0")),
        ldap.OPT_REFERRALS: 0,  # Disable referrals for better AD compatibility
    }

    # TLS/SSL Configuration
    if env_bool("LDAP_START_TLS", False):
        AUTH_LDAP_START_TLS = True

    # Certificate validation
    if env_bool("LDAP_IGNORE_CERT_ERRORS", False):
        AUTH_LDAP_CONNECTION_OPTIONS[ldap.OPT_X_TLS_REQUIRE_CERT] = ldap.OPT_X_TLS_NEVER
    else:
        AUTH_LDAP_CONNECTION_OPTIONS[ldap.OPT_X_TLS_REQUIRE_CERT] = ldap.OPT_X_TLS_DEMAND

    # Bind credentials
    AUTH_LDAP_BIND_DN = env("LDAP_BIND_DN", "")
    AUTH_LDAP_BIND_PASSWORD = env("LDAP_BIND_PASSWORD", "")

    # User search configuration
    AUTH_LDAP_USER_SEARCH_BASE = env("LDAP_USER_SEARCH_BASE", "")
    AUTH_LDAP_USER_SEARCH_FILTER = env(
        "LDAP_USER_SEARCH_FILTER", "(sAMAccountName=%(user)s)"
    )  # Default for AD
    AUTH_LDAP_USER_SEARCH_SCOPE = env("LDAP_USER_SEARCH_SCOPE", "SUBTREE")

    if not AUTH_LDAP_USER_SEARCH_BASE:
        raise ValueError("LDAP_USER_SEARCH_BASE is required when LDAP_ENABLED=true")

    # Map search scope string to ldap constant
    SCOPE_MAP = {
        "BASE": ldap.SCOPE_BASE,
        "ONELEVEL": ldap.SCOPE_ONELEVEL,
        "SUBTREE": ldap.SCOPE_SUBTREE,
    }
    search_scope = SCOPE_MAP.get(AUTH_LDAP_USER_SEARCH_SCOPE.upper(), ldap.SCOPE_SUBTREE)

    AUTH_LDAP_USER_SEARCH = LDAPSearch(
        AUTH_LDAP_USER_SEARCH_BASE,
        search_scope,
        AUTH_LDAP_USER_SEARCH_FILTER,
    )

    # User DN template (alternative to search)
    ldap_user_dn_template = env("LDAP_USER_DN_TEMPLATE", "")
    if ldap_user_dn_template:
        AUTH_LDAP_USER_DN_TEMPLATE = ldap_user_dn_template

    # User attribute mapping
    AUTH_LDAP_USER_ATTR_MAP = {
        "first_name": env("LDAP_ATTR_FIRST_NAME", "givenName"),
        "last_name": env("LDAP_ATTR_LAST_NAME", "sn"),
        "email": env("LDAP_ATTR_EMAIL", "mail"),
    }

    # User flags
    AUTH_LDAP_USER_FLAGS_BY_GROUP = {}

    # Configure staff and superuser flags based on groups
    admin_group_dn = env("LDAP_GROUP_ADMIN", "")
    if admin_group_dn:
        AUTH_LDAP_USER_FLAGS_BY_GROUP["is_staff"] = admin_group_dn
        AUTH_LDAP_USER_FLAGS_BY_GROUP["is_superuser"] = admin_group_dn

    # Group search configuration
    AUTH_LDAP_GROUP_SEARCH_BASE = env("LDAP_GROUP_SEARCH_BASE", "")
    if AUTH_LDAP_GROUP_SEARCH_BASE:
        # Determine group type (Active Directory vs OpenLDAP)
        group_type_str = env("LDAP_GROUP_TYPE", "ActiveDirectory")
        if group_type_str.lower() == "activedirectory":
            AUTH_LDAP_GROUP_TYPE = ActiveDirectoryGroupType(name_attr="cn")
        else:
            AUTH_LDAP_GROUP_TYPE = GroupOfNamesType(name_attr="cn")

        AUTH_LDAP_GROUP_SEARCH = LDAPSearch(
            AUTH_LDAP_GROUP_SEARCH_BASE,
            ldap.SCOPE_SUBTREE,
            env("LDAP_GROUP_SEARCH_FILTER", "(objectClass=group)"),
        )

        # Support nested groups for Active Directory
        if group_type_str.lower() == "activedirectory":
            AUTH_LDAP_FIND_GROUP_PERMS = True

    # Role mapping based on LDAP groups
    # Map LDAP group DNs to webnet roles
    viewer_groups = env("LDAP_GROUP_VIEWER", "").split(";") if env("LDAP_GROUP_VIEWER") else []
    operator_groups = (
        env("LDAP_GROUP_OPERATOR", "").split(";") if env("LDAP_GROUP_OPERATOR") else []
    )
    admin_groups = env("LDAP_GROUP_ADMIN", "").split(";") if env("LDAP_GROUP_ADMIN") else []

    # Remove empty strings from group lists
    viewer_groups = [g for g in viewer_groups if g]
    operator_groups = [g for g in operator_groups if g]
    admin_groups = [g for g in admin_groups if g]

    # Mirror groups to Django groups for permission handling
    AUTH_LDAP_MIRROR_GROUPS = True

    # Always update user attributes from LDAP on each login
    AUTH_LDAP_ALWAYS_UPDATE_USER = env_bool("LDAP_ALWAYS_UPDATE_USER", True)

    # Allow LDAP authentication to create new users
    AUTH_LDAP_USER_CREATE = env_bool("LDAP_USER_CREATE", True)

    # Cache groups for performance
    AUTH_LDAP_CACHE_TIMEOUT = int(env("LDAP_CACHE_TIMEOUT", "3600"))

    # Export configuration for use in settings.py
    LDAP_CONFIG = {
        "AUTH_LDAP_SERVER_URI": AUTH_LDAP_SERVER_URI,
        "AUTH_LDAP_CONNECTION_OPTIONS": AUTH_LDAP_CONNECTION_OPTIONS,
        "AUTH_LDAP_BIND_DN": AUTH_LDAP_BIND_DN,
        "AUTH_LDAP_BIND_PASSWORD": AUTH_LDAP_BIND_PASSWORD,
        "AUTH_LDAP_USER_SEARCH": AUTH_LDAP_USER_SEARCH,
        "AUTH_LDAP_USER_ATTR_MAP": AUTH_LDAP_USER_ATTR_MAP,
        "AUTH_LDAP_USER_FLAGS_BY_GROUP": AUTH_LDAP_USER_FLAGS_BY_GROUP,
        "AUTH_LDAP_ALWAYS_UPDATE_USER": AUTH_LDAP_ALWAYS_UPDATE_USER,
        "AUTH_LDAP_USER_CREATE": AUTH_LDAP_USER_CREATE,
        "AUTH_LDAP_CACHE_TIMEOUT": AUTH_LDAP_CACHE_TIMEOUT,
        "VIEWER_GROUPS": viewer_groups,
        "OPERATOR_GROUPS": operator_groups,
        "ADMIN_GROUPS": admin_groups,
    }

    # Add optional configurations
    if ldap_user_dn_template:
        LDAP_CONFIG["AUTH_LDAP_USER_DN_TEMPLATE"] = ldap_user_dn_template

    if AUTH_LDAP_GROUP_SEARCH_BASE:
        LDAP_CONFIG["AUTH_LDAP_GROUP_SEARCH"] = AUTH_LDAP_GROUP_SEARCH
        LDAP_CONFIG["AUTH_LDAP_GROUP_TYPE"] = AUTH_LDAP_GROUP_TYPE
        LDAP_CONFIG["AUTH_LDAP_MIRROR_GROUPS"] = AUTH_LDAP_MIRROR_GROUPS
        LDAP_CONFIG["AUTH_LDAP_FIND_GROUP_PERMS"] = env_bool("LDAP_FIND_GROUP_PERMS", True)

    if env_bool("LDAP_START_TLS", False):
        LDAP_CONFIG["AUTH_LDAP_START_TLS"] = True

else:
    # LDAP is disabled
    LDAP_CONFIG = {}
