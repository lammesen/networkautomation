import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.mark.django_db
def test_login_and_refresh():
    User.objects.create_user(username="alice", password="secret123", role="admin")
    client = APIClient()

    resp = client.post(
        "/api/v1/auth/login",
        {"username": "alice", "password": "secret123"},
        format="json",
    )
    assert resp.status_code == 200
    access = resp.data.get("access")
    refresh = resp.data.get("refresh")
    assert access
    assert refresh

    resp_refresh = client.post("/api/v1/auth/refresh", {"refresh": refresh}, format="json")
    assert resp_refresh.status_code == 200
    assert resp_refresh.data.get("access")
