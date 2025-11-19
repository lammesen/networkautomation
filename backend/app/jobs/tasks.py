from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Iterable, List

from celery import shared_task
from sqlalchemy.orm import Session

from app.automation.nornir_init import init_nornir_from_db
from app.automation.tasks_cli import run_commands
from app.automation.tasks_config import commit_merge, get_running_config, preview_merge
from app.automation.tasks_validate import run_policy
from app.compliance.models import ComplianceResult
from app.config_backup.models import ConfigSnapshot
from app.core.config import settings
from app.db.session import SessionLocal
from app.devices.models import Device
from app.jobs.events import publish_job_event
from app.jobs.models import Job, JobLog


def _log(
    db: Session,
    job: Job,
    level: str,
    message: str,
    host: str | None = None,
    extra: dict | None = None,
) -> None:
    payload = extra or {}
    log = JobLog(
        job_id=job.id,
        level=level,
        message=message,
        host=host,
        extra_json=json.dumps(payload),
    )
    db.add(log)
    db.commit()
    try:
        publish_job_event(
            job.id,
            {
                "ts": log.ts.isoformat(),
                "level": level,
                "message": message,
                "host": host,
                "extra": payload,
            },
        )
    except Exception:  # pragma: no cover - logging best effort
        pass


def _update_job(db: Session, job: Job, **kwargs) -> None:
    for key, value in kwargs.items():
        setattr(job, key, value)
    db.add(job)
    db.commit()


def _load_job(db: Session, job_id: int) -> Job:
    job = db.get(Job, job_id)
    if not job:
        raise ValueError("Job not found")
    return job


def _ensure_targets(device_ids: Iterable[int]) -> List[int]:
    ids = list(device_ids)
    if not ids:
        raise ValueError("No devices matched the requested filters")
    return ids


def _device_lookup(db: Session, device_ids: Iterable[int]) -> dict[str, Device]:
    devices = db.query(Device).filter(Device.id.in_(list(device_ids))).all()
    return {device.hostname: device for device in devices}


@shared_task(name="app.jobs.tasks.run_commands")
def run_commands_task(job_id: int, device_ids: List[int], commands: List[str], timeout: int | None = None) -> None:
    db = SessionLocal()
    job = _load_job(db, job_id)
    started_at = datetime.utcnow()
    _update_job(db, job, status="running", started_at=started_at)
    status = "success"
    summary: dict[str, dict[str, object]] = {"devices": {}}
    try:
        targets = _ensure_targets(device_ids)
        nr = init_nornir_from_db(db, targets)
        aggregated = nr.run(task=run_commands, commands=commands, timeout=timeout)
        for host, result in aggregated.items():
            host_summary = {
                "ok": not result.failed,
                "outputs": result.result,
            }
            if result.failed:
                status = "partial"
                host_summary["error"] = str(result.exception) if result.exception else "Command failed"
                _log(db, job, "ERROR", "Command execution failed", host, host_summary)
            else:
                _log(db, job, "INFO", "Commands executed", host, host_summary)
            summary["devices"][host] = host_summary
    except Exception as exc:  # pragma: no cover - defensive logging
        status = "failed"
        summary["error"] = str(exc)
        _log(db, job, "ERROR", f"Command job failed: {exc}")
        raise
    finally:
        _update_job(
            db,
            job,
            status=status,
            finished_at=datetime.utcnow(),
            result_summary_json=json.dumps(summary),
        )
        db.close()


@shared_task(name="app.jobs.tasks.backup_configs")
def backup_configs(job_id: int, device_ids: List[int], source: str) -> None:
    db = SessionLocal()
    job = _load_job(db, job_id)
    _update_job(db, job, status="running", started_at=datetime.utcnow())
    summary: dict[str, object] = {"snapshots": {}, "changed": 0, "unchanged": 0}
    status = "success"
    try:
        targets = _ensure_targets(device_ids)
        nr = init_nornir_from_db(db, targets)
        aggregated = nr.run(task=get_running_config)
        device_lookup = _device_lookup(db, targets)
        for host, result in aggregated.items():
            device = device_lookup.get(host)
            if not device:
                continue
            running_config = result.result
            digest = hashlib.sha256(running_config.encode()).hexdigest()
            latest = (
                db.query(ConfigSnapshot)
                .filter(ConfigSnapshot.device_id == device.id)
                .order_by(ConfigSnapshot.created_at.desc())
                .first()
            )
            if not latest or latest.hash != digest:
                snapshot = ConfigSnapshot(
                    device_id=device.id,
                    job_id=job.id,
                    source=source,
                    config_text=running_config,
                    hash=digest,
                )
                db.add(snapshot)
                db.commit()
                summary["changed"] += 1
                summary["snapshots"][host] = {
                    "snapshot_id": snapshot.id,
                    "hash": digest,
                }
                _log(db, job, "INFO", "Config snapshot stored", host, summary["snapshots"][host])
            else:
                summary["unchanged"] += 1
                _log(db, job, "INFO", "No config change detected", host, {"hash": digest})
    except Exception as exc:  # pragma: no cover - defensive logging
        status = "failed"
        summary["error"] = str(exc)
        _log(db, job, "ERROR", f"Backup job failed: {exc}")
        raise
    finally:
        _update_job(
            db,
            job,
            status=status,
            finished_at=datetime.utcnow(),
            result_summary_json=json.dumps(summary),
        )
        db.close()


@shared_task(name="app.jobs.tasks.preview_deploy")
def preview_deploy(job_id: int, device_ids: List[int], snippet: str, mode: str = "merge") -> None:
    db = SessionLocal()
    job = _load_job(db, job_id)
    _update_job(db, job, status="running", started_at=datetime.utcnow())
    status = "success"
    diffs: dict[str, object] = {}
    try:
        targets = _ensure_targets(device_ids)
        nr = init_nornir_from_db(db, targets)
        aggregated = nr.run(task=preview_merge, snippet=snippet, mode=mode)
        for host, result in aggregated.items():
            diff = result.result or ""
            diffs[host] = {"diff": diff}
            _log(db, job, "INFO", "Preview diff generated", host, diffs[host])
            if not diff:
                status = "partial"
    except Exception as exc:  # pragma: no cover
        status = "failed"
        diffs["error"] = str(exc)
        _log(db, job, "ERROR", f"Preview failed: {exc}")
        raise
    finally:
        _update_job(
            db,
            job,
            status=status,
            finished_at=datetime.utcnow(),
            result_summary_json=json.dumps({"snippet": snippet, "diffs": diffs, "mode": mode}),
        )
        db.close()


@shared_task(name="app.jobs.tasks.commit_deploy")
def commit_deploy(job_id: int, device_ids: List[int], snippet: str, mode: str = "merge") -> None:
    db = SessionLocal()
    job = _load_job(db, job_id)
    _update_job(db, job, status="running", started_at=datetime.utcnow())
    status = "success"
    results: dict[str, object] = {}
    try:
        targets = _ensure_targets(device_ids)
        nr = init_nornir_from_db(db, targets)
        aggregated = nr.run(task=commit_merge, snippet=snippet, mode=mode)
        for host, result in aggregated.items():
            host_payload = {"status": "committed", "details": result.result}
            if result.failed:
                status = "partial"
                host_payload["status"] = "error"
                host_payload["details"] = str(result.exception or "Commit failed")
                _log(db, job, "ERROR", "Commit failed", host, host_payload)
            else:
                _log(db, job, "INFO", "Commit completed", host, host_payload)
            results[host] = host_payload
    except Exception as exc:  # pragma: no cover
        status = "failed"
        results["error"] = str(exc)
        _log(db, job, "ERROR", f"Commit job failed: {exc}")
        raise
    finally:
        _update_job(
            db,
            job,
            status=status,
            finished_at=datetime.utcnow(),
            result_summary_json=json.dumps(results),
        )
        db.close()


@shared_task(name="app.jobs.tasks.compliance")
def compliance_task(job_id: int, device_ids: List[int], policy: dict) -> None:
    db = SessionLocal()
    job = _load_job(db, job_id)
    _update_job(db, job, status="running", started_at=datetime.utcnow())
    status = "success"
    results: dict[str, object] = {}
    try:
        targets = _ensure_targets(device_ids)
        nr = init_nornir_from_db(db, targets)
        aggregated = nr.run(task=run_policy, policy=policy)
        device_lookup = _device_lookup(db, targets)
        for host, result in aggregated.items():
            payload = result.result or {}
            status_value = payload.get("status", "unknown")
            results[host] = payload
            _log(db, job, "INFO", "Compliance evaluated", host, payload)
            device = device_lookup.get(host)
            if device:
                compliance_result = ComplianceResult(
                    policy_id=policy.get("id"),
                    device_id=device.id,
                    job_id=job.id,
                    status=status_value,
                    details_json=json.dumps(payload),
                )
                db.add(compliance_result)
                db.commit()
            if status_value != "pass":
                status = "partial"
    except Exception as exc:  # pragma: no cover
        status = "failed"
        results["error"] = str(exc)
        _log(db, job, "ERROR", f"Compliance job failed: {exc}")
        raise
    finally:
        _update_job(
            db,
            job,
            status=status,
            finished_at=datetime.utcnow(),
            result_summary_json=json.dumps(results),
        )
        db.close()


def enqueue_job(task, *args) -> None:
    if settings.execute_jobs_inline:
        task.apply(args=args)
    else:
        task.delay(*args)
