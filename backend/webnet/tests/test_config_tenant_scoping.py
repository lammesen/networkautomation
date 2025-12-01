import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from webnet.customers.models import Customer
from webnet.devices.models import Device, Credential
from webnet.config_mgmt.models import ConfigSnapshot
from webnet.jobs.models import Job

User = get_user_model()


def _client_for_customer(role: str, customer: Customer) -> APIClient:
    user = User.objects.create_user(
        username=f"{role}-{customer.name}", password="secret123", role=role
    )
    user.customers.add(customer)
    client = APIClient()
    client.login(username=user.username, password="secret123")
    return client


@pytest.mark.django_db
def test_config_snapshot_and_diff_denied_cross_tenant():
    c1 = Customer.objects.create(name="Acme")
    c2 = Customer.objects.create(name="Beta")
    user1 = User.objects.create_user(username="owner", password="secret123", role="admin")
    user1.customers.add(c1)
    cred = Credential.objects.create(customer=c1, name="lab", username="u1")
    cred.password = "pass"
    cred.save()
    device = Device.objects.create(
        customer=c1,
        hostname="r1",
        mgmt_ip="192.0.2.10",
        vendor="cisco",
        platform="ios",
        credential=cred,
    )
    job = Job.objects.create(type="config_backup", status="success", user=user1, customer=c1)
    snap1 = ConfigSnapshot.objects.create(device=device, job=job, source="manual", config_text="a")
    snap2 = ConfigSnapshot.objects.create(device=device, job=job, source="manual", config_text="b")

    client = _client_for_customer("operator", c2)

    resp_snapshot = client.get(f"/api/v1/config/snapshots/{snap1.id}/")
    assert resp_snapshot.status_code == 404

    resp_device_snaps = client.get(f"/api/v1/config/devices/{device.id}/snapshots")
    assert resp_device_snaps.status_code == 404

    resp_diff = client.get(f"/api/v1/config/devices/{device.id}/diff?from={snap1.id}&to={snap2.id}")
    assert resp_diff.status_code == 404


@pytest.mark.django_db
def test_device_detail_actions_respect_tenant():
    c1 = Customer.objects.create(name="Acme")
    c2 = Customer.objects.create(name="Beta")
    cred = Credential.objects.create(customer=c1, name="lab", username="u1")
    cred.password = "pass"
    cred.save()
    device = Device.objects.create(
        customer=c1,
        hostname="r1",
        mgmt_ip="192.0.2.10",
        vendor="cisco",
        platform="ios",
        credential=cred,
    )

    client = _client_for_customer("viewer", c2)

    for path in ("jobs", "snapshots", "topology"):
        resp = client.get(f"/api/v1/devices/{device.id}/{path}/")
        assert resp.status_code == 404


@pytest.mark.django_db
def test_job_logs_api_denied_cross_tenant():
    c1 = Customer.objects.create(name="Acme")
    c2 = Customer.objects.create(name="Beta")
    user1 = User.objects.create_user(username="owner", password="secret123", role="admin")
    user1.customers.add(c1)
    job = Job.objects.create(type="run_commands", status="success", user=user1, customer=c1)

    client = _client_for_customer("viewer", c2)
    resp = client.get(f"/api/v1/jobs/{job.id}/logs")
    assert resp.status_code == 404
