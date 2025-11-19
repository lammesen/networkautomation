from __future__ import annotations

from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_device_crud_flow(client: TestClient) -> None:
    create_payload = {
        "hostname": "core1",
        "mgmt_ip": "192.0.2.1",
        "vendor": "cisco",
        "platform": "ios",
        "role": "core",
        "site": "nyc",
        "tags": "core,dc",
        "napalm_driver": "ios",
        "netmiko_device_type": "cisco_ios",
    }
    created = client.post("/api/devices", json=create_payload)
    assert created.status_code == 200, created.text
    device_id = created.json()["id"]

    listed = client.get("/api/devices", params={"search": "core1"})
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    updated = client.put(f"/api/devices/{device_id}", json={"site": "lon"})
    assert updated.status_code == 200
    assert updated.json()["site"] == "lon"

    deleted = client.delete(f"/api/devices/{device_id}")
    assert deleted.status_code == 204

    confirm = client.get("/api/devices")
    assert confirm.status_code == 200
    assert confirm.json() == []
