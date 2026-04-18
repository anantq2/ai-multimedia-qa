"""tests/test_auth_routes.py — /api/auth/register, /login, /me."""
import pytest
from tests.conftest import make_user


class TestRegister:
    def test_register_success(self, client):
        response = client.post("/api/auth/register", json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "securepass123",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "newuser"
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_register_duplicate_username(self, client, test_user):
        response = client.post("/api/auth/register", json={
            "username": "testuser",
            "email": "other@example.com",
            "password": "password123",
        })
        assert response.status_code == 400
        assert "Username already taken" in response.json()["detail"]

    def test_register_duplicate_email(self, client, test_user):
        response = client.post("/api/auth/register", json={
            "username": "differentuser",
            "email": "test@example.com",
            "password": "password123",
        })
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]

    def test_register_invalid_email(self, client):
        response = client.post("/api/auth/register", json={
            "username": "someone",
            "email": "not-an-email",
            "password": "password123",
        })
        assert response.status_code == 422   # Pydantic EmailStr validation

    def test_register_missing_username(self, client):
        response = client.post("/api/auth/register", json={
            "email": "user@example.com",
            "password": "password123",
        })
        assert response.status_code == 422

    def test_register_missing_password(self, client):
        response = client.post("/api/auth/register", json={
            "username": "user",
            "email": "user@example.com",
        })
        assert response.status_code == 422


class TestLogin:
    def test_login_success(self, client, test_user):
        response = client.post("/api/auth/login", json={
            "username": "testuser",
            "password": "testpassword",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert "access_token" in data

    def test_login_wrong_password(self, client, test_user):
        response = client.post("/api/auth/login", json={
            "username": "testuser",
            "password": "wrongpassword",
        })
        assert response.status_code == 401
        assert "Invalid username or password" in response.json()["detail"]

    def test_login_nonexistent_user(self, client):
        response = client.post("/api/auth/login", json={
            "username": "ghost",
            "password": "anypassword",
        })
        assert response.status_code == 401

    def test_login_missing_fields(self, client):
        response = client.post("/api/auth/login", json={"username": "user"})
        assert response.status_code == 422


class TestMe:
    def test_me_returns_user_info(self, client, test_user, auth_headers):
        response = client.get("/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"

    def test_me_no_auth_header(self, client):
        response = client.get("/api/auth/me")
        assert response.status_code == 403   # HTTPBearer raises 403 when no token

    def test_me_invalid_token(self, client):
        response = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.jwt.token"})
        assert response.status_code == 401
