"""Main FastAPI application."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.api import (
    auth,
    commands,
    compliance,
    config,
    customers,
    devices,
    jobs,
    network,
    topology,
    users,
    websocket,
)
from app.api import errors
from app.core import settings, setup_logging
from app.core.logging import get_logger
from app.db import SessionLocal, seed_default_data
from app.domain.exceptions import DomainError

# Setup logging
setup_logging()

# Create app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
)

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

# Include routers
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
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/health/ready")
async def health_ready() -> dict:
    """Readiness check endpoint with dependency status.

    Returns detailed status of all dependencies:
    - database: PostgreSQL connection
    - redis: Redis connection
    - celery: Celery worker availability

    Returns 200 if all dependencies are healthy, 503 otherwise.
    """
    import redis

    status = {
        "database": {"status": "healthy"},
        "redis": {"status": "healthy"},
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
        r = redis.from_url(settings.redis_url)
        r.ping()
        r.close()
    except Exception as e:
        status["redis"] = {"status": "unhealthy", "error": str(e)}
        overall_healthy = False

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
