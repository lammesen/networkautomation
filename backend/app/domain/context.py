"""Request-scoped context helpers for multi-tenant operations."""

from dataclasses import dataclass

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


