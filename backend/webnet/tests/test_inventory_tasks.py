import pytest
from django.contrib.auth import get_user_model

from webnet.automation import build_inventory
from webnet.customers.models import Customer
from webnet.devices.models import Credential, Device
from webnet.jobs.models import Job, JobLog
from webnet.jobs.services import JobService
from webnet.jobs import tasks
from webnet.config_mgmt.models import ConfigSnapshot

User = get_user_model()


def _make_device(customer: Customer, hostname: str = "edge1", site: str = "DC1") -> Device:
    cred = Credential(customer=customer, name=f"cred-{hostname}", username="netops")
    cred.password = "password123"
    cred.save()
    return Device.objects.create(
        customer=customer,
        hostname=hostname,
        mgmt_ip="192.0.2.10",
        vendor="cisco",
        platform="ios",
        site=site,
        credential=cred,
        enabled=True,
    )


@pytest.mark.django_db
def test_build_inventory_scopes_by_customer_and_filters():
    c1 = Customer.objects.create(name="Acme")
    c2 = Customer.objects.create(name="Beta")
    _make_device(c1, hostname="edge-a", site="DC1")
    _make_device(c2, hostname="edge-b", site="DC2")

    inv = build_inventory({"site": "DC1"}, customer_id=c1.id)

    assert set(inv.hosts.keys()) == {"edge-a"}
    host = inv.hosts["edge-a"]
    assert host.username == "netops"
    assert host.extras["customer_id"] == c1.id
    assert host.extras["site"] == "DC1"


class _DummyResult:
    def __init__(self, result, failed: bool = False, exception=None):
        self.result = result
        self.failed = failed
        self.exception = exception


class _DummyInventory:
    def __init__(self, hostnames):
        self.hosts = {h: object() for h in hostnames}


class _DummyNornir:
    def __init__(self, hostnames):
        self.hostnames = list(hostnames)

    def run(self, task, **kwargs):
        results = {}
        for host in self.hostnames:
            if task.__name__ == "napalm_get":
                results[host] = _DummyResult({"config": {"running": "cfg"}})
            else:
                results[host] = _DummyResult(f"ran {task.__name__}")
        return results


@pytest.mark.django_db
def test_run_commands_job_updates_status_and_logs(monkeypatch):
    customer = Customer.objects.create(name="Acme")
    user = User.objects.create_user(username="alice", password="secret123", role="admin")
    user.customers.add(customer)
    _make_device(customer, hostname="edge1")
    job = Job.objects.create(type="run_commands", status="queued", user=user, customer=customer)

    monkeypatch.setattr(
        tasks, "build_inventory", lambda targets=None, customer_id=None: _DummyInventory(["edge1"])
    )
    monkeypatch.setattr(tasks, "_nr_from_inventory", lambda inv: _DummyNornir(inv.hosts.keys()))

    tasks.run_commands_job(job.id, {"filters": {}}, ["show version"], timeout=5)

    job.refresh_from_db()
    assert job.status == "success"
    assert JobLog.objects.filter(job=job).exists()


@pytest.mark.django_db
def test_config_backup_job_creates_snapshot(monkeypatch):
    customer = Customer.objects.create(name="Acme")
    user = User.objects.create_user(username="alice", password="secret123", role="admin")
    user.customers.add(customer)
    device = _make_device(customer, hostname="edge1")
    job = Job.objects.create(type="config_backup", status="queued", user=user, customer=customer)

    monkeypatch.setattr(
        tasks,
        "build_inventory",
        lambda targets=None, customer_id=None: _DummyInventory([device.hostname]),
    )
    monkeypatch.setattr(tasks, "_nr_from_inventory", lambda inv: _DummyNornir(inv.hosts.keys()))

    tasks.config_backup_job(job.id, {"filters": {}}, source_label="manual")

    job.refresh_from_db()
    assert job.status == "success"
    assert ConfigSnapshot.objects.filter(device=device, job=job).exists()


@pytest.mark.django_db
def test_enqueue_passes_customer_filters_for_reachability():
    customer = Customer.objects.create(name="Acme")
    user = User.objects.create_user(username="alice", password="secret123", role="admin")
    user.customers.add(customer)
    job = Job.objects.create(
        type="check_reachability",
        status="queued",
        user=user,
        customer=customer,
        target_summary_json={"filters": {"site": "DC1"}},
    )

    captured = {}

    def _dispatcher(name, args=None, kwargs=None):
        captured["name"] = name
        captured["args"] = args
        captured["kwargs"] = kwargs

    js = JobService(dispatcher=_dispatcher)
    js._enqueue(job)

    assert captured["name"] == "check_reachability_job"
    assert captured["args"] == (job.id, {"site": "DC1"})
    assert captured["kwargs"] is None
