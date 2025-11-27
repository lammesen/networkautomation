"""Main FastAPI application."""

import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.api import (
    api_keys,
    auth,
    commands,
    compliance,
    config,
    customers,
    devices,
    jobs,
    metrics,
    network,
    topology,
    users,
    websocket,
)
from app.api import errors
from app.core import settings, setup_logging
from app.core.logging import get_logger
from app.core.metrics import (
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_IN_PROGRESS,
    HTTP_REQUESTS_TOTAL,
    set_app_info,
)
from app.db import SessionLocal, seed_default_data
from app.domain.exceptions import DomainError

# Setup logging
setup_logging()

# Create app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
)

# Set application info metric
set_app_info(version=settings.api_version, environment=settings.environment)

# Rate limiter - disabled during testing
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.redis_url,
    enabled=not settings.testing,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def prometheus_metrics_middleware(request: Request, call_next):
    """Middleware to collect Prometheus metrics for all HTTP requests."""
    # Skip metrics for the metrics endpoint itself to avoid recursion
    if request.url.path == "/metrics":
        return await call_next(request)

    method = request.method
    # Normalize endpoint path (remove IDs for cardinality control)
    path = request.url.path
    # Replace numeric IDs with placeholder to reduce cardinality
    path_parts = path.split("/")
    normalized_parts = []
    for part in path_parts:
        if part.isdigit():
            normalized_parts.append("{id}")
        else:
            normalized_parts.append(part)
    endpoint = "/".join(normalized_parts)

    HTTP_REQUESTS_IN_PROGRESS.labels(method=method, endpoint=endpoint).inc()
    start_time = time.perf_counter()

    try:
        response = await call_next(request)
        status_code = str(response.status_code)
    except Exception:
        status_code = "500"
        raise
    finally:
        duration = time.perf_counter() - start_time
        HTTP_REQUESTS_IN_PROGRESS.labels(method=method, endpoint=endpoint).dec()
        HTTP_REQUEST_DURATION_SECONDS.labels(method=method, endpoint=endpoint).observe(duration)
        HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status_code=status_code).inc()

    return response


# Include routers
app.include_router(metrics.router)  # Metrics at root level (not under /api/v1)
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(users.router, prefix=settings.api_prefix)
app.include_router(customers.router, prefix=settings.api_prefix)
app.include_router(devices.router, prefix=settings.api_prefix)
app.include_router(devices.cred_router, prefix=settings.api_prefix)
app.include_router(jobs.admin_router, prefix=settings.api_prefix)
app.include_router(jobs.router, prefix=settings.api_prefix)
app.include_router(commands.router, prefix=settings.api_prefix)
app.include_router(config.router, prefix=settings.api_prefix)
app.include_router(compliance.router, prefix=settings.api_prefix)
app.include_router(network.router, prefix=settings.api_prefix)
app.include_router(topology.router, prefix=settings.api_prefix)
app.include_router(websocket.router, prefix=settings.api_prefix)
app.include_router(api_keys.router, prefix=settings.api_prefix)


@app.on_event("startup")
async def seed_defaults() -> None:
    """Seed default data on startup; ignore failures but log them."""
    try:
        db = SessionLocal()
    except Exception as exc:  # pragma: no cover - best effort
        get_logger(__name__).warning("Skipping default seed (session error): %s", exc)
        return
    try:
        seed_default_data(db)
    except Exception as exc:  # pragma: no cover - best effort
        get_logger(__name__).warning("Skipping default seed (operation error): %s", exc)
    finally:
        db.close()


@app.get("/health")
async def health() -> dict:
    """Basic health check endpoint (alias for /health/live)."""
    return {"status": "healthy"}


@app.get("/health/live")
async def health_live() -> dict:
    """Liveness probe endpoint.

    Returns 200 if the application is running.
    Use this for Kubernetes liveness probes to detect deadlocked processes.
    This check is intentionally lightweight - it only verifies the app responds.
    """
    return {"status": "healthy"}


@app.get("/health/ready")
async def health_ready() -> dict:
    """Readiness check endpoint with dependency status.

    Returns detailed status of all dependencies:
    - database: PostgreSQL connection
    - redis: Redis connection
    - celery: Celery worker availability

    Returns 200 if all critical dependencies (database, redis) are healthy.
    Returns 503 if any critical dependency is unhealthy.
    Celery worker status is informational and doesn't affect overall health.
    """
    import redis as redis_client

    from app.celery_app import celery_app

    status = {
        "database": {"status": "healthy"},
        "redis": {"status": "healthy"},
        "celery": {"status": "unknown"},
    }
    overall_healthy = True

    # Check database
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception as e:
        status["database"] = {"status": "unhealthy", "error": str(e)}
        overall_healthy = False

    # Check Redis
    try:
        r = redis_client.from_url(settings.redis_url)
        r.ping()
        r.close()
    except Exception as e:
        status["redis"] = {"status": "unhealthy", "error": str(e)}
        overall_healthy = False

    # Check Celery workers (informational - doesn't affect overall health)
    try:
        inspect = celery_app.control.inspect(timeout=2.0)
        ping_response = inspect.ping()
        if ping_response:
            worker_count = len(ping_response)
            status["celery"] = {
                "status": "healthy",
                "workers": worker_count,
                "worker_names": list(ping_response.keys()),
            }
        else:
            status["celery"] = {
                "status": "degraded",
                "workers": 0,
                "message": "No workers available",
            }
    except Exception as e:
        status["celery"] = {"status": "unhealthy", "error": str(e)}

    result = {
        "status": "healthy" if overall_healthy else "unhealthy",
        "dependencies": status,
    }

    if overall_healthy:
        return result
    else:
        return JSONResponse(status_code=503, content=result)


@app.get("/")
async def root() -> dict:
    """Root endpoint."""
    return {
        "message": "Network Automation API",
        "version": settings.api_version,
        "docs": "/docs",
    }


@app.exception_handler(DomainError)
async def domain_exception_handler(request: Request, exc: DomainError):
    """Translate domain errors to HTTP responses globally."""
    http_exc = errors.to_http(exc)
    return JSONResponse(
        status_code=http_exc.status_code,
        content={"detail": http_exc.detail},
    )
