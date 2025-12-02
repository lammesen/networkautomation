"""Tests for Ansible playbook API endpoints."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from webnet.customers.models import Customer
from webnet.ansible_mgmt.models import Playbook, AnsibleConfig
from webnet.jobs.models import Job
from webnet.devices.models import Device, Credential

User = get_user_model()


@pytest.mark.django_db
def test_create_playbook_requires_auth():
    """Test that creating a playbook requires authentication."""
    client = APIClient()
    resp = client.post(
        "/api/v1/ansible/playbooks/",
        {
            "name": "Test Playbook",
            "content": "---\n- hosts: all\n  tasks:\n    - debug: msg='test'\n",
        },
    )
    assert resp.status_code in {401, 403}


@pytest.mark.django_db
def test_create_playbook():
    """Test creating a playbook."""
    customer = Customer.objects.create(name="Acme")
    user = User.objects.create_user(username="admin", password="secret123", role="admin")
    user.customers.add(customer)

    client = APIClient()
    client.login(username="admin", password="secret123")

    resp = client.post(
        "/api/v1/ansible/playbooks/",
        {
            "customer": customer.id,
            "name": "Test Playbook",
            "description": "A test playbook",
            "source_type": "inline",
            "content": "---\n- hosts: all\n  tasks:\n    - debug: msg='test'\n",
            "variables": {"test_var": "value"},
            "tags": ["test"],
        },
        format="json",
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Test Playbook"
    assert resp.json()["source_type"] == "inline"
    assert Playbook.objects.filter(name="Test Playbook").exists()


@pytest.mark.django_db
def test_list_playbooks():
    """Test listing playbooks."""
    customer = Customer.objects.create(name="Acme")
    user = User.objects.create_user(username="admin", password="secret123", role="admin")
    user.customers.add(customer)

    Playbook.objects.create(
        customer=customer,
        name="Playbook 1",
        content="---\n- hosts: all\n",
        created_by=user,
    )
    Playbook.objects.create(
        customer=customer,
        name="Playbook 2",
        content="---\n- hosts: all\n",
        created_by=user,
    )

    client = APIClient()
    client.login(username="admin", password="secret123")

    resp = client.get("/api/v1/ansible/playbooks/")
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


@pytest.mark.django_db
def test_execute_playbook():
    """Test executing a playbook."""
    customer = Customer.objects.create(name="Acme")
    user = User.objects.create_user(username="admin", password="secret123", role="admin")
    user.customers.add(customer)

    playbook = Playbook.objects.create(
        customer=customer,
        name="Test Playbook",
        content="---\n- hosts: all\n  tasks:\n    - debug: msg='test'\n",
        created_by=user,
    )

    client = APIClient()
    client.login(username="admin", password="secret123")

    resp = client.post(
        f"/api/v1/ansible/playbooks/{playbook.id}/execute/",
        {
            "targets": {"site": "datacenter1"},
            "extra_vars": {"env": "test"},
        },
        format="json",
    )
    if resp.status_code != 201:
        print(f"Response: {resp.json()}")
    assert resp.status_code == 201
    assert "job_id" in resp.json()
    assert Job.objects.filter(id=resp.json()["job_id"], type="ansible_playbook").exists()


@pytest.mark.django_db
def test_validate_playbook():
    """Test playbook validation endpoint."""
    customer = Customer.objects.create(name="Acme")
    user = User.objects.create_user(username="admin", password="secret123", role="admin")
    user.customers.add(customer)

    # Valid playbook
    playbook = Playbook.objects.create(
        customer=customer,
        name="Valid Playbook",
        content="---\n- hosts: all\n  tasks:\n    - debug: msg='test'\n",
        created_by=user,
    )

    client = APIClient()
    client.login(username="admin", password="secret123")

    resp = client.get(f"/api/v1/ansible/playbooks/{playbook.id}/validate/")
    assert resp.status_code == 200
    assert resp.json()["valid"] is True


@pytest.mark.django_db
def test_validate_invalid_playbook():
    """Test validation of invalid playbook."""
    customer = Customer.objects.create(name="Acme")
    user = User.objects.create_user(username="admin", password="secret123", role="admin")
    user.customers.add(customer)

    # Invalid YAML
    playbook = Playbook.objects.create(
        customer=customer,
        name="Invalid Playbook",
        content="---\n  invalid yaml: [unclosed bracket",
        created_by=user,
    )

    client = APIClient()
    client.login(username="admin", password="secret123")

    resp = client.get(f"/api/v1/ansible/playbooks/{playbook.id}/validate/")
    assert resp.status_code == 400
    assert resp.json()["valid"] is False


@pytest.mark.django_db
def test_ansible_config_crud():
    """Test Ansible configuration CRUD operations."""
    customer = Customer.objects.create(name="Acme")
    user = User.objects.create_user(username="admin", password="secret123", role="admin")
    user.customers.add(customer)

    client = APIClient()
    client.login(username="admin", password="secret123")

    # Create config
    resp = client.post(
        "/api/v1/ansible/configs/",
        {
            "customer": customer.id,
            "ansible_cfg_content": "[defaults]\nhost_key_checking = False\n",
            "collections": ["cisco.ios", "ansible.netcommon"],
            "environment_vars": {"ANSIBLE_TIMEOUT": "30"},
        },
        format="json",
    )
    assert resp.status_code == 201
    config_id = resp.json()["id"]

    # Read config
    resp = client.get(f"/api/v1/ansible/configs/{config_id}/")
    assert resp.status_code == 200
    assert "cisco.ios" in resp.json()["collections"]

    # Update config
    resp = client.patch(
        f"/api/v1/ansible/configs/{config_id}/",
        {"collections": ["arista.eos"]},
        format="json",
    )
    assert resp.status_code == 200
    assert "arista.eos" in resp.json()["collections"]


@pytest.mark.django_db
def test_playbook_customer_scoping():
    """Test that playbooks are scoped to customer."""
    customer_a = Customer.objects.create(name="Acme")
    customer_b = Customer.objects.create(name="Beta")
    user_a = User.objects.create_user(username="oper_a", password="secret123", role="operator")
    user_b = User.objects.create_user(username="oper_b", password="secret123", role="operator")
    user_a.customers.add(customer_a)
    user_b.customers.add(customer_b)

    playbook_a = Playbook.objects.create(
        customer=customer_a,
        name="Playbook A",
        content="---\n- hosts: all\n",
        created_by=user_a,
    )

    client = APIClient()
    client.login(username="oper_b", password="secret123")

    # User B should not see Playbook A
    resp = client.get(f"/api/v1/ansible/playbooks/{playbook_a.id}/")
    assert resp.status_code in {403, 404}
