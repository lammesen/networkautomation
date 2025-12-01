import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from rest_framework.test import APIClient

from webnet.customers.models import Customer
from webnet.devices.models import Credential, Device
from webnet.jobs.models import Job

User = get_user_model()


def _make_credential(customer: Customer, name: str = "lab") -> Credential:
    cred = Credential(customer=customer, name=name, username="netops")
    cred.password = "password123"
    cred.enable_password = "enable123"
    cred.save()
    return cred


@pytest.mark.django_db
def test_viewer_is_read_only_for_devices():
    customer = Customer.objects.create(name="Acme")
    cred = _make_credential(customer)
    viewer = User.objects.create_user(username="viewer", password="secret123", role="viewer")
    viewer.customers.add(customer)

    client = APIClient()
    client.login(username="viewer", password="secret123")

    resp = client.post(
        "/api/v1/devices/",
        {
            "customer": customer.id,
            "hostname": "r1",
            "mgmt_ip": "192.0.2.10",
            "vendor": "cisco",
            "platform": "ios",
            "credential": cred.id,
        },
        format="json",
    )

    assert resp.status_code == 403


@pytest.mark.django_db
def test_operator_sees_only_assigned_customer_devices():
    c1 = Customer.objects.create(name="Acme")
    c2 = Customer.objects.create(name="Beta")
    cred1 = _make_credential(c1, name="c1")
    cred2 = _make_credential(c2, name="c2")
    Device.objects.create(
        customer=c1,
        hostname="edge1",
        mgmt_ip="192.0.2.11",
        vendor="cisco",
        platform="ios",
        credential=cred1,
    )
    Device.objects.create(
        customer=c2,
        hostname="edge2",
        mgmt_ip="192.0.2.12",
        vendor="juniper",
        platform="junos",
        credential=cred2,
    )
    operator = User.objects.create_user(username="op", password="secret123", role="operator")
    operator.customers.add(c1)

    client = APIClient()
    client.login(username="op", password="secret123")

    resp = client.get("/api/v1/devices/")
    assert resp.status_code == 200
    payload = resp.json()
    results = payload.get("results", payload)
    if isinstance(results, dict):
        results = [results]
    assert len(results) == 1
    assert results[0]["customer"] == c1.id
    assert results[0]["hostname"] == "edge1"


@pytest.mark.django_db
def test_job_logs_are_scoped_by_customer():
    c1 = Customer.objects.create(name="Acme")
    c2 = Customer.objects.create(name="Beta")
    user = User.objects.create_user(username="op", password="secret123", role="operator")
    user.customers.add(c1)
    other = User.objects.create_user(username="admin", password="secret123", role="admin")
    other.customers.add(c2)
    job_c2 = Job.objects.create(type="run_commands", status="success", user=other, customer=c2)

    client = APIClient()
    client.login(username="op", password="secret123")

    resp = client.get(f"/api/v1/jobs/{job_c2.id}/logs")
    assert resp.status_code == 404


@pytest.mark.django_db
def test_htmx_commands_block_viewers():
    customer = Customer.objects.create(name="Acme")
    viewer = User.objects.create_user(username="viewui", password="secret123", role="viewer")
    viewer.customers.add(customer)
    client = Client()
    client.login(username="viewui", password="secret123")

    resp = client.post(
        "/commands/",
        {"command": "show ip int br"},
        HTTP_HX_REQUEST="true",
    )

    assert resp.status_code == 403
