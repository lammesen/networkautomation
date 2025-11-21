"""User persistence helpers."""

from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy.orm import Session

from app.db import User
from app.repositories.base import SQLAlchemyRepository


class UserRepository(SQLAlchemyRepository[User]):
    """Encapsulates user-related queries."""

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.session.query(User).filter(User.id == user_id).first()

    def list_all(self) -> Sequence[User]:
        return self.session.query(User).order_by(User.username.asc()).all()


