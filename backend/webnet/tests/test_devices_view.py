import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from webnet.customers.models import Customer
from webnet.devices.models import Credential, Device
from webnet.users.models import User
from webnet.jobs.models import Job, JobLog


@pytest.mark.django_db
def test_devices_htmx_list_renders():
    customer = Customer.objects.create(name="Acme")
    user = User.objects.create_user(username="bob", password="secret123", role="admin")
    user.customers.add(customer)
    cred = Credential.objects.create(customer=customer, name="lab", username="u1")
    cred.password = "pass"
    cred.save()
    Device.objects.create(
        customer=customer,
        hostname="router1",
        mgmt_ip="192.0.2.1",
        vendor="cisco",
        platform="ios",
        credential=cred,
    )

    client = APIClient()
    client.login(username="bob", password="secret123")
    url = reverse("devices-list")
    resp = client.get(url, HTTP_HX_REQUEST="true")
    assert resp.status_code == 200
    assert "router1" in resp.content.decode()


@pytest.mark.django_db
def test_jobs_htmx_list_and_logs():
    customer = Customer.objects.create(name="Acme")
    user = User.objects.create_user(username="bob", password="secret123", role="admin")
    user.customers.add(customer)
    job = Job.objects.create(type="run_commands", status="success", user=user, customer=customer)
    JobLog.objects.create(job=job, level="INFO", message="hello")
    client = APIClient()
    client.login(username="bob", password="secret123")
    url = reverse("jobs-list")
    resp = client.get(url, HTTP_HX_REQUEST="true")
    assert resp.status_code == 200
    assert f"#{job.id}" in resp.content.decode()
    logs_resp = client.get(reverse("jobs-logs", args=[job.id]), HTTP_HX_REQUEST="true")
    assert logs_resp.status_code == 200
    assert "hello" in logs_resp.content.decode()
