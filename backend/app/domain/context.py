"""Request-scoped context helpers for multi-tenant operations."""

from dataclasses import dataclass
from typing import Optional, Sequence

from app.db import Customer, User
from app.domain.exceptions import ForbiddenError


@dataclass(slots=True)
class TenantRequestContext:
    """Wraps the authenticated user and active customer for service-layer use."""

    user: User
    customer: Customer

    @property
    def customer_id(self) -> int:
        return self.customer.id

    @property
    def is_admin(self) -> bool:
        return self.user.role == "admin"

    def assert_customer_access(self, target_customer_id: int) -> None:
        """Ensure the user may operate on the requested customer."""
        if not self.is_admin and target_customer_id != self.customer_id:
            raise ForbiddenError("IP range restriction: customer scope mismatch")


@dataclass(slots=True)
class MultiTenantContext:
    """Context that supports viewing resources across multiple customers.

    When customer is None, the user can view resources from all their assigned customers.
    When customer is set, it behaves like a single-tenant context.
    """

    user: User
    customer: Optional[Customer] = None

    @property
    def customer_id(self) -> Optional[int]:
        return self.customer.id if self.customer else None

    @property
    def customer_ids(self) -> Sequence[int]:
        """Returns all customer IDs the user has access to."""
        if self.customer:
            return [self.customer.id]
        return [c.id for c in self.user.customers]

    @property
    def is_admin(self) -> bool:
        return self.user.role == "admin"

    @property
    def is_single_customer(self) -> bool:
        """True if a specific customer is selected."""
        return self.customer is not None

    def assert_customer_access(self, target_customer_id: int) -> None:
        """Ensure the user may operate on the requested customer."""
        if self.is_admin:
            return
        if target_customer_id not in self.customer_ids:
            raise ForbiddenError("Access denied: customer scope mismatch")
