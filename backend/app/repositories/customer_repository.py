"""Customer persistence helpers."""

from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy.orm import Session

from app.db import Customer, CustomerIPRange
from app.repositories.base import SQLAlchemyRepository


class CustomerRepository(SQLAlchemyRepository[Customer]):
    """Customer data access."""

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def get_by_id(self, customer_id: int) -> Optional[Customer]:
        return self.session.query(Customer).filter(Customer.id == customer_id).first()

    def list_all(self) -> Sequence[Customer]:
        return self.session.query(Customer).order_by(Customer.name.asc()).all()

    def get_by_name(self, name: str) -> Optional[Customer]:
        return self.session.query(Customer).filter(Customer.name == name).first()


class CustomerIPRangeRepository(SQLAlchemyRepository[CustomerIPRange]):
    """Customer IP range data access."""

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def list_all(self) -> Sequence[CustomerIPRange]:
        return self.session.query(CustomerIPRange).all()

    def list_for_customer(self, customer_id: int) -> Sequence[CustomerIPRange]:
        return (
            self.session.query(CustomerIPRange)
            .filter(CustomerIPRange.customer_id == customer_id)
            .all()
        )

    def get_by_cidr(self, cidr: str) -> Optional[CustomerIPRange]:
        return (
            self.session.query(CustomerIPRange)
            .filter(CustomerIPRange.cidr == cidr)
            .first()
        )

    def get_by_id_for_customer(
        self, customer_id: int, range_id: int
    ) -> Optional[CustomerIPRange]:
        return (
            self.session.query(CustomerIPRange)
            .filter(
                CustomerIPRange.id == range_id,
                CustomerIPRange.customer_id == customer_id,
            )
            .first()
        )


