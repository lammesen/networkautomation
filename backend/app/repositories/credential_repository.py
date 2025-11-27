"""Credential persistence helpers."""

from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy.orm import Session

from app.db import Credential
from app.repositories.base import SQLAlchemyRepository


class CredentialRepository(SQLAlchemyRepository[Credential]):
    """Encapsulates credential access patterns."""

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def list_for_customer(self, customer_id: int) -> Sequence[Credential]:
        return (
            self.session.query(Credential)
            .filter(Credential.customer_id == customer_id)
            .order_by(Credential.name.asc())
            .all()
        )

    def list_for_customers(self, customer_ids: Sequence[int]) -> Sequence[Credential]:
        """List credentials for multiple customers."""
        return (
            self.session.query(Credential)
            .filter(Credential.customer_id.in_(customer_ids))
            .order_by(Credential.name.asc())
            .all()
        )

    def get_by_id_for_customer(self, credential_id: int, customer_id: int) -> Optional[Credential]:
        return (
            self.session.query(Credential)
            .filter(
                Credential.id == credential_id,
                Credential.customer_id == customer_id,
            )
            .first()
        )

    def get_by_id_for_customers(
        self, credential_id: int, customer_ids: Sequence[int]
    ) -> Optional[Credential]:
        """Get a credential if it belongs to any of the specified customers."""
        return (
            self.session.query(Credential)
            .filter(
                Credential.id == credential_id,
                Credential.customer_id.in_(customer_ids),
            )
            .first()
        )

    def get_by_name_for_customer(self, name: str, customer_id: int) -> Optional[Credential]:
        return (
            self.session.query(Credential)
            .filter(
                Credential.name == name,
                Credential.customer_id == customer_id,
            )
            .first()
        )
