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


def test_get_credential(client, auth_headers, test_credential):
    """Test getting a specific credential."""
    response = client.get(f"/api/v1/credentials/{test_credential.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_credential.id
    assert data["name"] == test_credential.name


def test_get_credential_not_found(client, auth_headers):
    """Test getting non-existent credential."""
    response = client.get("/api/v1/credentials/99999", headers=auth_headers)
    assert response.status_code == 404


def test_update_credential(client, operator_headers, test_credential):
    """Test updating a credential."""
    response = client.put(
        f"/api/v1/credentials/{test_credential.id}",
        headers=operator_headers,
        json={"username": "updated_user"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "updated_user"


def test_update_credential_name(client, operator_headers, test_credential):
    """Test updating credential name."""
    response = client.put(
        f"/api/v1/credentials/{test_credential.id}",
        headers=operator_headers,
        json={"name": "updated_cred_name"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "updated_cred_name"


def test_update_credential_duplicate_name(
    client, operator_headers, test_credential, db_session, test_customer
):
    """Test updating credential to duplicate name fails."""
    from app.db.models import Credential

    # Create another credential
    other_cred = Credential(
        name="other_cred",
        username="other",
        password="pass",
        customer_id=test_customer.id,
    )
    db_session.add(other_cred)
    db_session.commit()

    response = client.put(
        f"/api/v1/credentials/{test_credential.id}",
        headers=operator_headers,
        json={"name": "other_cred"},
    )
    assert response.status_code == 400


def test_update_credential_not_found(client, operator_headers):
    """Test updating non-existent credential."""
    response = client.put(
        "/api/v1/credentials/99999",
        headers=operator_headers,
        json={"username": "new_user"},
    )
    assert response.status_code == 404


def test_update_credential_viewer_forbidden(client, viewer_headers, test_credential):
    """Test viewer cannot update credential."""
    response = client.put(
        f"/api/v1/credentials/{test_credential.id}",
        headers=viewer_headers,
        json={"username": "should_fail"},
    )
    assert response.status_code == 403


def test_delete_credential(client, operator_headers, db_session, test_customer):
    """Test deleting a credential."""
    from app.db.models import Credential

    # Create a credential to delete
    cred = Credential(
        name="cred_to_delete",
        username="user",
        password="pass",
        customer_id=test_customer.id,
    )
    db_session.add(cred)
    db_session.commit()
    db_session.refresh(cred)
    cred_id = cred.id

    response = client.delete(f"/api/v1/credentials/{cred_id}", headers=operator_headers)
    assert response.status_code == 204

    # Verify it's gone
    get_response = client.get(f"/api/v1/credentials/{cred_id}", headers=operator_headers)
    assert get_response.status_code == 404


def test_delete_credential_not_found(client, operator_headers):
    """Test deleting non-existent credential."""
    response = client.delete("/api/v1/credentials/99999", headers=operator_headers)
    assert response.status_code == 404


def test_delete_credential_viewer_forbidden(client, viewer_headers, test_credential):
    """Test viewer cannot delete credential."""
    response = client.delete(f"/api/v1/credentials/{test_credential.id}", headers=viewer_headers)
    assert response.status_code == 403


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


def test_create_device_accepts_ipv6(client, auth_headers, test_credential):
    """Test creating a device with IPv6 management address."""
    response = client.post(
        "/api/v1/devices",
        headers=auth_headers,
        json={
            "hostname": "router-v6",
            "mgmt_ip": "2001:db8::1",
            "vendor": "cisco",
            "platform": "iosxe",
            "role": "edge",
            "site": "dc1",
            "credentials_ref": test_credential.id,
            "enabled": True,
        },
    )
    assert response.status_code == 201
    assert response.json()["mgmt_ip"] == "2001:db8::1"


def test_list_devices(client, auth_headers, test_credential, db_session, test_customer):
    """Test listing devices."""
    # Create a test device
    device = Device(
        hostname="router1",
        mgmt_ip="192.168.1.1",
        vendor="cisco",
        platform="ios",
        credentials_ref=test_credential.id,
        customer_id=test_customer.id,
        enabled=True,
    )
    db_session.add(device)
    db_session.commit()

    response = client.get("/api/v1/devices", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["devices"]) >= 1


def test_get_device(client, auth_headers, test_credential, db_session, test_customer):
    """Test getting a specific device."""
    device = Device(
        hostname="router1",
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

    response = client.get(f"/api/v1/devices/{device.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["hostname"] == "router1"


def test_update_device(client, auth_headers, test_credential, db_session, test_customer):
    """Test updating a device."""
    device = Device(
        hostname="router1",
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

    response = client.put(
        f"/api/v1/devices/{device.id}",
        headers=auth_headers,
        json={"role": "core"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "core"


def test_delete_device(client, auth_headers, test_credential, db_session, test_customer):
    """Test deleting a device (soft delete)."""
    device = Device(
        hostname="router1",
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

    response = client.delete(f"/api/v1/devices/{device.id}", headers=auth_headers)
    assert response.status_code == 204

    # Verify soft delete
    db_session.refresh(device)
    assert device.enabled is False


def test_filter_devices_by_site(client, auth_headers, test_credential, db_session, test_customer):
    """Test filtering devices by site."""
    device1 = Device(
        hostname="router1",
        mgmt_ip="192.168.1.1",
        vendor="cisco",
        platform="ios",
        site="dc1",
        credentials_ref=test_credential.id,
        customer_id=test_customer.id,
        enabled=True,
    )
    device2 = Device(
        hostname="router2",
        mgmt_ip="192.168.1.2",
        vendor="cisco",
        platform="ios",
        site="dc2",
        credentials_ref=test_credential.id,
        customer_id=test_customer.id,
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
