"""Admin-only user management endpoint tests."""


def _login(client, username: str, password: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_non_admin_cannot_list_users(client, operator_user):
    token = _login(client, "operator", "Operator123!")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/users", headers=headers)
    assert response.status_code == 403


def test_admin_can_list_and_update_users(client, auth_headers, operator_user):
    response = client.get("/api/v1/users", headers=auth_headers)
    assert response.status_code == 200
    assert any(user["username"] == "operator" for user in response.json())

    response = client.put(
        f"/api/v1/users/{operator_user.id}",
        headers=auth_headers,
        json={"role": "viewer", "is_active": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "viewer"
    assert data["is_active"] is True


def test_admin_cannot_deactivate_self(client, auth_headers, admin_user):
    response = client.put(
        f"/api/v1/users/{admin_user.id}",
        headers=auth_headers,
        json={"is_active": False},
    )
    assert response.status_code == 403
