import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from webnet.customers.models import Customer
from webnet.jobs.models import Job, JobLog

User = get_user_model()


@pytest.mark.django_db
def test_job_logs_api_requires_auth_and_lists_logs():
    customer = Customer.objects.create(name="Acme")
    user = User.objects.create_user(username="eva", password="secret123", role="admin")
    user.customers.add(customer)
    job = Job.objects.create(type="run_commands", status="success", user=user, customer=customer)
    JobLog.objects.create(job=job, level="INFO", message="hello api")

    client = APIClient()
    # unauthenticated should 401
    resp = client.get(f"/api/v1/jobs/{job.id}/logs")
    assert resp.status_code in {401, 403}

    client.login(username="eva", password="secret123")
    resp = client.get(f"/api/v1/jobs/{job.id}/logs")
    assert resp.status_code == 200
    assert any("hello api" in str(item.get("message")) for item in resp.json())


@pytest.mark.django_db
def test_job_logs_api_respects_customer_scope():
    customer_a = Customer.objects.create(name="Acme")
    customer_b = Customer.objects.create(name="Beta")
    admin = User.objects.create_user(username="admin", password="secret123", role="admin")
    user_b = User.objects.create_user(username="bob", password="secret123", role="operator")
    admin.customers.add(customer_a)
    user_b.customers.add(customer_b)

    job = Job.objects.create(type="run_commands", status="success", user=admin, customer=customer_a)
    JobLog.objects.create(job=job, level="INFO", message="secret logs")

    client = APIClient()
    client.login(username="bob", password="secret123")

    resp = client.get(f"/api/v1/jobs/{job.id}/logs")
    assert resp.status_code in {403, 404}
