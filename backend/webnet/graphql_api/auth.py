"""Authentication for GraphQL API using JWT and API Key."""

from __future__ import annotations

from typing import Optional
import hashlib

from django.utils import timezone
from strawberry.types import Info
from strawberry.permission import BasePermission

from webnet.users.models import APIKey, User


class IsAuthenticated(BasePermission):
    """Permission class for GraphQL queries requiring authentication."""

    message = "User is not authenticated"

    def has_permission(self, source, info: Info, **kwargs) -> bool:
        """Check if the user is authenticated via JWT or API key."""
        request = (
            info.context.get("request") if isinstance(info.context, dict) else info.context.request
        )
        return request and request.user and request.user.is_authenticated


def get_user_from_request(request) -> Optional[User]:
    """Authenticate user from JWT token or API key in request.

    This supports:
    - JWT token from Authorization: Bearer <token>
    - API key from Authorization: ApiKey <key> or X-API-Key header
    """
    # Try JWT authentication first
    auth_header = request.headers.get("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        from rest_framework_simplejwt.authentication import JWTAuthentication

        jwt_auth = JWTAuthentication()
        try:
            validated_token = jwt_auth.get_validated_token(auth_header.split(" ", 1)[1])
            user = jwt_auth.get_user(validated_token)
            if user and user.is_active:
                return user
        except Exception:
            pass  # Fall through to API key authentication

    # Check for API key authentication
    api_key_token = None

    if auth_header.lower().startswith("apikey "):
        api_key_token = auth_header.split(" ", 1)[1].strip()
    elif "X-API-Key" in request.headers:
        api_key_token = request.headers.get("X-API-Key", "").strip()

    if api_key_token and len(api_key_token) >= 16:
        key_hash = hashlib.sha256(api_key_token.encode()).hexdigest()
        try:
            api_key = APIKey.objects.select_related("user").get(key_hash=key_hash, is_active=True)

            # Check expiration
            if api_key.expires_at and api_key.expires_at <= timezone.now():
                return None

            # Check user
            if api_key.user and api_key.user.is_active:
                # Update last used timestamp
                APIKey.objects.filter(pk=api_key.pk).update(last_used_at=timezone.now())
                return api_key.user
        except APIKey.DoesNotExist:
            # API key not found: authentication fails silently (return None below)
            pass

    return None
