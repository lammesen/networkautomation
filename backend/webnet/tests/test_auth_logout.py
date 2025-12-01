import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.mark.django_db
def test_logout_get_allows_and_redirects():
    User.objects.create_user(username="alice", password="secret123", role="admin")
    client = APIClient()
    client.login(username="alice", password="secret123")

    resp = client.get("/logout/")
    assert resp.status_code in (200, 302)
