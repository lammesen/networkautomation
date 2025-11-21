"""Base repository utilities."""

from __future__ import annotations

from typing import Generic, Optional, TypeVar

from sqlalchemy.orm import Session

TModel = TypeVar("TModel")


class SQLAlchemyRepository(Generic[TModel]):
    """Minimal base repository storing the SQLAlchemy session."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, instance: TModel) -> TModel:
        self.session.add(instance)
        return instance

    def remove(self, instance: TModel) -> None:
        self.session.delete(instance)

    def refresh(self, instance: TModel) -> TModel:
        self.session.refresh(instance)
        return instance

    def commit(self) -> None:
        self.session.commit()

    def flush(self) -> None:
        self.session.flush()


