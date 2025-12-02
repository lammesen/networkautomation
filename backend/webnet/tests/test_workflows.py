import uuid

import pytest
from rest_framework.test import APIClient

from webnet.customers.models import Customer
from webnet.users.models import User


def _uuid() -> str:
    return str(uuid.uuid4())


@pytest.mark.django_db
def test_workflow_run_branches_and_logs():
    customer = Customer.objects.create(name="Acme")
    user = User.objects.create_user(username="ada", password="secret123", role="admin")
    user.customers.add(customer)

    client = APIClient()
    assert client.login(username="ada", password="secret123")

    set_node = {
        "ref": _uuid(),
        "name": "Set mode",
        "category": "data",
        "type": "set_variable",
        "position_x": 0,
        "position_y": 0,
        "config": {"key": "mode", "value": "blue"},
    }
    if_node = {
        "ref": _uuid(),
        "name": "Check mode",
        "category": "logic",
        "type": "condition",
        "position_x": 160,
        "position_y": 0,
        "config": {"condition": "context.get('mode') == 'blue'"},
    }
    backup_node = {
        "ref": _uuid(),
        "name": "Backup",
        "category": "service",
        "type": "config_backup",
        "position_x": 320,
        "position_y": -80,
        "config": {"job_type": "config_backup", "simulate": True},
    }
    notify_node = {
        "ref": _uuid(),
        "name": "Notify",
        "category": "notification",
        "type": "notify",
        "position_x": 320,
        "position_y": 80,
        "config": {"message": "not blue"},
    }
    payload = {
        "customer": customer.id,
        "name": "Branching workflow",
        "description": "branches on context",
        "nodes": [set_node, if_node, backup_node, notify_node],
        "edges": [
            {"source_ref": set_node["ref"], "target_ref": if_node["ref"]},
            {"source_ref": if_node["ref"], "target_ref": backup_node["ref"], "label": "true"},
            {"source_ref": if_node["ref"], "target_ref": notify_node["ref"], "label": "false"},
        ],
    }

    resp = client.post("/api/v1/workflows/", payload, format="json")
    assert resp.status_code == 201, resp.content
    workflow_id = resp.json()["id"]

    run_resp = client.post(f"/api/v1/workflows/{workflow_id}/run", {"inputs": {}}, format="json")
    assert run_resp.status_code in {201, 202}, run_resp.content
    data = run_resp.json()
    assert data["status"] in {"success", "partial"}
    steps = {step["node_name"]: step for step in data.get("steps", [])}
    assert steps["Set mode"]["status"] == "success"
    assert steps["Check mode"]["status"] == "success"
    # Notify path should be skipped when condition is true
    assert steps["Notify"]["status"] in {"queued", "skipped"}


@pytest.mark.django_db
def test_workflow_api_scoped_to_customer():
    customer_a = Customer.objects.create(name="Alpha")
    customer_b = Customer.objects.create(name="Beta")
    admin = User.objects.create_user(username="admin", password="secret123", role="admin")
    other = User.objects.create_user(username="olivia", password="secret123", role="operator")
    admin.customers.add(customer_a)
    other.customers.add(customer_b)

    client = APIClient()
    client.login(username="admin", password="secret123")

    resp = client.post(
        "/api/v1/workflows/",
        {
            "customer": customer_a.id,
            "name": "Scoped workflow",
            "nodes": [
                {
                    "ref": _uuid(),
                    "name": "noop",
                    "category": "data",
                    "type": "input",
                    "position_x": 0,
                    "position_y": 0,
                    "config": {},
                }
            ],
            "edges": [],
        },
        format="json",
    )
    assert resp.status_code == 201
    workflow_id = resp.json()["id"]

    client.logout()
    client.login(username="olivia", password="secret123")

    detail_resp = client.get(f"/api/v1/workflows/{workflow_id}/")
    assert detail_resp.status_code in {403, 404}

    run_resp = client.post(f"/api/v1/workflows/{workflow_id}/run", {}, format="json")
    assert run_resp.status_code in {403, 404}
