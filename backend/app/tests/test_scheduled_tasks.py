"""Tests for scheduled Celery tasks."""

from app.jobs import tasks as job_tasks


def test_scheduled_backup_creates_jobs_per_customer(
    monkeypatch, db_session, test_customer, second_customer, admin_user
):
    """Ensure scheduled backup wires customer_id and avoids TypeError."""
    created_customers: list[int] = []
    invoked_targets: list[int | None] = []

    def fake_create_job(db, job_type, user, customer_id, target_summary, payload):
        created_customers.append(customer_id)

        class FakeJob:
            def __init__(self, job_id: int):
                self.id = job_id

        return FakeJob(len(created_customers))

    def fake_config_backup(job_id: int, targets: dict, source_label: str) -> None:
        invoked_targets.append(targets.get("customer_id"))

    monkeypatch.setattr("app.jobs.manager.create_job", fake_create_job)
    monkeypatch.setattr(job_tasks, "config_backup_job", fake_config_backup)
    monkeypatch.setattr(job_tasks, "SessionLocal", lambda: db_session)

    job_tasks.scheduled_config_backup()

    assert set(created_customers) == {test_customer.id, second_customer.id}
    assert set(invoked_targets) == {test_customer.id, second_customer.id}
