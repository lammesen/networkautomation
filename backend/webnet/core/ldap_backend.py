"""Custom LDAP authentication backend with role mapping."""

from __future__ import annotations

import logging

from django.contrib.auth import get_user_model
from django_auth_ldap.backend import LDAPBackend

logger = logging.getLogger(__name__)

User = get_user_model()


class WebnetLDAPBackend(LDAPBackend):
    """Custom LDAP backend that maps LDAP groups to webnet roles."""

    def authenticate_ldap_user(self, ldap_user, password):
        """Authenticate and update user with role based on LDAP groups."""
        user = super().authenticate_ldap_user(ldap_user, password)
        if user is None:
            return None

        # Import LDAP_CONFIG here to avoid circular import issues
        # (webnet.settings imports this module, which would import ldap_config)
        from webnet.ldap_config import LDAP_CONFIG

        # Get user's LDAP group DNs - safely handle missing group configuration
        try:
            user_groups = ldap_user.group_dns
        except (AttributeError, KeyError):
            # If group queries fail or aren't configured, use empty list
            user_groups = []

        # Determine role based on group membership
        # Priority: admin > operator > viewer
        role = "viewer"  # Default role

        operator_groups = LDAP_CONFIG.get("OPERATOR_GROUPS", [])
        admin_groups = LDAP_CONFIG.get("ADMIN_GROUPS", [])

        # Check group membership
        for group_dn in user_groups:
            if group_dn in admin_groups:
                role = "admin"
                break  # Admin is highest priority
            elif group_dn in operator_groups:
                role = "operator"  # May be overridden by admin

        # Update user role if changed
        if user.role != role:
            logger.info(f"Updating user {user.username} role from {user.role} to {role}")
            user.role = role
            user.save(update_fields=["role"])

        # Handle customer assignment from LDAP attribute
        customer_attr = LDAP_CONFIG.get("LDAP_ATTR_CUSTOMER", "")
        if customer_attr:
            try:
                # Get customer ID or name from LDAP attribute
                customer_value = ldap_user.attrs.get(customer_attr)
                if customer_value and len(customer_value) > 0:
                    customer_identifier = customer_value[0]
                    self._assign_customer(user, customer_identifier)
            except (KeyError, IndexError, AttributeError) as e:
                logger.warning(f"Failed to assign customer from LDAP: {e}")

        return user

    def _assign_customer(self, user, customer_identifier: str) -> None:
        """Assign user to customer based on identifier from LDAP."""
        from webnet.customers.models import Customer

        try:
            # Try to find customer by ID or name
            try:
                customer_id = int(customer_identifier)
                customer = Customer.objects.get(id=customer_id)
            except (ValueError, Customer.DoesNotExist):
                # Try by name
                customer = Customer.objects.get(name=customer_identifier)

            # Add customer if not already assigned
            if not user.customers.filter(id=customer.id).exists():
                user.customers.add(customer)
                logger.info(f"Assigned user {user.username} to customer {customer.name}")
        except Customer.DoesNotExist:
            logger.warning(f"Customer '{customer_identifier}' not found for user {user.username}")
