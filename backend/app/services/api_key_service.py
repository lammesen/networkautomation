"""API Key service for managing API keys."""

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy.orm import Session

from app.db import APIKey, User
from app.domain.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.repositories.api_key_repository import APIKeyRepository


class APIKeyService:
    """Service for API key management operations."""

    # API key format: na_<random 32 chars>
    KEY_PREFIX = "na_"
    KEY_LENGTH = 32

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = APIKeyRepository(session)

    @staticmethod
    def generate_key() -> str:
        """Generate a new random API key.

        Returns:
            A new API key in format: na_<32 random chars>
        """
        random_part = secrets.token_urlsafe(APIKeyService.KEY_LENGTH)[: APIKeyService.KEY_LENGTH]
        return f"{APIKeyService.KEY_PREFIX}{random_part}"

    @staticmethod
    def hash_key(key: str) -> str:
        """Hash an API key for storage.

        Args:
            key: The plain API key.

        Returns:
            SHA-256 hash of the key.
        """
        return hashlib.sha256(key.encode()).hexdigest()

    @staticmethod
    def get_prefix(key: str) -> str:
        """Get the display prefix of an API key.

        Args:
            key: The plain API key.

        Returns:
            First 8 characters for display (e.g., "na_abc12")
        """
        return key[:8]

    def create_api_key(
        self,
        user: User,
        name: str,
        expires_at: Optional[datetime] = None,
        scopes: Optional[dict] = None,
    ) -> tuple[APIKey, str]:
        """Create a new API key for a user.

        Args:
            user: The user to create the key for.
            name: A descriptive name for the key.
            expires_at: Optional expiration datetime.
            scopes: Optional scope restrictions.

        Returns:
            Tuple of (APIKey model, plain key string).
            The plain key is only available at creation time.
        """
        if not name or len(name.strip()) == 0:
            raise ValidationError("API key name is required")

        if len(name) > 100:
            raise ValidationError("API key name must be 100 characters or less")

        # Generate the key
        plain_key = self.generate_key()
        key_hash = self.hash_key(plain_key)
        key_prefix = self.get_prefix(plain_key)

        # Create the API key record
        api_key = APIKey(
            user_id=user.id,
            name=name.strip(),
            key_prefix=key_prefix,
            key_hash=key_hash,
            expires_at=expires_at,
            scopes=scopes,
            is_active=True,
        )

        self.repo.create(api_key)

        # Return both the model and the plain key
        # The plain key is only available now!
        return api_key, plain_key

    def get_api_key(self, key_id: int, user: User) -> APIKey:
        """Get an API key by ID, verifying ownership.

        Args:
            key_id: The API key ID.
            user: The requesting user.

        Returns:
            The API key.

        Raises:
            NotFoundError: If key not found.
            ForbiddenError: If user doesn't own the key.
        """
        api_key = self.repo.get_by_id(key_id)
        if not api_key:
            raise NotFoundError("API key not found")

        if api_key.user_id != user.id and user.role != "admin":
            raise ForbiddenError("Access denied to this API key")

        return api_key

    def list_user_api_keys(self, user: User) -> Sequence[APIKey]:
        """List all API keys for a user.

        Args:
            user: The user.

        Returns:
            List of API keys.
        """
        return self.repo.list_by_user(user.id)

    def validate_api_key(self, plain_key: str) -> Optional[tuple[APIKey, User]]:
        """Validate an API key and return the associated key and user.

        Args:
            plain_key: The plain API key.

        Returns:
            Tuple of (APIKey, User) if valid, None otherwise.
        """
        if not plain_key or not plain_key.startswith(self.KEY_PREFIX):
            return None

        key_hash = self.hash_key(plain_key)
        api_key = self.repo.get_by_hash(key_hash)

        if not api_key:
            return None

        # Check if active
        if not api_key.is_active:
            return None

        # Check expiration
        if api_key.expires_at:
            # Handle both naive and aware datetimes
            expires_at = api_key.expires_at
            now = datetime.now(timezone.utc)
            if expires_at.tzinfo is None:
                # Naive datetime - assume UTC
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at < now:
                return None

        # Check if user is active
        if not api_key.user.is_active:
            return None

        # Update last used timestamp
        self.repo.update_last_used(api_key)

        return api_key, api_key.user

    def revoke_api_key(self, key_id: int, user: User) -> None:
        """Revoke (deactivate) an API key.

        Args:
            key_id: The API key ID.
            user: The requesting user.

        Raises:
            NotFoundError: If key not found.
            ForbiddenError: If user doesn't own the key.
        """
        api_key = self.get_api_key(key_id, user)
        self.repo.deactivate(api_key)

    def delete_api_key(self, key_id: int, user: User) -> None:
        """Permanently delete an API key.

        Args:
            key_id: The API key ID.
            user: The requesting user.

        Raises:
            NotFoundError: If key not found.
            ForbiddenError: If user doesn't own the key.
        """
        api_key = self.get_api_key(key_id, user)
        self.repo.delete(api_key)
