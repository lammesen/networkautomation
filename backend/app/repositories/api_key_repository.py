"""API Key repository for database operations."""

from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy.orm import Session

from app.db.models import APIKey


class APIKeyRepository:
    """Repository for API key database operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, api_key: APIKey) -> APIKey:
        """Create a new API key."""
        self.session.add(api_key)
        self.session.commit()
        self.session.refresh(api_key)
        return api_key

    def get_by_id(self, key_id: int) -> Optional[APIKey]:
        """Get API key by ID."""
        return self.session.query(APIKey).filter(APIKey.id == key_id).first()

    def get_by_hash(self, key_hash: str) -> Optional[APIKey]:
        """Get API key by hash."""
        return self.session.query(APIKey).filter(APIKey.key_hash == key_hash).first()

    def list_by_user(self, user_id: int) -> Sequence[APIKey]:
        """List all API keys for a user."""
        return (
            self.session.query(APIKey)
            .filter(APIKey.user_id == user_id)
            .order_by(APIKey.created_at.desc())
            .all()
        )

    def update_last_used(self, api_key: APIKey) -> None:
        """Update the last_used_at timestamp."""
        api_key.last_used_at = datetime.utcnow()
        self.session.commit()

    def deactivate(self, api_key: APIKey) -> None:
        """Deactivate an API key."""
        api_key.is_active = False
        self.session.commit()

    def delete(self, api_key: APIKey) -> None:
        """Delete an API key."""
        self.session.delete(api_key)
        self.session.commit()
