"""Tests for the JobService orchestration layer."""

from datetime import datetime, timedelta

from app.db import Customer, User
from app.services.job_service import JobService


def _create_user(db_session, username="tester", role="admin"):
    user = User(
        username=username,
        hashed_password="hashed",
        role=role,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _create_customer(db_session, name="tenant"):
    customer = Customer(name=name)
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    return customer


def test_create_job_records_payload(db_session):
    user = _create_user(db_session)
    customer = _create_customer(db_session)
    service = JobService(db_session)

    job = service.create_job(
        job_type="run_commands",
        user=user,
        customer_id=customer.id,
        target_summary={"filters": {"site": "dc1"}},
        payload={"commands": ["show version"]},
    )

    assert job.id is not None
    assert job.status == "queued"
    assert job.target_summary_json == {"filters": {"site": "dc1"}}
    assert job.payload_json == {"commands": ["show version"]}


def test_set_status_updates_timestamps(db_session):
    user = _create_user(db_session)
    customer = _create_customer(db_session)
    service = JobService(db_session)
    job = service.create_job(
        job_type="config_backup",
        user=user,
        customer_id=customer.id,
    )

    service.set_status(job.id, "running")
    db_session.refresh(job)
    assert job.started_at is not None
    started_at = job.started_at

    service.set_status(job.id, "success", {"total": 1})
    db_session.refresh(job)
    assert job.finished_at is not None
    assert job.finished_at >= started_at
    assert job.result_summary_json == {"total": 1}


def test_append_log_persists_entries(db_session):
    user = _create_user(db_session)
    customer = _create_customer(db_session)
    service = JobService(db_session)
    job = service.create_job(
        job_type="compliance_check",
        user=user,
        customer_id=customer.id,
    )

    service.append_log(job.id, level="INFO", message="Started", host=None)
    service.append_log(job.id, level="ERROR", message="Failure", host="router1")

    logs = job.logs
    assert len(logs) == 2
    assert logs[0].message == "Started"
    assert logs[1].host == "router1"


def test_create_job_can_be_scheduled(db_session):
    """Scheduled jobs should record scheduled_for and status."""
    user = _create_user(db_session)
    customer = _create_customer(db_session)
    service = JobService(db_session)
    schedule_time = datetime.utcnow() + timedelta(hours=1)

    job = service.create_job(
        job_type="run_commands",
        user=user,
        customer_id=customer.id,
        scheduled_for=schedule_time,
    )

    assert job.status == "scheduled"
    # Stored timestamp may lose microseconds; compare using timestamp
    assert int(job.scheduled_for.timestamp()) == int(schedule_time.timestamp())



