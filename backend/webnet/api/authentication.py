"""Custom API key authentication using hashed secrets stored on APIKey model."""

from __future__ import annotations

import hashlib
from typing import Optional, Tuple

from django.utils import timezone
from rest_framework import authentication, exceptions

from webnet.users.models import APIKey


class APIKeyAuthentication(authentication.BaseAuthentication):
    """Authenticate requests via `Authorization: ApiKey <token>` or `X-API-Key` header."""

    keyword = "apikey"

    def authenticate(self, request) -> Optional[Tuple[object, APIKey]]:
        token = self._get_token(request)
        if not token:
            return None

        if len(token) < 16:  # pragma: no cover - cheap sanity check
            raise exceptions.AuthenticationFailed("Invalid API key")

        key_hash = hashlib.sha256(token.encode()).hexdigest()
        try:
            api_key = APIKey.objects.select_related("user").get(key_hash=key_hash, is_active=True)
        except APIKey.DoesNotExist:
            raise exceptions.AuthenticationFailed("Invalid API key")

        if api_key.expires_at and api_key.expires_at <= timezone.now():
            raise exceptions.AuthenticationFailed("API key expired")

        user = api_key.user
        if not user or not user.is_active:
            raise exceptions.AuthenticationFailed("User inactive")

        APIKey.objects.filter(pk=api_key.pk).update(last_used_at=timezone.now())
        return user, api_key

    def _get_token(self, request) -> Optional[str]:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.lower().startswith(f"{self.keyword} "):
            return auth_header.split(" ", 1)[1].strip()

        key_header = request.headers.get("X-API-Key")
        if key_header:
            return key_header.strip()
        return None
