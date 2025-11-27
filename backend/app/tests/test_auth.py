"""Tests for authentication endpoints."""

import os

DEFAULT_ADMIN_PASSWORD = os.getenv("ADMIN_DEFAULT_PASSWORD", "Admin123!")


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_health_ready_endpoint(client):
    """Test readiness check endpoint with dependency status."""
    response = client.get("/health/ready")
    # In test environment, both database and redis should be mocked/available
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "dependencies" in data
    assert "database" in data["dependencies"]
    assert "redis" in data["dependencies"]


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Network Automation API"
    assert "version" in data


def test_login_success(client, admin_user):
    """Test successful login."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": DEFAULT_ADMIN_PASSWORD},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(client, admin_user):
    """Test login with invalid credentials."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "wrongpassword"},
    )
    assert response.status_code == 401


def test_login_nonexistent_user(client):
    """Test login with nonexistent user."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "nonexistent", "password": "password"},
    )
    assert response.status_code == 401


def test_get_current_user(client, auth_headers):
    """Test getting current user info."""
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "admin"
    assert data["role"] == "admin"
    assert data["is_active"] is True


def test_get_current_user_no_token(client):
    """Test getting current user without token."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_get_current_user_invalid_token(client):
    """Test getting current user with invalid token."""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid_token"},
    )
    assert response.status_code == 401


def test_refresh_token_success(client, admin_user):
    """Test successful token refresh."""
    # First login to get tokens
    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": DEFAULT_ADMIN_PASSWORD},
    )
    refresh_token = login_response.json()["refresh_token"]

    # Use refresh token to get new tokens
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_refresh_token_invalid(client):
    """Test refresh with invalid token."""
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid_token"},
    )
    assert response.status_code == 401


def test_refresh_token_with_access_token(client, admin_user):
    """Test refresh with access token instead of refresh token fails."""
    # First login to get tokens
    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": DEFAULT_ADMIN_PASSWORD},
    )
    access_token = login_response.json()["access_token"]

    # Try to use access token as refresh token
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access_token},
    )
    assert response.status_code == 401
    assert "invalid token type" in response.json()["detail"].lower()


def test_refresh_token_inactive_user(client, db_session, admin_user):
    """Test refresh token fails for inactive user."""
    # First login to get tokens
    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": DEFAULT_ADMIN_PASSWORD},
    )
    refresh_token = login_response.json()["refresh_token"]

    # Deactivate user
    admin_user.is_active = False
    db_session.commit()

    # Try to refresh
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 403
