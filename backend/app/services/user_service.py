"""User administration services."""

from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy.orm import Session

from app.db import User
from app.domain.exceptions import ForbiddenError, NotFoundError
from app.repositories.user_repository import UserRepository


class UserService:
    """Admin-only user management operations."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.users = UserRepository(session)

    def list_users(self, active: Optional[bool]) -> Sequence[User]:
        query = self.session.query(User)
        if active is not None:
            query = query.filter(User.is_active == active)
        return query.order_by(User.username.asc()).all()

    def update_user(self, user_id: int, payload, acting_admin: User) -> User:
        user = self.users.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")

        update_data = payload.model_dump(exclude_unset=True)
        if "is_active" in update_data and not update_data["is_active"]:
            if acting_admin.id == user_id:
                raise ForbiddenError("Admins cannot deactivate their own account")

        for field, value in update_data.items():
            setattr(user, field, value)

        self.session.commit()
        self.session.refresh(user)
        return user


