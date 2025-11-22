"""Database initialization script."""

from app.db import Base, engine, SessionLocal, User, Customer, Credential, Device
from app.core.auth import get_password_hash


def init_db() -> None:
    """Initialize database - create tables and default admin user."""
    # Create tables
    Base.metadata.create_all(bind=engine)
    print("Database tables created")
    
    db = SessionLocal()
    try:
        # Create Default Organization if it doesn't exist
        default_org = db.query(Customer).filter(Customer.name == "Default Organization").first()
        if not default_org:
            default_org = Customer(name="Default Organization", description="Default customer for migration")
            db.add(default_org)
            db.commit()
            db.refresh(default_org)
            print("Default Organization created")
        else:
            print("Default Organization already exists")

        # Create default admin user if not exists
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                username="admin",
                hashed_password=get_password_hash("admin123"),
                role="admin",
                is_active=True,
            )
            db.add(admin)
            db.commit()
            print("Default admin user created (username: admin, password: admin123)")
        else:
            print("Admin user already exists")
            
        # Ensure admin is assigned to Default Organization (though admin role overrides check, explicit is better)
        if default_org not in admin.customers:
            admin.customers.append(default_org)
            db.commit()
            print("Admin assigned to Default Organization")

        # --- Seed Data from Bun Backend ---
        # 1. Create Default Credentials
        cred = db.query(Credential).filter(Credential.name == "default-creds", Credential.customer_id == default_org.id).first()
        if not cred:
            cred = Credential(
                customer_id=default_org.id,
                name="default-creds",
                username="admin",
                password="cisco123", # In a real app, ensure this is encrypted if the model supports it
            )
            db.add(cred)
            db.commit()
            db.refresh(cred)
            print("Created default-creds")
        else:
            print("default-creds already exists")

        # Linux device credentials (matches linux-device container)
        linux_cred = (
            db.query(Credential)
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
            db.add(linux_cred)
            db.commit()
            db.refresh(linux_cred)
            print("Created linux-device-creds")
        else:
            linux_cred.username = "testuser"
            linux_cred.password = "testpassword"
            db.commit()
            print("linux-device-creds already exists (updated credentials)")

        # 2. Create Example Devices
        devices_data = [
            {"hostname": "core-router-01", "mgmt_ip": "192.0.2.10", "platform": "ios", "role": "core", "site": "lab"},
            {"hostname": "edge-switch-01", "mgmt_ip": "192.0.2.20", "platform": "ios", "role": "access", "site": "lab"},
        ]

        from app.db import Device

        for d_data in devices_data:
            device = db.query(Device).filter(Device.hostname == d_data["hostname"], Device.customer_id == default_org.id).first()
            if not device:
                device = Device(
                    customer_id=default_org.id,
                    hostname=d_data["hostname"],
                    mgmt_ip=d_data["mgmt_ip"],
                    vendor="cisco",
                    platform=d_data["platform"],
                    role=d_data["role"],
                    site=d_data["site"],
                    credentials_ref=cred.id,
                    enabled=False, # Disabled by default as per Bun seed
                )
                db.add(device)
                print(f"Created device {d_data['hostname']}")
            else:
                print(f"Device {d_data['hostname']} already exists")

        linux_device = (
            db.query(Device)
            .filter(Device.hostname == "linux-lab-01", Device.customer_id == default_org.id)
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
            db.add(linux_device)
            print("Created linux-lab-01 device")
        else:
            linux_device.mgmt_ip = "linux-device"
            linux_device.vendor = "linux"
            linux_device.platform = "linux"
            linux_device.credentials_ref = linux_cred.id
            linux_device.enabled = True
            linux_device.role = linux_device.role or "lab"
            linux_device.site = linux_device.site or "docker"
            print("linux-lab-01 already exists (updated settings)")

        db.commit()

    finally:
        db.close()


if __name__ == "__main__":
    init_db()