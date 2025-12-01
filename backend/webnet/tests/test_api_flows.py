import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from webnet.customers.models import Customer
from webnet.devices.models import Credential, Device, TopologyLink
from webnet.jobs.models import Job
from webnet.config_mgmt.models import ConfigSnapshot
from webnet.compliance.models import CompliancePolicy
from webnet.jobs.services import JobService

User = get_user_model()


def _make_user(role: str = "admin", customer: Customer | None = None) -> User:
    if customer is None:
        customer = Customer.objects.create(name="Acme")
    user = User.objects.create_user(username=f"{role}-user", password="secret123", role=role)
    user.customers.add(customer)
    return user


def _make_credential(customer: Customer, name: str = "lab") -> Credential:
    cred = Credential(customer=customer, name=name, username="netops")
    cred.password = "password123"
    cred.save()
    return cred


def _auth_client(user: User) -> APIClient:
    client = APIClient()
    client.login(username=user.username, password="secret123")
    return client


@pytest.mark.django_db
def test_devices_crud_and_import(monkeypatch):
    customer = Customer.objects.create(name="Acme")
    user = _make_user("admin", customer)
    cred = _make_credential(customer)
    client = _auth_client(user)

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
    assert resp.status_code == 201, resp.content

    csv_content = "hostname,mgmt_ip,vendor,platform,credential\nr2,192.0.2.11,cisco,ios,lab\n"
    upload = SimpleUploadedFile("devices.csv", csv_content.encode(), content_type="text/csv")
    resp_import = client.post(
        "/api/v1/devices/import",
        {"file": upload, "customer_id": customer.id},
        format="multipart",
    )
    assert resp_import.status_code == 200, resp_import.content
    summary = resp_import.json()
    assert summary["created"] == 1

    list_resp = client.get("/api/v1/devices/")
    assert list_resp.status_code == 200
    assert any(item["hostname"] == "r1" for item in list_resp.json()["results"])


@pytest.mark.django_db
def test_jobs_retry_and_cancel(monkeypatch):
    customer = Customer.objects.create(name="Acme")
    user = _make_user("admin", customer)
    client = _auth_client(user)
    job = Job.objects.create(type="run_commands", status="success", user=user, customer=customer)
    queued = Job.objects.create(type="run_commands", status="queued", user=user, customer=customer)

    monkeypatch.setattr(JobService, "_enqueue", lambda self, job: None)

    resp_retry = client.post(f"/api/v1/jobs/{job.id}/retry")
    assert resp_retry.status_code == 202
    assert resp_retry.json().get("job_id")

    resp_cancel = client.post(f"/api/v1/jobs/{queued.id}/cancel")
    assert resp_cancel.status_code == 200
    queued.refresh_from_db()
    assert queued.status == "cancelled"


@pytest.mark.django_db
def test_config_deploy_and_diff(monkeypatch):
    customer = Customer.objects.create(name="Acme")
    user = _make_user("admin", customer)
    client = _auth_client(user)
    device = Device.objects.create(
        customer=customer,
        hostname="r1",
        mgmt_ip="192.0.2.10",
        vendor="cisco",
        platform="ios",
        credential=_make_credential(customer),
    )
    job = Job.objects.create(type="config_backup", status="success", user=user, customer=customer)
    snap1 = ConfigSnapshot.objects.create(
        device=device, job=job, source="manual", config_text="int a"
    )
    snap2 = ConfigSnapshot.objects.create(
        device=device, job=job, source="manual", config_text="int b"
    )

    monkeypatch.setattr(JobService, "_enqueue", lambda self, job: None)

    resp_preview = client.post(
        "/api/v1/config/deploy/preview",
        {"customer_id": customer.id, "mode": "merge", "snippet": "snip", "targets": {}},
        format="json",
    )
    assert resp_preview.status_code == 202

    resp_diff = client.get(f"/api/v1/config/devices/{device.id}/diff?from={snap1.id}&to={snap2.id}")

    assert resp_diff.status_code == 200
    assert "diff" in resp_diff.json()


@pytest.mark.django_db
def test_compliance_run(monkeypatch):
    customer = Customer.objects.create(name="Acme")
    user = _make_user("admin", customer)
    client = _auth_client(user)
    policy = CompliancePolicy.objects.create(
        customer=customer,
        name="Baseline",
        description="",
        scope_json={},
        definition_yaml="rules: []",
        created_by=user,
    )

    monkeypatch.setattr(JobService, "_enqueue", lambda self, job: None)

    resp = client.post(f"/api/v1/compliance/policies/{policy.id}/run/")
    assert resp.status_code == 202
    assert resp.json().get("job_id")


@pytest.mark.django_db
def test_topology_list_and_clear():
    c1 = Customer.objects.create(name="Acme")
    c2 = Customer.objects.create(name="Beta")
    user = _make_user("admin", c1)
    client = _auth_client(user)
    d1 = Device.objects.create(
        customer=c1,
        hostname="r1",
        mgmt_ip="192.0.2.10",
        vendor="cisco",
        platform="ios",
        credential=_make_credential(c1),
    )
    d2 = Device.objects.create(
        customer=c2,
        hostname="r2",
        mgmt_ip="192.0.2.20",
        vendor="cisco",
        platform="ios",
        credential=_make_credential(c2),
    )
    TopologyLink.objects.create(
        customer=c1,
        local_device=d1,
        local_interface="Gi0/1",
        remote_hostname="sw-a",
        remote_interface="Gi0/2",
        protocol="cdp",
    )
    TopologyLink.objects.create(
        customer=c2,
        local_device=d2,
        local_interface="Gi0/1",
        remote_hostname="sw-b",
        remote_interface="Gi0/2",
        protocol="cdp",
    )

    resp_list = client.get("/api/v1/topology/links/")
    assert resp_list.status_code == 200
    results = resp_list.json()["results"]
    assert any(link["remote_hostname"] == "sw-a" for link in results)
    assert any(link["remote_hostname"] == "sw-b" for link in results)

    resp_clear = client.delete("/api/v1/topology/links/clear/")
    assert resp_clear.status_code == 200
    assert resp_clear.json()["deleted"] == 2


@pytest.mark.django_db
def test_bulk_backup(monkeypatch):
    """Test bulk-backup endpoint queues config backup jobs for multiple devices."""
    customer = Customer.objects.create(name="Acme")
    user = _make_user("admin", customer)
    cred = _make_credential(customer)
    client = _auth_client(user)

    # Create test devices
    d1 = Device.objects.create(
        customer=customer,
        hostname="r1",
        mgmt_ip="192.0.2.10",
        vendor="cisco",
        platform="ios",
        credential=cred,
    )
    d2 = Device.objects.create(
        customer=customer,
        hostname="r2",
        mgmt_ip="192.0.2.11",
        vendor="cisco",
        platform="ios",
        credential=cred,
    )

    monkeypatch.setattr(JobService, "_enqueue", lambda self, job: None)

    # Test with valid device IDs
    resp = client.post(
        "/api/v1/devices/bulk-backup/",
        {"device_ids": [d1.id, d2.id]},
        format="json",
    )
    assert resp.status_code == 202, resp.content
    data = resp.json()
    assert data["total_devices"] == 2
    assert len(data["jobs"]) == 1  # All devices belong to same customer
    assert data["jobs"][0]["device_count"] == 2

    # Verify job was created
    job = Job.objects.get(pk=data["jobs"][0]["job_id"])
    assert job.type == "config_backup"
    assert job.customer == customer

    # Test with no device IDs
    resp_empty = client.post("/api/v1/devices/bulk-backup/", {"device_ids": []}, format="json")
    assert resp_empty.status_code == 400


@pytest.mark.django_db
def test_bulk_compliance(monkeypatch):
    """Test bulk-compliance endpoint queues compliance check jobs for multiple devices."""
    customer = Customer.objects.create(name="Acme")
    user = _make_user("admin", customer)
    cred = _make_credential(customer)
    client = _auth_client(user)

    # Create test devices
    d1 = Device.objects.create(
        customer=customer,
        hostname="r1",
        mgmt_ip="192.0.2.10",
        vendor="cisco",
        platform="ios",
        credential=cred,
    )
    d2 = Device.objects.create(
        customer=customer,
        hostname="r2",
        mgmt_ip="192.0.2.11",
        vendor="cisco",
        platform="ios",
        credential=cred,
    )

    monkeypatch.setattr(JobService, "_enqueue", lambda self, job: None)

    # Test with valid device IDs
    resp = client.post(
        "/api/v1/devices/bulk-compliance/",
        {"device_ids": [d1.id, d2.id]},
        format="json",
    )
    assert resp.status_code == 202, resp.content
    data = resp.json()
    assert data["total_devices"] == 2
    assert len(data["jobs"]) == 1  # All devices belong to same customer
    assert data["jobs"][0]["device_count"] == 2

    # Verify job was created
    job = Job.objects.get(pk=data["jobs"][0]["job_id"])
    assert job.type == "compliance_check"
    assert job.customer == customer

    # Test with no device IDs
    resp_empty = client.post("/api/v1/devices/bulk-compliance/", {"device_ids": []}, format="json")
    assert resp_empty.status_code == 400
