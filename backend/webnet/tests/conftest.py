import os

import pytest
from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from webnet.customers.models import Customer
from webnet.devices.models import Credential, Device


# Enable DEBUG mode for tests before Django settings load
os.environ.setdefault("DEBUG", "true")

User = get_user_model()


@pytest.fixture(autouse=True)
def set_encryption_key(settings):
    """Ensure ENCRYPTION_KEY is set for tests using Credential encryption."""
    key = Fernet.generate_key().decode()
    settings.ENCRYPTION_KEY = key
    os.environ["ENCRYPTION_KEY"] = key
    settings.CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        }
    }


@pytest.fixture
def customer(db):
    """Create a test customer."""
    return Customer.objects.create(name="Test Customer")


@pytest.fixture
def other_customer(db):
    """Create another test customer for tenant isolation tests."""
    return Customer.objects.create(name="Other Customer")


@pytest.fixture
def credential(db, customer):
    """Create a test credential."""
    cred = Credential(customer=customer, name="Test Credential", username="testuser")
    cred.password = "testpassword123"
    cred.save()
    return cred


@pytest.fixture
def device(db, customer, credential):
    """Create a test device."""
    return Device.objects.create(
        customer=customer,
        hostname="test-device",
        mgmt_ip="192.168.1.1",
        vendor="cisco",
        platform="ios",
        credential=credential,
    )


@pytest.fixture
def admin_user(db, customer):
    """Create an admin user with access to test customer."""
    user = User.objects.create_user(
        username="testadmin",
        password="testpassword123",
        role="admin",
    )
    user.customers.add(customer)
    return user


@pytest.fixture
def operator_user(db, customer):
    """Create an operator user with access to test customer."""
    user = User.objects.create_user(
        username="testoperator",
        password="testpassword123",
        role="operator",
    )
    user.customers.add(customer)
    return user


@pytest.fixture
def viewer_user(db, customer):
    """Create a viewer user with access to test customer."""
    user = User.objects.create_user(
        username="testviewer",
        password="testpassword123",
        role="viewer",
    )
    user.customers.add(customer)
    return user


@pytest.fixture
def api_client():
    """Create a DRF API client."""
    return APIClient()
