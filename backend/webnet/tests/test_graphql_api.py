"""Tests for GraphQL API."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from webnet.customers.models import Customer
from webnet.devices.models import Device, Credential, Tag
from webnet.jobs.models import Job
from webnet.graphql_api.schema import schema

User = get_user_model()


@pytest.fixture
def gql_context(db):
    """Create a GraphQL context with test data."""
    # Create customers
    customer1 = Customer.objects.create(name="Test Customer 1")
    customer2 = Customer.objects.create(name="Test Customer 2")

    # Create users
    admin_user = User.objects.create_user(
        username="admin",
        password="test123",
        role="admin",
    )

    operator_user = User.objects.create_user(
        username="operator",
        password="test123",
        role="operator",
    )
    operator_user.customers.add(customer1)

    viewer_user = User.objects.create_user(
        username="viewer",
        password="test123",
        role="viewer",
    )
    viewer_user.customers.add(customer1)

    # Create credentials
    cred1 = Credential.objects.create(
        customer=customer1,
        name="cred1",
        username="admin",
    )
    cred1.password = "secret"
    cred1.save()

    cred2 = Credential.objects.create(
        customer=customer2,
        name="cred2",
        username="admin",
    )
    cred2.password = "secret"
    cred2.save()

    # Create devices
    device1 = Device.objects.create(
        customer=customer1,
        hostname="router1",
        mgmt_ip="192.168.1.1",
        vendor="cisco",
        platform="ios",
        role="router",
        site="datacenter",
        credential=cred1,
    )

    device2 = Device.objects.create(
        customer=customer1,
        hostname="switch1",
        mgmt_ip="192.168.1.2",
        vendor="cisco",
        platform="ios",
        role="switch",
        site="datacenter",
        credential=cred1,
    )

    device3 = Device.objects.create(
        customer=customer2,
        hostname="router2",
        mgmt_ip="192.168.2.1",
        vendor="juniper",
        platform="junos",
        role="router",
        site="branch",
        credential=cred2,
    )

    # Create tags
    tag1 = Tag.objects.create(
        customer=customer1,
        name="production",
        color="#FF0000",
    )
    device1.device_tags.add(tag1)

    # Create jobs
    job1 = Job.objects.create(
        customer=customer1,
        user=admin_user,
        type="config_backup",
        status="success",
    )

    job2 = Job.objects.create(
        customer=customer2,
        user=admin_user,
        type="config_backup",
        status="running",
    )

    return {
        "customer1": customer1,
        "customer2": customer2,
        "admin_user": admin_user,
        "operator_user": operator_user,
        "viewer_user": viewer_user,
        "device1": device1,
        "device2": device2,
        "device3": device3,
        "tag1": tag1,
        "job1": job1,
        "job2": job2,
        "cred1": cred1,
        "cred2": cred2,
    }


class MockRequest:
    """Mock request object for GraphQL context."""

    def __init__(self, user=None):
        self.user = user
        self.headers = {}


@pytest.mark.django_db
def test_me_query(gql_context):
    """Test that authenticated user can query their own info."""
    query = """
        query {
            me {
                id
                username
                role
            }
        }
    """

    request = MockRequest(user=gql_context["admin_user"])
    result = schema.execute_sync(
        query,
        context_value={"request": request},
    )

    assert result.errors is None
    assert result.data["me"]["username"] == "admin"
    assert result.data["me"]["role"] == "admin"


@pytest.mark.django_db
def test_customers_query_admin(gql_context):
    """Test that admin can see all customers."""
    query = """
        query {
            customers {
                id
                name
            }
        }
    """

    request = MockRequest(user=gql_context["admin_user"])
    result = schema.execute_sync(
        query,
        context_value={"request": request},
    )

    assert result.errors is None
    assert len(result.data["customers"]) == 2
    customer_names = [c["name"] for c in result.data["customers"]]
    assert "Test Customer 1" in customer_names
    assert "Test Customer 2" in customer_names


@pytest.mark.django_db
def test_customers_query_scoped_user(gql_context):
    """Test that non-admin users only see their assigned customers."""
    query = """
        query {
            customers {
                id
                name
            }
        }
    """

    request = MockRequest(user=gql_context["viewer_user"])
    result = schema.execute_sync(
        query,
        context_value={"request": request},
    )

    assert result.errors is None
    assert len(result.data["customers"]) == 1
    assert result.data["customers"][0]["name"] == "Test Customer 1"


@pytest.mark.django_db
def test_devices_query_scoped(gql_context):
    """Test that users only see devices from their assigned customers."""
    query = """
        query {
            devices {
                id
                hostname
                vendor
                customer {
                    name
                }
            }
        }
    """

    request = MockRequest(user=gql_context["operator_user"])
    result = schema.execute_sync(
        query,
        context_value={"request": request},
    )

    assert result.errors is None
    assert len(result.data["devices"]) == 2  # Only customer1 devices
    hostnames = [d["hostname"] for d in result.data["devices"]]
    assert "router1" in hostnames
    assert "switch1" in hostnames
    assert "router2" not in hostnames  # From customer2


@pytest.mark.django_db
def test_device_by_id(gql_context):
    """Test querying a single device by ID."""
    query = """
        query($id: Int!) {
            device(id: $id) {
                id
                hostname
                mgmtIp
                vendor
                platform
                credential {
                    name
                    username
                }
            }
        }
    """

    request = MockRequest(user=gql_context["admin_user"])
    result = schema.execute_sync(
        query,
        context_value={"request": request},
        variable_values={"id": gql_context["device1"].id},
    )

    assert result.errors is None
    assert result.data["device"]["hostname"] == "router1"
    assert result.data["device"]["mgmtIp"] == "192.168.1.1"
    assert result.data["device"]["credential"]["name"] == "cred1"
    # Password should not be exposed
    assert "password" not in result.data["device"]["credential"]


@pytest.mark.django_db
def test_device_query_with_filters(gql_context):
    """Test device query with various filters."""
    query = """
        query($vendor: String, $role: String) {
            devices(vendor: $vendor, role: $role) {
                hostname
                vendor
                role
            }
        }
    """

    request = MockRequest(user=gql_context["admin_user"])
    result = schema.execute_sync(
        query,
        context_value={"request": request},
        variable_values={"vendor": "cisco", "role": "router"},
    )

    assert result.errors is None
    assert len(result.data["devices"]) == 1
    assert result.data["devices"][0]["hostname"] == "router1"


@pytest.mark.django_db
def test_jobs_query_scoped(gql_context):
    """Test that users only see jobs from their assigned customers."""
    query = """
        query {
            jobs {
                id
                type
                status
                customer {
                    name
                }
            }
        }
    """

    request = MockRequest(user=gql_context["viewer_user"])
    result = schema.execute_sync(
        query,
        context_value={"request": request},
    )

    assert result.errors is None
    assert len(result.data["jobs"]) == 1  # Only customer1 jobs
    assert result.data["jobs"][0]["customer"]["name"] == "Test Customer 1"


@pytest.mark.django_db
def test_job_by_id_with_nested_data(gql_context):
    """Test querying a job with nested user and customer data."""
    query = """
        query($id: Int!) {
            job(id: $id) {
                id
                type
                status
                user {
                    username
                }
                customer {
                    name
                }
            }
        }
    """

    request = MockRequest(user=gql_context["admin_user"])
    result = schema.execute_sync(
        query,
        context_value={"request": request},
        variable_values={"id": gql_context["job1"].id},
    )

    assert result.errors is None
    assert result.data["job"]["type"] == "config_backup"
    assert result.data["job"]["user"]["username"] == "admin"
    assert result.data["job"]["customer"]["name"] == "Test Customer 1"


@pytest.mark.django_db
def test_unauthorized_access(gql_context):
    """Test that unauthenticated requests are rejected."""
    query = """
        query {
            devices {
                hostname
            }
        }
    """

    request = MockRequest(user=None)
    result = schema.execute_sync(
        query,
        context_value={"request": request},
    )

    # Should have errors due to lack of authentication
    assert result.errors is not None


@pytest.mark.django_db
def test_cross_customer_access_denied(gql_context):
    """Test that users cannot access devices from other customers."""
    query = """
        query($id: Int!) {
            device(id: $id) {
                hostname
            }
        }
    """

    # Try to access customer2's device as viewer (only has access to customer1)
    request = MockRequest(user=gql_context["viewer_user"])
    result = schema.execute_sync(
        query,
        context_value={"request": request},
        variable_values={"id": gql_context["device3"].id},
    )

    assert result.errors is None
    assert result.data["device"] is None  # Should return None for unauthorized access


@pytest.mark.django_db
def test_tags_query(gql_context):
    """Test querying tags."""
    query = """
        query($customerId: Int) {
            tags(customerId: $customerId) {
                name
                color
                customer {
                    name
                }
            }
        }
    """

    request = MockRequest(user=gql_context["admin_user"])
    result = schema.execute_sync(
        query,
        context_value={"request": request},
        variable_values={"customerId": gql_context["customer1"].id},
    )

    assert result.errors is None
    assert len(result.data["tags"]) == 1
    assert result.data["tags"][0]["name"] == "production"
    assert result.data["tags"][0]["color"] == "#FF0000"


@pytest.mark.django_db
def test_device_with_tags(gql_context):
    """Test querying device with its tags."""
    query = """
        query($id: Int!) {
            device(id: $id) {
                hostname
                tags {
                    name
                    color
                }
            }
        }
    """

    request = MockRequest(user=gql_context["admin_user"])
    result = schema.execute_sync(
        query,
        context_value={"request": request},
        variable_values={"id": gql_context["device1"].id},
    )

    assert result.errors is None
    assert result.data["device"]["hostname"] == "router1"
    assert len(result.data["device"]["tags"]) == 1
    assert result.data["device"]["tags"][0]["name"] == "production"


@pytest.mark.django_db
def test_complex_nested_query(gql_context):
    """Test a complex query with multiple levels of nesting."""
    query = """
        query {
            customers {
                name
                devices {
                    hostname
                    vendor
                    tags {
                        name
                    }
                    credential {
                        name
                    }
                }
                jobs {
                    type
                    status
                }
            }
        }
    """

    request = MockRequest(user=gql_context["admin_user"])
    result = schema.execute_sync(
        query,
        context_value={"request": request},
    )

    assert result.errors is None
    assert len(result.data["customers"]) == 2

    # Check customer1 has correct devices and jobs
    customer1_data = next(c for c in result.data["customers"] if c["name"] == "Test Customer 1")
    assert len(customer1_data["devices"]) == 2
    assert len(customer1_data["jobs"]) == 1
