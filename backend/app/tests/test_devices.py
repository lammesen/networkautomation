"""Tests for device endpoints."""

from app.db.models import Device


def test_create_credential(client, auth_headers):
    """Test creating a credential."""
    response = client.post(
        "/api/v1/credentials",
        headers=auth_headers,
        json={
            "name": "test_cred",
            "username": "testuser",
            "password": "testpass",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "test_cred"
    assert data["username"] == "testuser"
    assert "id" in data


def test_list_credentials(client, auth_headers, test_credential):
    """Test listing credentials."""
    response = client.get("/api/v1/credentials", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_create_device(client, auth_headers, test_credential):
    """Test creating a device."""
    response = client.post(
        "/api/v1/devices",
        headers=auth_headers,
        json={
            "hostname": "router1",
            "mgmt_ip": "192.168.1.1",
            "vendor": "cisco",
            "platform": "ios",
            "role": "edge",
            "site": "dc1",
            "credentials_ref": test_credential.id,
            "enabled": True,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["hostname"] == "router1"
    assert data["mgmt_ip"] == "192.168.1.1"
    assert data["vendor"] == "cisco"


def test_list_devices(client, auth_headers, test_credential, db_session):
    """Test listing devices."""
    # Create a test device
    device = Device(
        hostname="router1",
        mgmt_ip="192.168.1.1",
        vendor="cisco",
        platform="ios",
        credentials_ref=test_credential.id,
        enabled=True,
    )
    db_session.add(device)
    db_session.commit()
    
    response = client.get("/api/v1/devices", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["devices"]) >= 1


def test_get_device(client, auth_headers, test_credential, db_session):
    """Test getting a specific device."""
    device = Device(
        hostname="router1",
        mgmt_ip="192.168.1.1",
        vendor="cisco",
        platform="ios",
        credentials_ref=test_credential.id,
        enabled=True,
    )
    db_session.add(device)
    db_session.commit()
    db_session.refresh(device)
    
    response = client.get(f"/api/v1/devices/{device.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["hostname"] == "router1"


def test_update_device(client, auth_headers, test_credential, db_session):
    """Test updating a device."""
    device = Device(
        hostname="router1",
        mgmt_ip="192.168.1.1",
        vendor="cisco",
        platform="ios",
        credentials_ref=test_credential.id,
        enabled=True,
    )
    db_session.add(device)
    db_session.commit()
    db_session.refresh(device)
    
    response = client.put(
        f"/api/v1/devices/{device.id}",
        headers=auth_headers,
        json={"role": "core"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "core"


def test_delete_device(client, auth_headers, test_credential, db_session):
    """Test deleting a device (soft delete)."""
    device = Device(
        hostname="router1",
        mgmt_ip="192.168.1.1",
        vendor="cisco",
        platform="ios",
        credentials_ref=test_credential.id,
        enabled=True,
    )
    db_session.add(device)
    db_session.commit()
    db_session.refresh(device)
    
    response = client.delete(f"/api/v1/devices/{device.id}", headers=auth_headers)
    assert response.status_code == 204
    
    # Verify soft delete
    db_session.refresh(device)
    assert device.enabled is False


def test_filter_devices_by_site(client, auth_headers, test_credential, db_session):
    """Test filtering devices by site."""
    device1 = Device(
        hostname="router1",
        mgmt_ip="192.168.1.1",
        vendor="cisco",
        platform="ios",
        site="dc1",
        credentials_ref=test_credential.id,
        enabled=True,
    )
    device2 = Device(
        hostname="router2",
        mgmt_ip="192.168.1.2",
        vendor="cisco",
        platform="ios",
        site="dc2",
        credentials_ref=test_credential.id,
        enabled=True,
    )
    db_session.add(device1)
    db_session.add(device2)
    db_session.commit()
    
    response = client.get("/api/v1/devices?site=dc1", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["devices"][0]["site"] == "dc1"
