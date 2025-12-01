import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from webnet.customers.models import Customer
from webnet.devices.models import Credential, Device, TopologyLink
from webnet.config_mgmt.models import ConfigSnapshot
from webnet.jobs.models import Job
from webnet.compliance.models import CompliancePolicy, ComplianceResult
from webnet.users.models import User


def _make_user(username: str, customer: Customer, role: str = "admin") -> User:
    user = User.objects.create_user(username=username, password="secret123", role=role)
    user.customers.add(customer)
    return user


def _make_device(customer: Customer, hostname: str = "r1") -> Device:
    cred = Credential(customer=customer, name=f"cred-{hostname}", username="netops")
    cred.password = "password123"
    cred.save()
    return Device.objects.create(
        customer=customer,
        hostname=hostname,
        mgmt_ip="192.0.2.10",
        vendor="cisco",
        platform="ios",
        credential=cred,
    )


@pytest.mark.django_db
def test_device_detail_htmx_sections():
    customer = Customer.objects.create(name="Acme")
    user = _make_user("alice", customer)
    device = _make_device(customer, hostname="edge1")
    job = Job.objects.create(type="run_commands", status="success", user=user, customer=customer)
    ConfigSnapshot.objects.create(device=device, job=job, source="manual", config_text="cfg")
    TopologyLink.objects.create(
        customer=customer,
        local_device=device,
        local_interface="Gi0/1",
        remote_hostname="sw1",
        remote_interface="Gi0/2",
        protocol="cdp",
    )

    client = APIClient()
    client.login(username="alice", password="secret123")

    detail = client.get(reverse("devices-detail", args=[device.id]))
    assert detail.status_code == 200
    assert "edge1" in detail.content.decode()

    snaps = client.get(reverse("devices-snapshots", args=[device.id]), HTTP_HX_REQUEST="true")
    assert snaps.status_code == 200
    assert "manual" in snaps.content.decode()

    jobs = client.get(reverse("devices-jobs", args=[device.id]), HTTP_HX_REQUEST="true")
    assert jobs.status_code == 200
    assert f"#{job.id}" in jobs.content.decode()

    topo = client.get(reverse("devices-topology", args=[device.id]), HTTP_HX_REQUEST="true")
    assert topo.status_code == 200
    assert "sw1" in topo.content.decode()


@pytest.mark.django_db
def test_topology_htmx_scopes_customer():
    c1 = Customer.objects.create(name="Acme")
    c2 = Customer.objects.create(name="Beta")
    _make_user("bob", c1, role="operator")
    d1 = _make_device(c1, hostname="edge-a")
    d2 = _make_device(c2, hostname="edge-b")
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

    client = APIClient()
    client.login(username="bob", password="secret123")
    resp = client.get(reverse("topology-list"), HTTP_HX_REQUEST="true")
    body = resp.content.decode()
    assert resp.status_code == 200
    assert "sw-a" in body
    assert "sw-b" not in body


@pytest.mark.django_db
def test_compliance_overview_htmx_latest_status():
    customer = Customer.objects.create(name="Acme")
    user = _make_user("carol", customer)
    policy = CompliancePolicy.objects.create(
        customer=customer,
        name="Baseline",
        description="",
        scope_json={},
        definition_yaml="rules: []",
        created_by=user,
    )
    ComplianceResult.objects.create(
        policy=policy,
        device=_make_device(customer, hostname="r-ov"),
        job=Job.objects.create(
            type="compliance_check", status="success", user=user, customer=customer
        ),
        status="fail",
        details_json={},
    )
    ComplianceResult.objects.create(
        policy=policy,
        device=_make_device(customer, hostname="r-ov2"),
        job=Job.objects.create(
            type="compliance_check", status="success", user=user, customer=customer
        ),
        status="pass",
        details_json={},
    )

    client = APIClient()
    client.login(username="carol", password="secret123")

    resp = client.get(reverse("compliance-overview"), HTTP_HX_REQUEST="true")
    assert resp.status_code == 200
    content = resp.content.decode()
    assert "Baseline" in content
    assert "Pass" in content
