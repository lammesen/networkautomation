"""Authentication for GraphQL API using JWT and API Key."""

from __future__ import annotations

import hashlib
import logging
from typing import Optional

from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError
from strawberry.types import Info
from strawberry.permission import BasePermission

from webnet.users.models import APIKey, User

logger = logging.getLogger(__name__)


class IsAuthenticated(BasePermission):
    """Permission class for GraphQL queries requiring authentication."""

    message = "User is not authenticated"

    def has_permission(self, source, info: Info, **kwargs) -> bool:
        """Check if the user is authenticated via JWT or API key."""
        request = info.context.request
        return request.user and request.user.is_authenticated


def get_user_from_request(request) -> Optional[User]:
    """Authenticate user from JWT token or API key in request.

    This supports:
    - JWT token from Authorization: Bearer <token>
    - API key from Authorization: ApiKey <key> or X-API-Key header
    - Session authentication (if user is already authenticated)
    """
    # Check for session authentication (already authenticated)
    if hasattr(request, "user") and request.user and request.user.is_authenticated:
        return request.user

    auth_header = request.headers.get("Authorization", "")

    # Check for JWT Bearer token authentication
    if auth_header.lower().startswith("bearer "):
        jwt_token = auth_header.split(" ", 1)[1].strip()
        try:
            access_token = AccessToken(jwt_token)
            user_id = access_token.get("user_id")
            if user_id:
                user = User.objects.filter(pk=user_id, is_active=True).first()
                if user:
                    return user
        except TokenError as e:
            logger.debug(f"JWT token validation failed: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error validating JWT token: {e}")
        return None

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
            pass

    return None
