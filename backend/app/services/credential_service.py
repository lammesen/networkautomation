"""Credential service layer."""

from __future__ import annotations

from typing import Sequence

from sqlalchemy.orm import Session

from app.db import Credential
from app.domain.context import TenantRequestContext
from app.domain.exceptions import ConflictError, NotFoundError
from app.repositories import CredentialRepository


class CredentialService:
    """Business logic for credential CRUD operations."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.credentials = CredentialRepository(session)

    def list_credentials(self, context: TenantRequestContext) -> Sequence[Credential]:
        return self.credentials.list_for_customer(context.customer_id)

    def get_credential(
        self,
        credential_id: int,
        context: TenantRequestContext,
    ) -> Credential:
        credential = self.credentials.get_by_id_for_customer(
            credential_id,
            context.customer_id,
        )
        if not credential:
            raise NotFoundError("Credential not found")
        return credential

    def create_credential(
        self,
        payload,
        context: TenantRequestContext,
    ) -> Credential:
        existing = self.credentials.get_by_name_for_customer(
            payload.name,
            context.customer_id,
        )
        if existing:
            raise ConflictError("Credential with this name already exists for the customer")

        credential = Credential(
            **payload.model_dump(),
            customer_id=context.customer_id,
        )

        self.session.add(credential)
        self.session.commit()
        self.session.refresh(credential)
        return credential

    def update_credential(
        self,
        credential_id: int,
        payload,
        context: TenantRequestContext,
    ) -> Credential:
        credential = self.get_credential(credential_id, context)

        update_data = payload.model_dump(exclude_unset=True)

        if "name" in update_data and update_data["name"] != credential.name:
            existing = self.credentials.get_by_name_for_customer(
                update_data["name"],
                context.customer_id,
            )
            if existing:
                raise ConflictError("Credential with this name already exists for the customer")

        for field, value in update_data.items():
            setattr(credential, field, value)

        self.session.commit()
        self.session.refresh(credential)
        return credential

    def delete_credential(
        self,
        credential_id: int,
        context: TenantRequestContext,
    ) -> None:
        credential = self.get_credential(credential_id, context)
        self.session.delete(credential)
        self.session.commit()
