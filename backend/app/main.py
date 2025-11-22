"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    auth,
    commands,
    compliance,
    config,
    customers,
    devices,
    jobs,
    users,
    websocket,
)
from app.core import settings, setup_logging
from app.core.logging import get_logger
from app.db import Credential, Customer, Device, SessionLocal


def _ensure_linux_lab_device() -> None:
    """Guarantee the linux-device sample record exists (idempotent)."""
    try:
        db = SessionLocal()
    except Exception as exc:  # pragma: no cover - best effort
        get_logger(__name__).warning(
            "Skipping linux sample device bootstrap (session error): %s", exc
        )
        return
    try:
        customer = (
            db.query(Customer)
            .filter(Customer.name == "Default Organization")
            .first()
        )
        if not customer:
            return

        cred = (
            db.query(Credential)
            .filter(
                Credential.customer_id == customer.id,
                Credential.name == "linux-device-creds",
            )
            .first()
        )
        if not cred:
            cred = Credential(
                customer_id=customer.id,
                name="linux-device-creds",
                username="testuser",
                password="testpassword",
            )
            db.add(cred)
            db.commit()
            db.refresh(cred)
        else:
            cred.username = "testuser"
            cred.password = "testpassword"
            db.commit()

        device = (
            db.query(Device)
            .filter(
                Device.customer_id == customer.id,
                Device.hostname == "linux-lab-01",
            )
            .first()
        )
        if not device:
            device = Device(
                customer_id=customer.id,
                hostname="linux-lab-01",
                mgmt_ip="linux-device",
                vendor="linux",
                platform="linux",
                role="lab",
                site="docker",
                credentials_ref=cred.id,
                enabled=True,
            )
            db.add(device)
        else:
            device.mgmt_ip = "linux-device"
            device.vendor = "linux"
            device.platform = "linux"
            device.credentials_ref = cred.id
            device.enabled = True
            device.role = device.role or "lab"
            device.site = device.site or "docker"

        db.commit()
    except Exception as exc:  # pragma: no cover - best effort
        get_logger(__name__).warning(
            "Skipping linux sample device bootstrap (operation error): %s", exc
        )
    finally:
        db.close()

# Setup logging
setup_logging()

# Create app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
)

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
app.include_router(jobs.router, prefix=settings.api_prefix)
app.include_router(commands.router, prefix=settings.api_prefix)
app.include_router(config.router, prefix=settings.api_prefix)
app.include_router(compliance.router, prefix=settings.api_prefix)
app.include_router(websocket.router, prefix=settings.api_prefix)


@app.on_event("startup")
async def ensure_sample_devices() -> None:
    _ensure_linux_lab_device()


@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/")
async def root() -> dict:
    """Root endpoint."""
    return {
        "message": "Network Automation API",
        "version": settings.api_version,
        "docs": "/docs",
    }
