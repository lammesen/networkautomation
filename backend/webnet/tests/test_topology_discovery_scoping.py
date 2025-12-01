import pytest
from django.contrib.auth import get_user_model

from webnet.jobs.models import Job
from webnet.jobs import tasks
from webnet.customers.models import Customer
from webnet.devices.models import Device, Credential, TopologyLink

User = get_user_model()


class _FakeResult:
    def __init__(self, output: str):
        self.failed = False
        self.result = output
        self.exception = None


class _FakeNR:
    def __init__(self, output: str):
        self.output = output

    def run(self, *args, **kwargs):
        return {"h1": _FakeResult(self.output)}


class _FakeInventory:
    def __init__(self, hosts_present: bool = True):
        self.hosts = {"h1": {}} if hosts_present else {}


@pytest.mark.django_db
def test_topology_discovery_scopes_device_lookup(monkeypatch):
    c1 = Customer.objects.create(name="Acme")
    c2 = Customer.objects.create(name="Beta")
    user = User.objects.create_user(username="owner", password="secret123", role="admin")
    user.customers.add(c1)

    # Device with hostname exists only in different customer (c2)
    cred2 = Credential.objects.create(customer=c2, name="lab", username="u1")
    cred2.password = "pass"
    cred2.save()
    Device.objects.create(
        customer=c2,
        hostname="h1",
        mgmt_ip="192.0.2.10",
        vendor="cisco",
        platform="ios",
        credential=cred2,
    )

    job = Job.objects.create(type="topology_discovery", status="queued", user=user, customer=c1)

    monkeypatch.setattr(tasks, "build_inventory", lambda targets, customer_id: _FakeInventory())
    monkeypatch.setattr(
        tasks,
        "_nr_from_inventory",
        lambda inv: _FakeNR("Device ID : sw\nInterface: Gi0/1, Port ID (outgoing port): Gi0/2"),
    )

    tasks.topology_discovery_job(job.id, targets={})

    assert TopologyLink.objects.count() == 0
