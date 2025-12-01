import hashlib
import secrets
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from webnet.customers.models import Customer
from webnet.users.models import APIKey

User = get_user_model()


def _create_api_key(user):
    raw = secrets.token_urlsafe(32)
    api_key = APIKey.objects.create(
        user=user,
        name="cli",
        key_prefix=raw[:8],
        key_hash=hashlib.sha256(raw.encode()).hexdigest(),
    )
    return raw, api_key


@pytest.mark.django_db
def test_api_key_auth_allows_access_to_customer_list():
    customer = Customer.objects.create(name="Acme")
    user = User.objects.create_user(username="alice", password="secret123", role="admin")
    user.customers.add(customer)
    token, _ = _create_api_key(user)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"ApiKey {token}")

    resp = client.get("/api/v1/customers/")
    assert resp.status_code == 200
    payload = resp.json()
    items = payload.get("results", payload if isinstance(payload, list) else [])
    names = [item.get("name") for item in items]
    assert "Acme" in names


@pytest.mark.django_db
def test_api_key_auth_rejects_expired_key():
    customer = Customer.objects.create(name="Acme")
    user = User.objects.create_user(username="bob", password="secret123", role="admin")
    user.customers.add(customer)
    token, api_key = _create_api_key(user)
    api_key.expires_at = timezone.now() - timedelta(minutes=1)
    api_key.save(update_fields=["expires_at"])

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"ApiKey {token}")

    resp = client.get("/api/v1/customers/")
    assert resp.status_code in {401, 403}
