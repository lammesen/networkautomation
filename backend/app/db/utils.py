"""Database utility helpers."""

from __future__ import annotations

from app.core import settings
from app.core.logging import get_logger
from app.db import Base, Credential, Customer, Device, SessionLocal, User

logger = get_logger(__name__)


def seed_default_data(db_session) -> None:
    """Create default org/admin and sample devices/credentials (idempotent)."""
    if settings.environment.lower() == "production":
        logger.info("Skipping default seed in production environment")
        return
    # Ensure tables exist for the bound engine (safe to call repeatedly)
    try:
        bind = db_session.get_bind()
        if bind:
            Base.metadata.create_all(bind=bind)
    except Exception:  # pragma: no cover - defensive
        logger.warning("Skipping table creation during seed (metadata error)", exc_info=True)

    # Default organization
    default_org = db_session.query(Customer).filter(Customer.name == "Default Organization").first()
    if not default_org:
        default_org = Customer(
            name="Default Organization",
            description="Default customer for migration",
        )
        db_session.add(default_org)
        db_session.commit()
        db_session.refresh(default_org)
        logger.info("Created Default Organization")

    # Default admin user
    admin = db_session.query(User).filter(User.username == "admin").first()
    if not admin:
        from app.core.auth import get_password_hash  # avoid circular import at module load

        admin = User(
            username="admin",
            hashed_password=get_password_hash(settings.admin_default_password),
            role="admin",
            is_active=True,
        )
        db_session.add(admin)
        db_session.commit()
        logger.info("Created default admin user (username: admin)")

    # Ensure admin assigned to default org
    if default_org not in admin.customers:
        admin.customers.append(default_org)
        db_session.commit()

    # Seed credentials
    cred = (
        db_session.query(Credential)
        .filter(
            Credential.name == "default-creds",
            Credential.customer_id == default_org.id,
        )
        .first()
    )
    if not cred:
        cred = Credential(
            customer_id=default_org.id,
            name="default-creds",
            username="admin",
            password="cisco123",
        )
        db_session.add(cred)
        db_session.commit()
        db_session.refresh(cred)
        logger.info("Created credential default-creds")

    linux_cred = (
        db_session.query(Credential)
        .filter(
            Credential.name == "linux-device-creds",
            Credential.customer_id == default_org.id,
        )
        .first()
    )
    if not linux_cred:
        linux_cred = Credential(
            customer_id=default_org.id,
            name="linux-device-creds",
            username="testuser",
            password="testpassword",
        )
        db_session.add(linux_cred)
        db_session.commit()
        db_session.refresh(linux_cred)
        logger.info("Created credential linux-device-creds")
    else:
        # Keep credentials in sync if present
        linux_cred.username = "testuser"
        linux_cred.password = "testpassword"
        db_session.commit()

    # Seed devices
    devices_data = [
        {
            "hostname": "core-router-01",
            "mgmt_ip": "192.0.2.10",
            "platform": "ios",
            "role": "core",
            "site": "lab",
            "vendor": "cisco",
            "cred": cred,
            "enabled": False,
        },
        {
            "hostname": "edge-switch-01",
            "mgmt_ip": "192.0.2.20",
            "platform": "ios",
            "role": "access",
            "site": "lab",
            "vendor": "cisco",
            "cred": cred,
            "enabled": False,
        },
    ]

    for entry in devices_data:
        device = (
            db_session.query(Device)
            .filter(
                Device.hostname == entry["hostname"],
                Device.customer_id == default_org.id,
            )
            .first()
        )
        if not device:
            device = Device(
                customer_id=default_org.id,
                hostname=entry["hostname"],
                mgmt_ip=entry["mgmt_ip"],
                vendor=entry["vendor"],
                platform=entry["platform"],
                role=entry["role"],
                site=entry["site"],
                credentials_ref=entry["cred"].id,
                enabled=entry["enabled"],
            )
            db_session.add(device)

    linux_device = (
        db_session.query(Device)
        .filter(
            Device.hostname == "linux-lab-01",
            Device.customer_id == default_org.id,
        )
        .first()
    )
    if not linux_device:
        linux_device = Device(
            customer_id=default_org.id,
            hostname="linux-lab-01",
            mgmt_ip="linux-device",
            vendor="linux",
            platform="linux",
            role="lab",
            site="docker",
            credentials_ref=linux_cred.id,
            enabled=True,
        )
        db_session.add(linux_device)
    else:
        linux_device.mgmt_ip = "linux-device"
        linux_device.vendor = "linux"
        linux_device.platform = "linux"
        linux_device.credentials_ref = linux_cred.id
        linux_device.enabled = True
        linux_device.role = linux_device.role or "lab"
        linux_device.site = linux_device.site or "docker"

    db_session.commit()


def seed_with_new_session() -> None:
    """Helper used by scripts to seed using a fresh session."""
    db = SessionLocal()
    try:
        seed_default_data(db)
    finally:
        db.close()
