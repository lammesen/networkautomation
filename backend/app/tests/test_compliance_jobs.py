"""Tests for compliance Celery task behavior."""

from app.automation import context as automation_context
from app.db.models import CompliancePolicy, ComplianceResult, Device, Job
from app.jobs import tasks as job_tasks


def test_compliance_check_job_records_results(
    monkeypatch, db_session, admin_user, test_customer, test_credential
):
    """Compliance task should honor validation results."""
    device = Device(
        hostname="comp-dev1",
        mgmt_ip="192.0.2.55",
        vendor="cisco",
        platform="ios",
        credentials_ref=test_credential.id,
        customer_id=test_customer.id,
        enabled=True,
    )
    db_session.add(device)
    db_session.commit()
    db_session.refresh(device)

    policy = CompliancePolicy(
        name="policy1",
        description="",
        scope_json={},  # filters are not evaluated in the stub
        definition_yaml="---\nget_facts:\n  hostname: expected",
        created_by=admin_user.id,
        customer_id=test_customer.id,
    )
    job = Job(
        type="compliance_check",
        status="queued",
        user_id=admin_user.id,
        customer_id=test_customer.id,
        target_summary_json={},
        payload_json={"policy_id": 0},
    )
    db_session.add_all([policy, job])
    db_session.commit()
    db_session.refresh(job)
    db_session.refresh(policy)

    # Ensure task uses the same test session
    monkeypatch.setattr(job_tasks, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(job_tasks.JobExecution, "__exit__", lambda self, exc_type, exc, tb: None)

    # Limit device selection to our device
    monkeypatch.setattr(
        automation_context,
        "filter_devices_from_db",
        lambda filters, customer_id=None: [device.id],
    )

    class FakeResult:
        def __init__(self, complies: bool):
            self.failed = False
            self.result = {"complies": complies}
            self.exception = None

    class FakeNornir:
        def run(self, task, validation_source):
            return {device.hostname: FakeResult(False)}

    def fake_nornir(self, num_workers: int = 10):
        return FakeNornir()

    monkeypatch.setattr(automation_context.AutomationContext, "nornir", fake_nornir)

    job_tasks.compliance_check_job(job.id, policy.id)

    db_session.refresh(job)
    results = db_session.query(ComplianceResult).all()

    assert job.status == "success"
    assert len(results) == 1
    assert results[0].status == "fail"
