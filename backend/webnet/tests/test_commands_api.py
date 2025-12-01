import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from unittest.mock import patch

from webnet.customers.models import Customer

User = get_user_model()


@pytest.mark.django_db
def test_commands_run_requires_non_viewer(monkeypatch):
    customer = Customer.objects.create(name="Acme")
    admin = User.objects.create_user(username="alice", password="secret123", role="admin")
    admin.customers.add(customer)
    viewer = User.objects.create_user(username="victor", password="secret123", role="viewer")
    viewer.customers.add(customer)

    # Avoid Celery dispatch
    with patch("webnet.jobs.services.JobService._enqueue", return_value=None):
        client = APIClient()
        client.login(username="alice", password="secret123")
        resp = client.post(
            "/api/v1/commands/run",
            {"targets": {"site": "lab"}, "commands": ["show version"], "customer_id": customer.id},
            format="json",
        )
        assert resp.status_code == 202
        assert "job_id" in resp.data

        client.logout()
        client.login(username="victor", password="secret123")
        resp2 = client.post(
            "/api/v1/commands/run",
            {"targets": {"site": "lab"}, "commands": ["show version"], "customer_id": customer.id},
            format="json",
        )
        assert resp2.status_code == 403
