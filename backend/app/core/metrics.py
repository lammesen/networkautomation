"""Prometheus metrics for the Network Automation API.

This module provides application metrics for monitoring with Prometheus.
Metrics are exposed at the /metrics endpoint.

Metrics Categories:
- HTTP request metrics (latency, count, errors)
- Job metrics (queued, running, completed, failed)
- Device metrics (total, reachable, unreachable)
- Authentication metrics (login attempts, failures)
"""

import inspect
import time
from functools import wraps
from typing import Any, Callable

from prometheus_client import Counter, Gauge, Histogram, Info

# Application info
APP_INFO = Info("netauto_app", "Network Automation application information")

# HTTP Request metrics
HTTP_REQUESTS_TOTAL = Counter(
    "netauto_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "netauto_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

HTTP_REQUESTS_IN_PROGRESS = Gauge(
    "netauto_http_requests_in_progress",
    "Number of HTTP requests currently in progress",
    ["method", "endpoint"],
)

# Authentication metrics
AUTH_LOGIN_ATTEMPTS_TOTAL = Counter(
    "netauto_auth_login_attempts_total",
    "Total login attempts",
    ["status"],  # success, failure
)

AUTH_ACTIVE_SESSIONS = Gauge(
    "netauto_auth_active_sessions",
    "Number of active user sessions",
)

# Job metrics
JOBS_TOTAL = Counter(
    "netauto_jobs_total",
    "Total jobs created",
    ["job_type", "status"],
)

JOBS_IN_PROGRESS = Gauge(
    "netauto_jobs_in_progress",
    "Number of jobs currently in progress",
    ["job_type"],
)

JOB_DURATION_SECONDS = Histogram(
    "netauto_job_duration_seconds",
    "Job execution duration in seconds",
    ["job_type", "status"],
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0),
)

JOBS_QUEUED = Gauge(
    "netauto_jobs_queued",
    "Number of jobs waiting in queue",
)

# Device metrics
DEVICES_TOTAL = Gauge(
    "netauto_devices_total",
    "Total number of devices",
    ["customer", "vendor", "platform"],
)

DEVICES_REACHABLE = Gauge(
    "netauto_devices_reachable",
    "Number of reachable devices",
    ["customer"],
)

DEVICES_UNREACHABLE = Gauge(
    "netauto_devices_unreachable",
    "Number of unreachable devices",
    ["customer"],
)

# Compliance metrics
COMPLIANCE_CHECK_TOTAL = Counter(
    "netauto_compliance_checks_total",
    "Total compliance checks run",
    ["policy", "status"],  # pass, fail
)

COMPLIANCE_PASS_RATE = Gauge(
    "netauto_compliance_pass_rate",
    "Current compliance pass rate (0-1)",
    ["customer"],
)

# Config backup metrics
CONFIG_BACKUPS_TOTAL = Counter(
    "netauto_config_backups_total",
    "Total config backups performed",
    ["source", "status"],  # source: manual, scheduled; status: success, failure
)

CONFIG_CHANGES_DETECTED = Counter(
    "netauto_config_changes_detected_total",
    "Total config changes detected",
    ["customer"],
)

# WebSocket metrics
WEBSOCKET_CONNECTIONS = Gauge(
    "netauto_websocket_connections",
    "Number of active WebSocket connections",
    ["type"],  # ssh, job_logs
)

# Database metrics
DB_CONNECTIONS_IN_USE = Gauge(
    "netauto_db_connections_in_use",
    "Number of database connections currently in use",
)

DB_CONNECTIONS_AVAILABLE = Gauge(
    "netauto_db_connections_available",
    "Number of available database connections in pool",
)

# Celery worker metrics
CELERY_WORKERS_ACTIVE = Gauge(
    "netauto_celery_workers_active",
    "Number of active Celery workers",
)

CELERY_TASKS_ACTIVE = Gauge(
    "netauto_celery_tasks_active",
    "Number of currently executing Celery tasks",
)


def set_app_info(version: str, environment: str) -> None:
    """Set application info metric.

    Args:
        version: Application version string.
        environment: Deployment environment (development, staging, production).
    """
    APP_INFO.info({"version": version, "environment": environment})


def track_request_metrics(method: str, endpoint: str) -> Callable[..., Any]:
    """Decorator to track HTTP request metrics.

    Args:
        method: HTTP method (GET, POST, etc.).
        endpoint: API endpoint path.

    Returns:
        Decorator function.

    Example:
        @app.get("/api/v1/devices")
        @track_request_metrics("GET", "/api/v1/devices")
        async def list_devices():
            ...
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            HTTP_REQUESTS_IN_PROGRESS.labels(method=method, endpoint=endpoint).inc()
            start_time = time.perf_counter()
            status_code = "500"
            try:
                result = await func(*args, **kwargs)
                status_code = "200"
                return result
            except Exception:
                status_code = "500"
                raise
            finally:
                duration = time.perf_counter() - start_time
                HTTP_REQUESTS_IN_PROGRESS.labels(method=method, endpoint=endpoint).dec()
                HTTP_REQUEST_DURATION_SECONDS.labels(method=method, endpoint=endpoint).observe(
                    duration
                )
                HTTP_REQUESTS_TOTAL.labels(
                    method=method, endpoint=endpoint, status_code=status_code
                ).inc()

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            HTTP_REQUESTS_IN_PROGRESS.labels(method=method, endpoint=endpoint).inc()
            start_time = time.perf_counter()
            status_code = "500"
            try:
                result = func(*args, **kwargs)
                status_code = "200"
                return result
            except Exception:
                status_code = "500"
                raise
            finally:
                duration = time.perf_counter() - start_time
                HTTP_REQUESTS_IN_PROGRESS.labels(method=method, endpoint=endpoint).dec()
                HTTP_REQUEST_DURATION_SECONDS.labels(method=method, endpoint=endpoint).observe(
                    duration
                )
                HTTP_REQUESTS_TOTAL.labels(
                    method=method, endpoint=endpoint, status_code=status_code
                ).inc()

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def record_login_attempt(success: bool) -> None:
    """Record a login attempt.

    Args:
        success: Whether the login was successful.
    """
    status = "success" if success else "failure"
    AUTH_LOGIN_ATTEMPTS_TOTAL.labels(status=status).inc()


def record_job_created(job_type: str) -> None:
    """Record a job creation.

    Args:
        job_type: Type of job (run_commands, config_backup, compliance_check, etc.).
    """
    JOBS_TOTAL.labels(job_type=job_type, status="created").inc()
    JOBS_IN_PROGRESS.labels(job_type=job_type).inc()


def record_job_completed(job_type: str, success: bool, duration_seconds: float) -> None:
    """Record a job completion.

    Args:
        job_type: Type of job.
        success: Whether the job succeeded.
        duration_seconds: Job execution duration in seconds.
    """
    status = "success" if success else "failure"
    JOBS_TOTAL.labels(job_type=job_type, status=status).inc()
    JOBS_IN_PROGRESS.labels(job_type=job_type).dec()
    JOB_DURATION_SECONDS.labels(job_type=job_type, status=status).observe(duration_seconds)


def record_compliance_check(policy: str, passed: bool) -> None:
    """Record a compliance check result.

    Args:
        policy: Name of the compliance policy.
        passed: Whether the check passed.
    """
    status = "pass" if passed else "fail"
    COMPLIANCE_CHECK_TOTAL.labels(policy=policy, status=status).inc()


def record_config_backup(source: str, success: bool) -> None:
    """Record a config backup result.

    Args:
        source: Backup source (manual, scheduled).
        success: Whether the backup succeeded.
    """
    status = "success" if success else "failure"
    CONFIG_BACKUPS_TOTAL.labels(source=source, status=status).inc()


def update_device_counts(customer: str, vendor: str, platform: str, count: int) -> None:
    """Update device count gauge.

    Args:
        customer: Customer name.
        vendor: Device vendor.
        platform: Device platform.
        count: Number of devices.
    """
    DEVICES_TOTAL.labels(customer=customer, vendor=vendor, platform=platform).set(count)


def update_reachability_counts(customer: str, reachable: int, unreachable: int) -> None:
    """Update device reachability counts.

    Args:
        customer: Customer name.
        reachable: Number of reachable devices.
        unreachable: Number of unreachable devices.
    """
    DEVICES_REACHABLE.labels(customer=customer).set(reachable)
    DEVICES_UNREACHABLE.labels(customer=customer).set(unreachable)


def update_websocket_connections(connection_type: str, count: int) -> None:
    """Update WebSocket connection count.

    Args:
        connection_type: Type of WebSocket connection (ssh, job_logs).
        count: Number of active connections.
    """
    WEBSOCKET_CONNECTIONS.labels(type=connection_type).set(count)


def update_celery_metrics(workers: int, active_tasks: int) -> None:
    """Update Celery worker metrics.

    Args:
        workers: Number of active workers.
        active_tasks: Number of currently executing tasks.
    """
    CELERY_WORKERS_ACTIVE.set(workers)
    CELERY_TASKS_ACTIVE.set(active_tasks)
