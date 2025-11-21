"""Customer and tenant management services."""

from __future__ import annotations

import ipaddress
from typing import Sequence

from sqlalchemy.orm import Session

from app.db import Customer, CustomerIPRange, User
from app.domain.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)
from app.repositories import (
    CustomerIPRangeRepository,
    CustomerRepository,
    UserRepository,
)


class CustomerService:
    """Business logic around customers, memberships, and IP ranges."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.customers = CustomerRepository(session)
        self.ip_ranges = CustomerIPRangeRepository(session)
        self.users = UserRepository(session)

    # ------------------------------------------------------------------
    # Customers

    def create_customer(self, payload) -> Customer:
        if self.customers.get_by_name(payload.name):
            raise ConflictError("Customer with this name already exists")

        customer = Customer(**payload.model_dump())
        self.session.add(customer)
        self.session.commit()
        self.session.refresh(customer)
        return customer

    def list_customers(self, user: User) -> Sequence[Customer]:
        if user.role == "admin":
            return self.customers.list_all()
        return user.customers

    def get_customer(self, customer_id: int, user: User) -> Customer:
        customer = self.customers.get_by_id(customer_id)
        if not customer:
            raise NotFoundError("Customer not found")
        if user.role != "admin" and customer not in user.customers:
            raise ForbiddenError("Access denied")
        return customer

    # ------------------------------------------------------------------
    # Membership

    def add_user_to_customer(self, customer_id: int, user_id: int) -> None:
        customer = self._require_customer(customer_id)
        user = self._require_user(user_id)
        if user not in customer.users:
            customer.users.append(user)
            self.session.commit()

    def remove_user_from_customer(self, customer_id: int, user_id: int) -> None:
        customer = self._require_customer(customer_id)
        user = self._require_user(user_id)
        if user in customer.users:
            customer.users.remove(user)
            self.session.commit()

    # ------------------------------------------------------------------
    # IP Ranges

    def list_ip_ranges(self, customer_id: int, user: User) -> Sequence[CustomerIPRange]:
        customer = self.get_customer(customer_id, user)
        return customer.ip_ranges

    def create_ip_range(self, customer_id: int, payload) -> CustomerIPRange:
        if self.ip_ranges.get_by_cidr(payload.cidr):
            raise ConflictError(
                f"IP range {payload.cidr} is already assigned to a customer"
            )

        try:
            ipaddress.ip_network(payload.cidr)
        except ValueError:
            raise ValidationError("Invalid CIDR format")

        customer = self._require_customer(customer_id)
        ip_range = CustomerIPRange(customer_id=customer.id, **payload.model_dump())
        self.session.add(ip_range)
        self.session.commit()
        self.session.refresh(ip_range)
        return ip_range

    def delete_ip_range(self, customer_id: int, range_id: int) -> None:
        ip_range = self.ip_ranges.get_by_id_for_customer(customer_id, range_id)
        if not ip_range:
            raise NotFoundError("IP range not found")
        self.session.delete(ip_range)
        self.session.commit()

    # ------------------------------------------------------------------

    def _require_customer(self, customer_id: int) -> Customer:
        customer = self.customers.get_by_id(customer_id)
        if not customer:
            raise NotFoundError("Customer not found")
        return customer

    def _require_user(self, user_id: int) -> User:
        user = self.users.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        return user


