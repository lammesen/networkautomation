"""Test configuration and fixtures."""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Use a fixed, valid Fernet key for test reproducibility
# Generated via: Fernet.generate_key().decode()
TEST_ENCRYPTION_KEY = "6zcciVWk9pw0xGyzngHL5zpIYNF7ryit-8IOGo8RwuU="
os.environ.setdefault("ENCRYPTION_KEY", TEST_ENCRYPTION_KEY)
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ["TESTING"] = "true"  # Disable rate limiting in tests
DEFAULT_ADMIN_PASSWORD = os.environ.setdefault("ADMIN_DEFAULT_PASSWORD", "Admin123!")

from app.core.auth import get_password_hash  # noqa: E402
from app.db import Base, get_db  # noqa: E402
from app.db.models import Credential, Customer, User  # noqa: E402
from app.main import app  # noqa: E402 - must set env vars before importing

# Use in-memory SQLite for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    """Create a test client with overridden database dependency."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_customer(db_session):
    customer = Customer(name="test_customer")
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    return customer


@pytest.fixture
def admin_user(db_session, test_customer):
    """Create an admin user for testing."""
    user = User(
        username="admin",
        hashed_password=get_password_hash(DEFAULT_ADMIN_PASSWORD),
        role="admin",
        is_active=True,
    )
    user.customers.append(test_customer)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def operator_user(db_session, test_customer):
    """Create an operator user for testing."""
    user = User(
        username="operator",
        hashed_password=get_password_hash("Operator123!"),
        role="operator",
        is_active=True,
    )
    user.customers.append(test_customer)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def viewer_user(db_session, test_customer):
    """Create a viewer user for testing."""
    user = User(
        username="viewer",
        hashed_password=get_password_hash("Viewer123!"),
        role="viewer",
        is_active=True,
    )
    user.customers.append(test_customer)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_credential(db_session, test_customer):
    """Create a test credential."""
    credential = Credential(
        name="test_cred",
        username="testuser",
        password="testpass",
        customer_id=test_customer.id,
    )
    db_session.add(credential)
    db_session.commit()
    db_session.refresh(credential)
    return credential


@pytest.fixture
def auth_headers(client, admin_user, test_customer):
    """Get authentication headers for admin user."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": DEFAULT_ADMIN_PASSWORD},
    )
    token = response.json()["access_token"]
    return {
        "Authorization": f"Bearer {token}",
        "X-Customer-ID": str(test_customer.id),
    }


@pytest.fixture
def operator_headers(client, operator_user, test_customer):
    """Get authentication headers for operator user."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "operator", "password": "Operator123!"},
    )
    token = response.json()["access_token"]
    return {
        "Authorization": f"Bearer {token}",
        "X-Customer-ID": str(test_customer.id),
    }


@pytest.fixture
def viewer_headers(client, viewer_user, test_customer):
    """Get authentication headers for viewer user."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "viewer", "password": "Viewer123!"},
    )
    token = response.json()["access_token"]
    return {
        "Authorization": f"Bearer {token}",
        "X-Customer-ID": str(test_customer.id),
    }


@pytest.fixture
def test_device(db_session, test_customer, test_credential):
    """Create a test device."""
    from app.db.models import Device

    device = Device(
        hostname="test-router-1",
        mgmt_ip="192.168.1.1",
        vendor="cisco",
        platform="ios",
        credentials_ref=test_credential.id,
        customer_id=test_customer.id,
        enabled=True,
    )
    db_session.add(device)
    db_session.commit()
    db_session.refresh(device)
    return device


@pytest.fixture
def test_job(db_session, admin_user, test_customer):
    """Create a test job."""
    from app.db.models import Job

    job = Job(
        type="run_commands",
        status="queued",
        user_id=admin_user.id,
        customer_id=test_customer.id,
        target_summary_json={"devices": []},
        payload_json={"commands": ["show version"]},
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


@pytest.fixture
def second_customer(db_session):
    """Create a second customer for multi-tenancy tests."""
    customer = Customer(name="second_customer")
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    return customer
